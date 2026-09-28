def run(args, context):
    return {"success": True, "output": ""}

def help(args, context):
    return "Do nothing, successfully."

def man(args, context, **kwargs):
    return """
NAME
    true - do nothing, successfully

SYNOPSIS
    true

DESCRIPTION
    Does nothing and returns true (success).

OPTIONS
    This command takes no options.

EXAMPLES
    true
"""
