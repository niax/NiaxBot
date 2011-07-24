import signals

import logging
import simplejson

settings = {}

def _get_dict_for_path(key, settings_dict, create_missing=False):
    split = key.find('.')
    if split != -1:
        new_key = key[:split]
        remains = key[split+1:]
        if new_key in settings_dict:
            return _get_dict_for_path(remains, settings_dict[new_key], create_missing=create_missing)
        elif create_missing:
            settings_dict[new_key] = {}
            return _get_dict_for_path(remains, settings_dict[new_key], create_missing=create_missing)
        else:
            return new_key, None
    else:
        return key, settings_dict
    

def get(key):
    child_key, parent = _get_dict_for_path(key, settings)
    if parent == None:
        return None
    if child_key in parent: 
        return parent[child_key]
    return None

def set(key, value):
    child_key, parent = _get_dict_for_path(key, settings, create_missing=True)
    parent[child_key] = value

def load_json(json):
    global settings
    settings = simplejson.loads(json)

def dump_json():
    global settings
    return simplejson.dumps(settings, indent=' ')

# Command handlers
def cmd_set(arguments):
    split = arguments.find(' ')
    key = arguments
    if split != -1:
        key = arguments[:split]
        arguments = arguments[split + 1:]
        set(key, arguments)
        logger.info('%s = %s' % (key, get(key)))
    else:
        logger.info('%s = %s' % (key, get(key)))

# Signals
signals.add_first("command set", cmd_set)

# Set the logger
logger = logging.getLogger('irc.settings')
