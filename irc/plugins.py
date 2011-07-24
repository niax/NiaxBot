import signals
import imp
import logging
import os.path

modules = {} # Hash between path and modules objects
logger = logging.getLogger('irc.plugins')

def _get_name(path):
    name = os.path.basename(path)
    name = os.path.splitext(name)[0]
    return name
    
def load_plugin(path):
    name = _get_name(path)
    if path in modules:
        logger.info("Reloading %s" % name)
        reload_plugin(path)
    else:
        logger.info("Loading %s from %s" % (name, path))
        modules[path] = imp.load_source(name, path)

def unload_plugin(path):
    name = _get_name(path)
    if path in modules:
        logger.info("Unloading %s" % name)
        signals.unbind_module(modules[path])
        del modules[path]

def reload_plugin(path):
    unload_plugin(path)
    load_plugin(path)

def command(args):
    argsplit = args.split(' ') 
    cmd = argsplit[0]
    path = ' '.join(argsplit[1:])
    if cmd == 'load':
        load_plugin(path)
    elif cmd == 'reload':
        reload_plugin(path)
    elif cmd == 'unload':
        unload_plugin(path)
    elif cmd == 'list':
        for module in modules:
            logger.info(module)

signals.add("command plugin", command)
