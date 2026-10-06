from commands import wm

def define_flags():
    return wm.define_flags()

def run(args, flags, user_context, **kwargs):
    return wm.run(args, flags, user_context, **kwargs)

def man(args, flags, user_context, **kwargs):
    return wm.man(args, flags, user_context, **kwargs)

def help(args, flags, user_context, **kwargs):
    return wm.help(args, flags, user_context, **kwargs)
