def run(args, flags, user_context, **kwargs):
    """
    Mounts a host folder into the virtual filesystem.
    """
    if not args or args[0] != "host":
        return {
            "success": False,
            "error": {
                "message": "mount: invalid usage",
                "suggestion": "Usage: mount host <mount_point>"
            }
        }
        
    if len(args) < 2:
        return {
            "success": False,
            "error": {
                "message": "mount: missing mount point",
                "suggestion": "Usage: mount host <mount_point>"
            }
        }

    mount_point = args[1]
    
    return {
        "effect": "mount_host",
        "mountPoint": mount_point
    }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    mount - mount host directories into the VFS (portable mode only)

SYNOPSIS
    mount host <mount_point>

DESCRIPTION
    Mounts a folder from the host computer into the FractalOS Virtual File System.
    This command is only available in portable mode (Desktop app).
    When executed, it will open a host folder selection dialog.
    
    All files inside the host folder will become readable and writable within FractalOS.
    
    Note: Python scripts executed within FractalOS cannot dynamically `open()` host files
    because the python environment is isolated. Standard commands like `cat`, `grep`, 
    and the `editor` fully support host files.

EXAMPLES
    mount host /mnt/projects
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: mount host <mount_point>"
