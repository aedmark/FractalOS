import json
import os
import re
import datetime
import hashlib
from filesystem import fs_manager

RESERVED_COMMANDS = {
    "ls", "cat", "cd", "rm", "cp", "mv", "mkdir", "echo", "pwd", "grep",
    "python", "samwise", "sudo", "su", "sh", "exit", "help", "man", "pkg",
    "clear", "date", "whoami", "uname", "tree", "find", "chmod", "chown",
    "touch", "ps", "kill", "top", "history", "alias", "unalias", "clip"
}

def define_flags():
    return {
        'flags': [
            {'name': 'help', 'short': 'h', 'long': 'help', 'takes_value': False},
            {'name': 'json', 'short': 'j', 'long': 'json', 'takes_value': False},
            {'name': 'dry_run', 'short': 'n', 'long': 'dry-run', 'takes_value': False},
            {'name': 'registry', 'short': 'r', 'long': 'registry', 'takes_value': True},
            {'name': 'export', 'short': 'e', 'long': 'export', 'takes_value': True},
            {'name': 'out', 'short': 'o', 'long': 'out', 'takes_value': True},
            {'name': 'mesh', 'short': 'm', 'long': 'mesh', 'takes_value': False},
        ],
        'aliases': {
            'h': 'help',
            'j': 'json',
            'n': 'dry_run',
            'r': 'registry',
            'e': 'export',
            'o': 'out',
            'm': 'mesh'
        },
        'metadata': {}
    }

def _get_manifest(user_context):
    node = fs_manager.get_node("/etc/pkg_manifest.json")
    if not node:
        return {}
    try:
        return json.loads(node.get('content', '{}'))
    except Exception:
        return {}

def _save_manifest(manifest, user_context):
    try:
        if not fs_manager.get_node("/etc"):
            fs_manager.create_directory("/etc", user_context, parents=True)
        fs_manager.write_file("/etc/pkg_manifest.json", json.dumps(manifest, indent=2), user_context)
    except PermissionError:
        raise PermissionError(13, "Permission denied to modify /etc. Are you root? Try 'sudo pkg ...'", "/etc")

async def _fetch_url(url):
    try:
        import pyodide.http
        response = await pyodide.http.pyfetch(url)
        if response.status >= 400:
            return None, f"HTTP Error {response.status}"
        return await response.text(), None
    except Exception as e:
        return None, str(e)

def _get_checksum(content_str):
    try:
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    except Exception:
        return hashlib.sha1(content_str.encode('utf-8')).hexdigest()

def _resolve_vfs_path(path_str, user_context=None):
    if user_context and user_context.get("current_path"):
        fs_manager.current_path = user_context.get("current_path")
    if not path_str:
        return fs_manager.current_path
    return fs_manager.get_absolute_path(path_str)

def _read_file_from_vfs(path_str, user_context=None):
    abs_path = _resolve_vfs_path(path_str, user_context)
    node = fs_manager.get_node(abs_path)
    if not node:
        return None, f"File '{path_str}' not found."
    if node.get("type") != "file":
        return None, f"'{path_str}' is not a file."
    return node.get("content", ""), None

def _write_file_to_vfs(path_str, content_str, user_context):
    abs_path = _resolve_vfs_path(path_str, user_context)
    parent_dir = os.path.dirname(abs_path)
    if not fs_manager.get_node(parent_dir):
        fs_manager.create_directory(parent_dir, user_context, parents=True)
    fs_manager.write_file(abs_path, content_str, user_context)
    return abs_path

def _compile_and_inspect(content, source_path="<package>"):
    import importlib.util
    try:
        compiled_code = compile(content, source_path, "exec")
    except SyntaxError as e:
        return None, f"SyntaxError at line {e.lineno}: {e.msg}"
    except Exception as e:
        return None, f"Compilation error: {str(e)}"

    spec = importlib.util.spec_from_loader("pkg_temp_inspect", loader=None)
    module = importlib.util.module_from_spec(spec)
    try:
        exec(compiled_code, module.__dict__)
    except Exception as e:
        return None, f"Runtime error during package inspection: {str(e)}"

    return module, None

def _validate_module(module, default_name=None):
    errors = []
    warnings = []

    if not hasattr(module, "run") or not callable(getattr(module, "run")):
        errors.append("Package missing required 'run(args, flags, user_context, ...)' function.")

    if not hasattr(module, "man") and not hasattr(module, "help"):
        warnings.append("Package lacks documentation ('man' or 'help' function).")

    meta = {}
    if hasattr(module, "metadata") and callable(getattr(module, "metadata")):
        try:
            meta = module.metadata()
            if not isinstance(meta, dict):
                errors.append("'metadata()' must return a dictionary.")
                meta = {}
        except Exception as e:
            errors.append(f"Error calling 'metadata()': {str(e)}")
    else:
        warnings.append("Package does not define 'metadata()'. Default metadata will be inferred.")

    name = meta.get("name") or default_name
    if not name:
        errors.append("Package name is not defined in metadata and could not be inferred.")
    elif not re.match(r"^[a-zA-Z0-9_\-]+$", name):
        errors.append(f"Package name '{name}' contains invalid characters (allowed: alphanumeric, _, -).")
    elif name in RESERVED_COMMANDS:
        warnings.append(f"Package name '{name}' collides with a core system command.")

    version = meta.get("version", "1.0.0")
    if not isinstance(version, str):
        errors.append("Package 'version' in metadata must be a string (e.g. '1.0.0').")

    description = meta.get("description", "")
    author = meta.get("author", "Unknown")
    license_type = meta.get("license", "MIT")
    wheels = meta.get("wheels", [])
    dependencies = meta.get("dependencies", [])

    return {
        "valid": len(errors) == 0,
        "name": name,
        "version": str(version),
        "description": str(description),
        "author": str(author),
        "license": str(license_type),
        "wheels": list(wheels) if isinstance(wheels, (list, tuple)) else [],
        "dependencies": list(dependencies) if isinstance(dependencies, (list, tuple)) else [],
        "errors": errors,
        "warnings": warnings,
        "raw_meta": meta
    }

def _get_local_repo_path(user_context, custom_export=None):
    if custom_export:
        return _resolve_vfs_path(custom_export, user_context)
    username = (user_context.get("name") or user_context.get("current_user", "Guest")) if user_context else "Guest"
    if username == "root":
        return "/var/pkg/repo"
    return f"/home/{username}/.pkg/repo"

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    if user_context:
        if 'name' not in user_context and 'current_user' in user_context:
            user_context['name'] = user_context['current_user']
        if 'current_user' not in user_context and 'name' in user_context:
            user_context['current_user'] = user_context['name']
        if user_context.get('current_path'):
            fs_manager.current_path = user_context['current_path']

    if not args:
        return {
            "success": False,
            "error": {
                "message": "pkg: missing subcommand",
                "suggestion": "Try 'pkg list', 'pkg validate <file>', 'pkg init <name>', 'pkg pack <file>', 'pkg publish <file>', or 'pkg install <name>'"
            }
        }

    cmd = args[0].lower()

    # ---------------------------------------------------------
    # pkg list
    # ---------------------------------------------------------
    if cmd in ("list", "ls"):
        manifest = _get_manifest(user_context)
        if flags.get("json"):
            return json.dumps(manifest, indent=2)

        if not manifest:
            return "No packages installed."

        output = ["\x1b[1;36m=== INSTALLED PACKAGES ===\x1b[0m"]
        for name, info in manifest.items():
            version = info.get("version", "1.0.0")
            desc = info.get("description", "No description provided.")
            author = info.get("author", "")
            auth_str = f" by {author}" if author else ""
            output.append(f"  \x1b[1;32m{name}\x1b[0m (v{version}{auth_str}) - {desc}")
        return "\n".join(output)

    # ---------------------------------------------------------
    # pkg init <name> [path]
    # ---------------------------------------------------------
    elif cmd in ("init", "new", "scaffold"):
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "pkg init: missing package name",
                    "suggestion": "Usage: pkg init <name> [target_file.py]"
                }
            }
        pkg_name = args[1]
        if not re.match(r"^[a-zA-Z0-9_\-]+$", pkg_name):
            return {
                "success": False,
                "error": {
                    "message": f"pkg init: invalid package name '{pkg_name}'",
                    "suggestion": "Names must contain only letters, numbers, underscores, or hyphens."
                }
            }

        target_file = args[2] if len(args) > 2 else f"./{pkg_name}.py"
        username = user_context.get("current_user", "Guest") if user_context else "Guest"

        scaffold_code = f'''"""
{pkg_name} - FractalOS community command package
"""

def metadata():
    return {{
        "name": "{pkg_name}",
        "version": "1.0.0",
        "description": "Custom {pkg_name} command for FractalOS",
        "author": "{username}",
        "license": "MIT",
        "wheels": [],
        "dependencies": []
    }}

def define_flags():
    return {{
        "flags": [
            {{"name": "help", "short": "h", "long": "help", "takes_value": False}},
            {{"name": "loud", "short": "l", "long": "loud", "takes_value": False}},
        ],
        "aliases": {{"h": "help", "l": "loud"}}
    }}

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    if flags.get("help"):
        return {{"success": True, "output": help(args, flags, user_context)}}

    msg = " ".join(args) if args else "FractalOS package system"
    if flags.get("loud"):
        msg = msg.upper() + "!"
    return f"[{pkg_name}] {{msg}}"

def man(args, flags, user_context, **kwargs):
    return """
NAME
    {pkg_name} - Custom FractalOS community package

SYNOPSIS
    {pkg_name} [-l|--loud] [arguments...]

DESCRIPTION
    Command scaffolded via 'pkg init'.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: {pkg_name} [-l|--loud] [arguments...]"
'''
        try:
            abs_path = _write_file_to_vfs(target_file, scaffold_code, user_context)
            return {
                "success": True,
                "output": f"Created package template at \x1b[34m{abs_path}\x1b[0m\nNext: edit the file, run 'pkg validate {target_file}', then 'pkg publish {target_file}'."
            }
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "message": f"pkg init: failed to write file: {str(e)}",
                    "suggestion": "Check directory permissions."
                }
            }

    # ---------------------------------------------------------
    # pkg validate <path|name>
    # ---------------------------------------------------------
    elif cmd in ("validate", "check"):
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "pkg validate: missing target file or package name",
                    "suggestion": "Usage: pkg validate <path/to/package.py>"
                }
            }
        target = args[1]
        content, err = _read_file_from_vfs(target, user_context)
        filename = os.path.basename(target)

        # If not found directly, check installed packages
        if err:
            installed_path = f"/etc/packages/commands/{target}.py"
            content, err2 = _read_file_from_vfs(installed_path, user_context)
            if err2:
                return {
                    "success": False,
                    "error": {
                        "message": f"pkg validate: '{target}' not found",
                        "suggestion": f"Checked '{target}' and '{installed_path}'."
                    }
                }
            filename = f"{target}.py"

        # Check if it's an .fpkg package bundle
        if filename.endswith(".fpkg") or (content and content.strip().startswith("{") and "fractalos-package-v1" in content):
            try:
                bundle = json.loads(content)
                content = bundle.get("source", "")
                filename = f"{bundle.get('name', 'pkg')}.py"
            except Exception as e:
                return {
                    "success": False,
                    "error": {
                        "message": f"pkg validate: malformed .fpkg bundle: {str(e)}",
                        "suggestion": "Ensure the bundle is valid JSON."
                    }
                }

        module, comp_err = _compile_and_inspect(content, filename)
        if comp_err:
            if flags.get("json"):
                return json.dumps({"valid": False, "error": comp_err}, indent=2)
            return {
                "success": False,
                "error": {
                    "message": f"pkg validate: syntax / compilation failure",
                    "suggestion": comp_err
                }
            }

        default_name = filename.replace(".py", "")
        v_res = _validate_module(module, default_name)

        if flags.get("json"):
            return json.dumps(v_res, indent=2)

        out_lines = [f"\x1b[1;36m=== VALIDATION REPORT: {v_res['name']} ===\x1b[0m"]
        out_lines.append(f"  File: {target}")
        out_lines.append(f"  Version: {v_res['version']}")
        out_lines.append(f"  Description: {v_res['description'] or '(none)'}")
        out_lines.append(f"  Author: {v_res['author']}")
        out_lines.append(f"  License: {v_res['license']}")

        if v_res["valid"]:
            out_lines.append("\n  \x1b[1;32m✓ Syntax compilation: PASS\x1b[0m")
            out_lines.append("  \x1b[1;32m✓ Entry point: run() defined\x1b[0m")
            out_lines.append("  \x1b[1;32m✓ Metadata schema: PASS\x1b[0m")
        else:
            out_lines.append("\n  \x1b[1;31m✗ ERRORS:\x1b[0m")
            for err_item in v_res["errors"]:
                out_lines.append(f"    - {err_item}")

        if v_res["warnings"]:
            out_lines.append("  \x1b[1;33m⚠ WARNINGS:\x1b[0m")
            for w in v_res["warnings"]:
                out_lines.append(f"    - {w}")

        if v_res["valid"]:
            out_lines.append(f"\n\x1b[1;32mSUCCESS:\x1b[0m Package '{v_res['name']}' is valid and ready to publish.")
            return "\n".join(out_lines)
        else:
            return {
                "success": False,
                "error": {
                    "message": f"pkg validate: {len(v_res['errors'])} validation error(s)",
                    "suggestion": "\n".join(out_lines)
                }
            }

    # ---------------------------------------------------------
    # pkg pack <path> [--out <dest>] [--json]
    # ---------------------------------------------------------
    elif cmd in ("pack", "bundle"):
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "pkg pack: missing source file",
                    "suggestion": "Usage: pkg pack <path/to/package.py> [--out <file.fpkg>]"
                }
            }
        source = args[1]
        content, err = _read_file_from_vfs(source, user_context)
        if err:
            return {"success": False, "error": {"message": f"pkg pack: {err}", "suggestion": "Specify an existing file."}}

        filename = os.path.basename(source)
        module, comp_err = _compile_and_inspect(content, filename)
        if comp_err:
            return {"success": False, "error": {"message": "pkg pack: compilation failed", "suggestion": comp_err}}

        default_name = filename.replace(".py", "")
        v_res = _validate_module(module, default_name)
        if not v_res["valid"]:
            return {
                "success": False,
                "error": {
                    "message": "pkg pack: package failed validation",
                    "suggestion": "\n".join(v_res["errors"])
                }
            }

        checksum = _get_checksum(content)
        pkg_name = v_res["name"]
        pkg_version = v_res["version"]
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"

        bundle = {
            "format": "fractalos-package-v1",
            "name": pkg_name,
            "version": pkg_version,
            "description": v_res["description"],
            "author": v_res["author"],
            "license": v_res["license"],
            "wheels": v_res["wheels"],
            "dependencies": v_res["dependencies"],
            "sha256": checksum,
            "size": len(content.encode('utf-8')),
            "created_at": now_iso,
            "source": content
        }

        bundle_json = json.dumps(bundle, indent=2)

        if flags.get("json"):
            return bundle_json

        out_dest = flags.get("out") or f"./{pkg_name}-{pkg_version}.fpkg"
        abs_dest = _write_file_to_vfs(out_dest, bundle_json, user_context)

        return (
            f"Successfully packaged \x1b[1;32m{pkg_name}\x1b[0m (v{pkg_version}) -> \x1b[34m{abs_dest}\x1b[0m\n"
            f"  Size: {bundle['size']} bytes | SHA256: {checksum[:16]}..."
        )

    # ---------------------------------------------------------
    # pkg publish <source> [--export <dir>] [--registry <url>] [--mesh] [--dry-run]
    # ---------------------------------------------------------
    elif cmd in ("publish", "pub"):
        if len(args) < 2:
            return {
                "success": False,
                "error": {
                    "message": "pkg publish: missing package file or name",
                    "suggestion": "Usage: pkg publish <path/to/pkg.py> [--dry-run] [--export <dir>] [--mesh]"
                }
            }
        source = args[1]
        content, err = _read_file_from_vfs(source, user_context)
        filename = os.path.basename(source)

        # Check installed packages if local file not found
        if err:
            installed_path = f"/etc/packages/commands/{source}.py"
            content, err2 = _read_file_from_vfs(installed_path, user_context)
            if err2:
                return {
                    "success": False,
                    "error": {
                        "message": f"pkg publish: package source '{source}' not found",
                        "suggestion": f"Check local path or ensure package is installed."
                    }
                }
            filename = f"{source}.py"

        # Check if bundle
        raw_bundle = None
        if filename.endswith(".fpkg") or (content and content.strip().startswith("{") and "fractalos-package-v1" in content):
            try:
                raw_bundle = json.loads(content)
                content = raw_bundle.get("source", "")
                filename = f"{raw_bundle.get('name', 'pkg')}.py"
            except Exception as e:
                return {"success": False, "error": {"message": f"pkg publish: invalid bundle format: {str(e)}"}}

        module, comp_err = _compile_and_inspect(content, filename)
        if comp_err:
            return {"success": False, "error": {"message": "pkg publish: compilation error", "suggestion": comp_err}}

        default_name = filename.replace(".py", "")
        v_res = _validate_module(module, default_name)
        if not v_res["valid"]:
            return {
                "success": False,
                "error": {
                    "message": "pkg publish: package failed validation",
                    "suggestion": "\n".join(v_res["errors"])
                }
            }

        pkg_name = v_res["name"]
        pkg_version = v_res["version"]
        checksum = _get_checksum(content)
        size_bytes = len(content.encode('utf-8'))
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"

        # Prepare registry entry
        manifest_entry = {
            "name": pkg_name,
            "version": pkg_version,
            "description": v_res["description"],
            "author": v_res["author"],
            "license": v_res["license"],
            "wheels": v_res["wheels"],
            "dependencies": v_res["dependencies"],
            "sha256": checksum,
            "size": size_bytes,
            "file": f"{pkg_name}.py",
            "published_at": now_iso
        }

        # Build bundle
        bundle = {
            "format": "fractalos-package-v1",
            "name": pkg_name,
            "version": pkg_version,
            "description": v_res["description"],
            "author": v_res["author"],
            "license": v_res["license"],
            "wheels": v_res["wheels"],
            "dependencies": v_res["dependencies"],
            "sha256": checksum,
            "size": size_bytes,
            "created_at": now_iso,
            "source": content
        }

        # Determine target
        custom_export = flags.get("export")
        registry_url = flags.get("registry")
        is_mesh = flags.get("mesh", False)
        repo_dir = _get_local_repo_path(user_context, custom_export)

        target_desc = f"Local Repository ({repo_dir})"
        if registry_url:
            target_desc = f"Remote Registry ({registry_url})"
        elif is_mesh:
            target_desc = f"Distributed Mesh & Local Repo ({repo_dir})"

        # DRY RUN
        if flags.get("dry_run"):
            report = [
                "\x1b[1;33m[DRY RUN] Package Publishing Simulation\x1b[0m",
                f"  Package: \x1b[1;32m{pkg_name}\x1b[0m (v{pkg_version})",
                f"  Author: {v_res['author']} | License: {v_res['license']}",
                f"  SHA256: {checksum}",
                f"  Size: {size_bytes} bytes",
                f"  Target: {target_desc}",
                "  Status: Validated and ready for publishing. 0 files modified."
            ]
            if flags.get("json"):
                return json.dumps({
                    "dry_run": True,
                    "target": target_desc,
                    "package": manifest_entry
                }, indent=2)
            return "\n".join(report)

        # WRITE TO LOCAL/EXPORT REPO
        try:
            if not fs_manager.get_node(repo_dir):
                fs_manager.create_directory(repo_dir, user_context, parents=True)

            # 1. Write python source file
            py_path = f"{repo_dir}/{pkg_name}.py"
            fs_manager.write_file(py_path, content, user_context)

            # 2. Write package bundle file (.fpkg)
            fpkg_path = f"{repo_dir}/{pkg_name}-{pkg_version}.fpkg"
            fs_manager.write_file(fpkg_path, json.dumps(bundle, indent=2), user_context)

            # 3. Update index.json
            index_path = f"{repo_dir}/index.json"
            index_data = {"format": "fractalos-registry-v1", "updated_at": now_iso, "packages": {}}
            index_node = fs_manager.get_node(index_path)
            if index_node and index_node.get("type") == "file":
                try:
                    index_data = json.loads(index_node.get("content", "{}"))
                    if "packages" not in index_data:
                        index_data["packages"] = {}
                except Exception:
                    pass

            index_data["updated_at"] = now_iso
            index_data["packages"][pkg_name] = manifest_entry
            fs_manager.write_file(index_path, json.dumps(index_data, indent=2), user_context)

        except PermissionError:
            return {
                "success": False,
                "error": {
                    "message": f"pkg publish: Permission denied writing to '{repo_dir}'",
                    "suggestion": "Try 'sudo pkg publish' or pass '--export /path/to/custom/dir'."
                }
            }

        # REMOTE REGISTRY (Optional URL)
        remote_status = ""
        if registry_url:
            # Under pyodide, send POST
            try:
                import pyodide.http
                res = await pyodide.http.pyfetch(
                    registry_url,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                    body=json.dumps({"package": bundle})
                )
                if res.status >= 400:
                    remote_status = f" (Remote registry returned HTTP {res.status})"
                else:
                    remote_status = " (Published to remote registry)"
            except Exception as e:
                remote_status = f" (Remote upload warning: {str(e)})"

        # Result report
        summary = [
            f"\x1b[1;32m✓ Successfully published package '{pkg_name}' (v{pkg_version})\x1b[0m",
            f"  Repository: \x1b[34m{repo_dir}\x1b[0m{remote_status}",
            f"  Index updated: {repo_dir}/index.json",
            f"  Package bundle: {fpkg_path} ({size_bytes} bytes)",
            f"  SHA256 Checksum: {checksum[:16]}..."
        ]

        ret_val = {
            "success": True,
            "output": "\n".join(summary)
        }

        if is_mesh:
            ret_val["effect"] = "pkg_mesh_publish"
            ret_val["package"] = manifest_entry
            ret_val["sender"] = user_context.get("current_user", "Guest") if user_context else "Guest"

        if flags.get("json"):
            ret_val["output"] = json.dumps(manifest_entry, indent=2)

        return ret_val

    # ---------------------------------------------------------
    # pkg search [query]
    # ---------------------------------------------------------
    elif cmd in ("search", "find"):
        query = args[1].lower() if len(args) > 1 else ""
        username = user_context.get("current_user", "Guest") if user_context else "Guest"
        search_dirs = ["/var/pkg/repo", f"/home/{username}/.pkg/repo"]

        found = {}
        for sdir in search_dirs:
            idx_node = fs_manager.get_node(f"{sdir}/index.json")
            if idx_node and idx_node.get("type") == "file":
                try:
                    data = json.loads(idx_node.get("content", "{}"))
                    for pname, pmeta in data.get("packages", {}).items():
                        if not query or query in pname.lower() or query in pmeta.get("description", "").lower():
                            found[pname] = {**pmeta, "repo": sdir}
                except Exception:
                    pass

        if not found:
            return f"No packages found matching '{query}' in local repositories."

        out = ["\x1b[1;36m=== AVAILABLE COMMUNITY PACKAGES ===\x1b[0m"]
        for pname, pmeta in sorted(found.items()):
            ver = pmeta.get("version", "1.0.0")
            desc = pmeta.get("description", "")
            author = pmeta.get("author", "")
            auth_str = f" by {author}" if author else ""
            out.append(f"  \x1b[1;32m{pname}\x1b[0m (v{ver}{auth_str}) - {desc}")
            out.append(f"    Location: {pmeta['repo']}/{pmeta.get('file', pname + '.py')}")
        return "\n".join(out)

    # ---------------------------------------------------------
    # pkg remove <name>
    # ---------------------------------------------------------
    elif cmd in ("remove", "rm", "uninstall"):
        if len(args) < 2:
            return {"success": False, "error": {"message": "pkg remove: missing package name", "suggestion": "Try 'pkg remove <name>'"}}
        name = args[1]
        manifest = _get_manifest(user_context)
        if name not in manifest:
            return {"success": False, "error": {"message": f"pkg remove: package '{name}' not found", "suggestion": "Use 'pkg list' to see installed packages."}}

        del manifest[name]
        _save_manifest(manifest, user_context)

        pkg_path = f"/etc/packages/commands/{name}.py"
        try:
            fs_manager.remove(pkg_path)
        except Exception:
            pass

        return {
            "success": True,
            "output": f"Removed package '{name}'.",
            "effect": "update_commands_manifest"
        }

    # ---------------------------------------------------------
    # pkg install <source>
    # ---------------------------------------------------------
    elif cmd in ("install", "i", "add"):
        if len(args) < 2:
            return {"success": False, "error": {"message": "pkg install: missing source", "suggestion": "Try 'pkg install <name|url|path>'"}}

        source = args[1]
        content = None
        username = user_context.get("current_user", "Guest") if user_context else "Guest"

        DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/aedmark/fractalos-packages/main/packages"

        if source.startswith("http://") or source.startswith("https://"):
            content, err = await _fetch_url(source)
            if err:
                return {"success": False, "error": {"message": f"pkg install: failed to fetch URL", "suggestion": err}}
        else:
            # 1. Check direct path
            content, err = _read_file_from_vfs(source, user_context)

            # 2. Check local repos (/var/pkg/repo, ~/.pkg/repo)
            if err:
                candidate_paths = [
                    f"/var/pkg/repo/{source}.py",
                    f"/var/pkg/repo/{source}.fpkg",
                    f"/home/{username}/.pkg/repo/{source}.py",
                    f"/home/{username}/.pkg/repo/{source}.fpkg"
                ]
                for cpath in candidate_paths:
                    c_content, c_err = _read_file_from_vfs(cpath, user_context)
                    if not c_err:
                        content = c_content
                        break

            # 3. Check remote default registry URL
            if not content:
                registry_url = f"{DEFAULT_REGISTRY_URL}/{source}.py"
                content, err = await _fetch_url(registry_url)
                if err or not content or content.strip() == "404: Not Found" or content.startswith("404:"):
                    return {
                        "success": False,
                        "error": {
                            "message": f"pkg install: package '{source}' not found locally or in registry.",
                            "suggestion": f"Checked local file, /var/pkg/repo, ~/.pkg/repo, and {registry_url}"
                        }
                    }

        # Check if bundle (.fpkg)
        if content and (source.endswith(".fpkg") or (content.strip().startswith("{") and "fractalos-package-v1" in content)):
            try:
                bundle = json.loads(content)
                content = bundle.get("source", "")
            except Exception as e:
                return {"success": False, "error": {"message": f"pkg install: corrupted package bundle: {str(e)}"}}

        filename = os.path.basename(source).replace(".fpkg", ".py")
        module, comp_err = _compile_and_inspect(content, filename)
        if comp_err:
            return {"success": False, "error": {"message": f"pkg install: package compilation failed", "suggestion": comp_err}}

        default_name = filename.replace(".py", "")
        v_res = _validate_module(module, default_name)
        if not v_res["valid"]:
            return {"success": False, "error": {"message": "pkg install: invalid package", "suggestion": "\n".join(v_res["errors"])}}

        name = v_res["name"]

        # Save to VFS in /etc/packages/commands/
        try:
            if not fs_manager.get_node("/etc/packages"):
                fs_manager.create_directory("/etc/packages", user_context, parents=True)
            if not fs_manager.get_node("/etc/packages/commands"):
                fs_manager.create_directory("/etc/packages/commands", user_context, parents=True)

            pkg_path = f"/etc/packages/commands/{name}.py"
            fs_manager.write_file(pkg_path, content, user_context)
        except PermissionError:
            return {
                "success": False,
                "error": {
                    "message": "pkg: Permission denied",
                    "suggestion": "You need root privileges to install system packages. Try 'sudo pkg install'."
                }
            }

        # Update manifest
        manifest = _get_manifest(user_context)
        manifest[name] = {
            "version": v_res["version"],
            "description": v_res["description"],
            "author": v_res["author"],
            "license": v_res["license"],
            "wheels": v_res["wheels"],
            "dependencies": v_res["dependencies"],
            "installed_at": datetime.datetime.utcnow().isoformat() + "Z"
        }
        _save_manifest(manifest, user_context)

        return {
            "success": True,
            "output": f"Successfully installed package '{name}' (v{v_res['version']}). Run '{name}' to execute.",
            "effect": "update_commands_manifest"
        }

    else:
        return {
            "success": False,
            "error": {
                "message": f"pkg: unknown command '{cmd}'",
                "suggestion": "Try 'pkg list', 'pkg install', 'pkg remove', 'pkg validate', 'pkg init', 'pkg pack', 'pkg publish', or 'pkg search'"
            }
        }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    pkg - FractalOS package manager & community publishing tool

SYNOPSIS
    pkg list [-j|--json]
    pkg init <name> [target_file.py]
    pkg validate <path|name> [-j|--json]
    pkg pack <path> [-o <out.fpkg>] [-j|--json]
    pkg publish <path|name> [-n|--dry-run] [-e <dir>] [-r <url>] [-m|--mesh]
    pkg search [query]
    pkg install <name|url|path>
    pkg remove <name>

DESCRIPTION
    Manages, validates, bundles, publishes, and installs community packages in FractalOS.
    Packages are Python files defining the command interface:
      - metadata(): returns dict with name, version, description, author, license, wheels, dependencies
      - define_flags(): declares command line flags and aliases
      - run(args, flags, user_context, ...): execution entry point
      - man(...) and help(...): documentation

SUBCOMMANDS
    list, ls
        List all installed packages and versions.
    init <name> [file]
        Scaffold a valid new package starter template.
    validate <path>, check
        Audit a package file for syntax errors, required functions, and metadata schema.
    pack <path>, bundle
        Package code and metadata into a distributable .fpkg bundle with SHA256 verification.
    publish <path>
        Publish a package to the local community repository (/var/pkg/repo or ~/.pkg/repo),
        an export directory, a remote registry, or announce it across the mesh network.
    search [query], find
        Search available community repositories for packages.
    install <source>, i, add
        Install a package from local repository, .fpkg bundle, file path, URL, or registry.
    remove <name>, rm, uninstall
        Uninstall a package from the system.

OPTIONS
    -n, --dry-run
        Simulate packaging/publishing and preview the catalog entry without modifying files.
    -j, --json
        Output manifest, validation, or package bundle in JSON format.
    -e, --export <dir>
        Specify custom export directory for package publishing.
    -o, --out <file>
        Specify output destination file for 'pkg pack'.
    -m, --mesh
        Announce published package to peer nodes across the local mesh network.

EXAMPLES
    pkg init mycalc
    pkg validate ./mycalc.py
    pkg publish ./mycalc.py --dry-run
    pkg publish ./mycalc.py
    pkg install mycalc
    mycalc --help
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: pkg [list | init <name> | validate <file> | pack <file> | publish <file> | search | install <source> | remove <name>]"
