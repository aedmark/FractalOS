import json
import os
from filesystem import fs_manager

def define_flags():
    return {
        'flags': [],
        'metadata': {}
    }

def _get_manifest(user_context):
    node = fs_manager.get_node("/etc/pkg_manifest.json")
    if not node:
        return {}
    try:
        return json.loads(node.get('content', '{}'))
    except:
        return {}

def _save_manifest(manifest, user_context):
    if not fs_manager.get_node("/etc"):
        fs_manager.create_directory("/etc", user_context)
    fs_manager.write_file("/etc/pkg_manifest.json", json.dumps(manifest, indent=2), user_context)

async def _fetch_url(url):
    import pyodide.http
    try:
        response = await pyodide.http.pyfetch(url)
        if response.status >= 400:
            return None, f"HTTP Error {response.status}"
        return await response.text(), None
    except Exception as e:
        return None, str(e)

async def run(args, flags, user_context, stdin_data=None, **kwargs):
    if not args:
        return {"success": False, "error": {"message": "pkg: missing command", "suggestion": "Try 'pkg list', 'pkg install <url|path>', or 'pkg remove <name>'"}}
        
    cmd = args[0].lower()
    
    if cmd == "list":
        manifest = _get_manifest(user_context)
        if not manifest:
            return "No packages installed."
        
        output = ["INSTALLED PACKAGES:"]
        for name, info in manifest.items():
            version = info.get("version", "1.0.0")
            desc = info.get("description", "No description provided.")
            output.append(f"  {name} (v{version}) - {desc}")
        return "\n".join(output)
        
    elif cmd == "remove":
        if len(args) < 2:
            return {"success": False, "error": {"message": "pkg remove: missing package name", "suggestion": "Try 'pkg remove <name>'"}}
        name = args[1]
        manifest = _get_manifest(user_context)
        if name not in manifest:
            return {"success": False, "error": {"message": f"pkg remove: package '{name}' not found", "suggestion": "Use 'pkg list' to see installed packages."}}
            
        del manifest[name]
        _save_manifest(manifest, user_context)
        
        pkg_path = f"/etc/packages/commands/{name}.py"
        fs_manager.delete_node(pkg_path, user_context)
        
        return {
            "success": True, 
            "output": f"Removed package '{name}'.",
            "effect": "update_commands_manifest"
        }
        
    elif cmd == "install":
        if len(args) < 2:
            return {"success": False, "error": {"message": "pkg install: missing source", "suggestion": "Try 'pkg install <url>' or 'pkg install <local_file>'"}}
            
        source = args[1]
        content = None
        
        if source.startswith("http://") or source.startswith("https://"):
            content, err = await _fetch_url(source)
            if err:
                return {"success": False, "error": {"message": f"pkg install: failed to fetch URL", "suggestion": err}}
        else:
            node = fs_manager.get_node(source)
            if not node or node.get("type") != "file":
                return {"success": False, "error": {"message": f"pkg install: file '{source}' not found", "suggestion": "Check the path."}}
            content = node.get("content", "")
            
        # Parse the package
        import importlib.util
        import sys
        
        # We need to compile it to see if it's valid, and run metadata()
        spec = importlib.util.spec_from_loader("temp_pkg", loader=None)
        module = importlib.util.module_from_spec(spec)
        try:
            exec(content, module.__dict__)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return {"success": False, "error": {"message": f"pkg install: package compilation failed", "suggestion": str(e) + "\n" + tb}}
            
        if not hasattr(module, "run"):
            return {"success": False, "error": {"message": "pkg install: invalid package", "suggestion": "Package must define a run() function."}}
            
        # Extract metadata
        name = None
        # Default to filename if it's a local file, otherwise infer from metadata or URL
        if not source.startswith("http"):
            name = source.split("/")[-1].replace(".py", "")
        else:
            name = source.split("/")[-1].replace(".py", "")
            if not name or name == "":
                name = "unnamed_pkg"
                
        meta = {}
        if hasattr(module, "metadata"):
            try:
                meta = module.metadata()
                if "name" in meta:
                    name = meta["name"]
            except Exception as e:
                pass
                
        # Save to VFS
        if not fs_manager.get_node("/etc/packages"):
            fs_manager.create_directory("/etc/packages", user_context)
        if not fs_manager.get_node("/etc/packages/commands"):
            fs_manager.create_directory("/etc/packages/commands", user_context)
            
        pkg_path = f"/etc/packages/commands/{name}.py"
        fs_manager.write_file(pkg_path, content, user_context)
        
        # Update manifest
        manifest = _get_manifest(user_context)
        manifest[name] = {
            "version": meta.get("version", "1.0.0"),
            "description": meta.get("description", ""),
            "wheels": meta.get("wheels", [])
        }
        _save_manifest(manifest, user_context)
        
        return {
            "success": True, 
            "output": f"Successfully installed package '{name}' (v{manifest[name]['version']}).",
            "effect": "update_commands_manifest"
        }
        
    else:
        return {"success": False, "error": {"message": f"pkg: unknown command '{cmd}'", "suggestion": "Try 'pkg list', 'pkg install', or 'pkg remove'"}}

def man(args, flags, user_context, **kwargs):
    return """
NAME
    pkg - FractalOS package manager

SYNOPSIS
    pkg list
    pkg install <url|path>
    pkg remove <name>

DESCRIPTION
    Installs, lists, and removes user packages (commands) in FractalOS.
    Packages are Python files that implement the command interface.
    Installed packages are saved to /etc/packages/commands/ and registered in /etc/pkg_manifest.json.
    
    If a package specifies required Pyodide wheels in its metadata(), you MUST reboot the OS
    for them to be loaded into the Pyodide environment.

EXAMPLES
    pkg list
    pkg install https://example.com/my_command.py
    pkg install /home/guest/my_script.py
    pkg remove my_script
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: pkg [list | install <url|path> | remove <name>]"
