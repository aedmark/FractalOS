from filesystem import fs_manager
import os

def run(args, flags, user_context, config=None, **kwargs):
    if not config or not config.get('NETWORKING_ENABLED'):
        return {
            "success": False,
            "error": {
                "message": "mesh-cp: networking is disabled by the system administrator.",
                "suggestion": "To enable networking, set NETWORKING_ENABLED to true in the system configuration and reboot."
            }
        }

    if not args:
        return {
            "success": False,
            "error": {
                "message": "mesh-cp: missing file arguments",
                "suggestion": "Usage: mesh-cp <source> <destination>\nExamples:\n  mesh-cp local.txt node-123:remote.txt\n  mesh-cp node-123:remote.txt local.txt"
            }
        }

    # Handle subcommands 'send' and 'pull'
    if args[0] == "send":
        if len(args) < 3:
            return {
                "success": False,
                "error": {
                    "message": "mesh-cp send: missing arguments",
                    "suggestion": "Usage: mesh-cp send <targetId> <localPath> [<remotePath>]"
                }
            }
        target_id = args[1]
        local_path = args[2]
        remote_path = args[3] if len(args) > 3 else os.path.basename(local_path)
        return _handle_push(local_path, target_id, remote_path, user_context)

    if args[0] == "pull":
        if len(args) < 3:
            return {
                "success": False,
                "error": {
                    "message": "mesh-cp pull: missing arguments",
                    "suggestion": "Usage: mesh-cp pull <targetId> <remotePath> [<localPath>]"
                }
            }
        target_id = args[1]
        remote_path = args[2]
        local_path = args[3] if len(args) > 3 else os.path.basename(remote_path)
        return _handle_pull(target_id, remote_path, local_path, user_context)

    # Classic scp-style: mesh-cp <src> <dst>
    if len(args) != 2:
        return {
            "success": False,
            "error": {
                "message": "mesh-cp: invalid arguments",
                "suggestion": "Usage: mesh-cp <src> <dst>\nExample: mesh-cp file.txt nodeB:file.txt"
            }
        }

    src, dst = args[0], args[1]

    if ':' in src and ':' in dst:
        return {
            "success": False,
            "error": {
                "message": "mesh-cp: cannot copy between two remote nodes directly",
                "suggestion": "Copy the file to your local node first."
            }
        }

    if ':' in src:
        # PULL: remote -> local
        target_id, remote_path = src.split(':', 1)
        if not target_id or not remote_path:
            return {"success": False, "error": "mesh-cp: invalid remote source syntax 'node:path'"}
        return _handle_pull(target_id, remote_path, dst, user_context)

    if ':' in dst:
        # PUSH: local -> remote
        target_id, remote_path = dst.split(':', 1)
        if not target_id:
            return {"success": False, "error": "mesh-cp: invalid remote destination syntax 'node:path'"}
        if not remote_path or remote_path.endswith('/'):
            remote_path = os.path.join(remote_path, os.path.basename(src))
        return _handle_push(src, target_id, remote_path, user_context)

    return {
        "success": False,
        "error": {
            "message": "mesh-cp: neither source nor destination specifies a remote node (missing ':')",
            "suggestion": "Use standard 'cp' for local file copying, or specify 'nodeId:path' for mesh transfers."
        }
    }


def _handle_push(local_path, target_id, remote_path, user_context):
    abs_local = fs_manager.get_absolute_path(local_path)
    node = fs_manager.get_node(abs_local)
    if not node:
        return {
            "success": False,
            "error": {
                "message": f"mesh-cp: local file '{local_path}' not found",
                "suggestion": "Check the path and try again."
            }
        }

    if node.get("type") != "file":
        return {
            "success": False,
            "error": {
                "message": f"mesh-cp: '{local_path}' is a directory, not a file",
                "suggestion": "Directory transfer is not yet supported."
            }
        }

    if not fs_manager.has_permission(abs_local, user_context, 'read'):
        return {
            "success": False,
            "error": {
                "message": f"mesh-cp: permission denied reading '{local_path}'",
                "suggestion": "Ensure you have read permissions on the file."
            }
        }

    content = node.get("content", "")
    return {
        "effect": "mesh_file_send",
        "targetId": target_id,
        "remotePath": remote_path,
        "localPath": local_path,
        "content": content,
        "size": len(content)
    }


def _handle_pull(target_id, remote_path, local_path, user_context):
    abs_local = fs_manager.get_absolute_path(local_path)
    dest_node = fs_manager.get_node(abs_local)
    if dest_node and dest_node.get('type') == 'directory':
        final_local_path = os.path.join(abs_local, os.path.basename(remote_path))
    else:
        final_local_path = abs_local

    parent_dir = os.path.dirname(final_local_path)
    parent_node = fs_manager.get_node(parent_dir)
    if not parent_node or parent_node.get('type') != 'directory':
        return {
            "success": False,
            "error": {
                "message": f"mesh-cp: local destination directory '{parent_dir}' does not exist",
                "suggestion": "Create the directory first or specify a valid local path."
            }
        }

    if not fs_manager.has_permission(parent_dir, user_context, 'write'):
        return {
            "success": False,
            "error": {
                "message": f"mesh-cp: permission denied writing to '{parent_dir}'",
                "suggestion": "Ensure you have write permission in the target directory."
            }
        }

    return {
        "effect": "mesh_file_pull",
        "targetId": target_id,
        "remotePath": remote_path,
        "localPath": final_local_path
    }


def man(args, flags, user_context, **kwargs):
    return """
NAME
    mesh-cp - Peer-to-peer file transfer across the FractalOS mesh network.

SYNOPSIS
    mesh-cp <local_file> <targetId>:<remote_path>
    mesh-cp <targetId>:<remote_file> <local_path>
    mesh-cp send <targetId> <local_file> [<remote_path>]
    mesh-cp pull <targetId> <remote_file> [<local_path>]

DESCRIPTION
    Transfers files directly between FractalOS nodes over the mesh network
    (WebRTC / WebSockets / BroadcastChannel) without third-party cloud storage.

    Files are transferred with integrity and authenticated using existing
    virtual filesystem permissions on both sending and receiving nodes.

OPTIONS
    This command takes no options.

EXAMPLES
    mesh-cp notes.txt oos-1727700000-42:notes.txt
    mesh-cp oos-1727700000-42:/home/root/backup.tar.gz ./backup.tar.gz
    mesh-cp send oos-1727700000-42 config.json
    mesh-cp pull oos-1727700000-42 /etc/network.conf ./network.conf
"""


def help(args, flags, user_context, **kwargs):
    return "Usage: mesh-cp <source> <destination>"
