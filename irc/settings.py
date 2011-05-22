import signals
import logging

settings = {}

class Setting(object):
    def __init__(self, key, formatter):  
        self.formatter = formatter
        self.key = key
        self.value = formatter.default() if formatter != None else None

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def set_str(self, string):
        if self.formatter == None:
            # No formatter set
            self.value = string
        else:    
            self.value = self.formatter.deserialize(string)

    def get_str(self):
        str_value = ''
        if self.formatter == None:
            # No formatter set
            str_value = self.value
        else:
            str_value = self.formatter.serialize(self.value)        
        return str_value

    def set_formatter(self, formatter):
        str_value = self.get_str()
        self.formatter = formatter
        self.set_str(str_value)

class SettingFormatter(object):
    def deserialize(self, string):
        raise NotImplementedError("Formatter not implemented")

    def serialize(self, string):
        raise NotImplementedError("Formatter not implemented")

    def default(self):
        raise NotImplementedError("Formatter not implemented")

class StringFormatter(SettingFormatter):
    def deserialize(self, string):
        return string

    def serialize(self, string):
        return string

    def default(self):
        return ''

class IntFormatter(SettingFormatter):
    def deserialize(self, string):
        return int(string)

    def serialize(self, value):
        return str(value)

    def default(self):
        return 0

class BoolFormatter(SettingFormatter):
    def deserialize(self, string):
        return string == "True"

    def serialize(self, value):
        return "True" if value else "False"

    def default(self):
        return False

formatters = {
    'string': StringFormatter(),
    'int': IntFormatter(),
    'bool': BoolFormatter(),
}

def add_setting(key, formatter_name):
    formatter = formatters[formatter_name]
    if key in settings:
        setting = settings[key]
        if setting.formatter == None:
            # This setting was set before being added
            setting.set_formatter(formatter)
        elif setting.formatter != formatter:
            # If the formatters are equal we can assume setting definition is the same
            raise Error("Setting already exists")
        # Otherwise - this setting is already added with the correct formatter
    else:
        settings[key] = Setting(key, formatter)

def add_setting_str(key):
    # Lazy shortcut for adding a string setting
    add_setting(key, 'string')

def add_setting_int(key):
    add_setting(key, 'int')

def add_setting_bool(key):
    add_setting(key, 'bool')

def _get_or_create_setting(key):
    setting = None
    if key in settings:
        setting = settings[key]
    else:
        setting = Setting(key, None) # None formatter means no type is known
        settings[key] = setting
    return setting
        
    
def get(key):
    if key in settings:
        return settings[key].get()
    else:
        return None

def get_str(key):
    if key in settings:
        return settings[key].get_str()
    else:
        return None
    

def set(key, value):
    _get_or_create_setting(key).set(value)

def set_str(key, string):
    _get_or_create_setting(key).set_str(string)
    

def get_all():
    # TODO: make this pull out a key-value dict of settings
    return settings

# Command handlers
def cmd_set(arguments):
    split = arguments.find(' ')
    key = arguments
    if split != -1:
        key = arguments[:split]
        arguments = arguments[split + 1:]
        set_str(key, arguments)
        logger.info('%s = %s' % (key, get_str(key)))
    else:
        logger.info('%s = %s' % (key, get_str(key)))
        

# Signals
signals.add_first("command set", cmd_set)

# Set the logger
logger = logging.getLogger('irc.signals')
