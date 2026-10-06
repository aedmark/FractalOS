import commands.mesh_cp as mesh_cp

def run(args, flags, user_context, config=None, **kwargs):
    return mesh_cp.run(args, flags, user_context, config=config, **kwargs)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    scp - Secure copy over FractalOS mesh network (alias to mesh-cp).

SYNOPSIS
    scp <source> <destination>

DESCRIPTION
    Transfers files directly between FractalOS nodes over the mesh network.
    Syntax and behavior are identical to 'mesh-cp'.

EXAMPLES
    scp local.txt node-123:remote.txt
    scp node-123:remote.txt local.txt
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: scp <source> <destination>"
