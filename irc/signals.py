import logging
import inspect

class SignalHandler(object):
    def __init__(self):
        self.first = []
        self.functions = []
        self.last = []
    
    def add(self, function):
        self.functions.append(function)

    def add_first(self, function):
        self.first.insert(0, function)

    def add_last(self, function):
        self.last.append(function)

    def emit(self, signal, arguments):
        for functionlist in (self.first, self.functions, self.last):
            for function in functionlist:
                function(*arguments) # *arguments unfolds the list of arguments

    def unbind_module(self, module):
        self.first = self._unbind_module_list(module, self.first)
        self.functions = self._unbind_module_list(module, self.functions)
        self.last = self._unbind_module_list(module, self.last)

    def _unbind_module_list(self, module, list):
        return filter(lambda x: inspect.getmodule(x) != module, list)
        

handlers = {} # Hash between signal names and SignalHandler
logger = logging.getLogger('irc')

def _handler(signal):
    if not signal in handlers:
        handlers[signal] = SignalHandler()
    return handlers[signal]

def add(signal, function):
    logger.debug('Added %s for signal %s' % (signal, function))
    _handler(signal).add(function)
        
def add_first(signal, function):
    logger.debug('Added %s for signal %s (first)' % (signal, function))
    _handler(signal).add_first(function)

def add_last(signal, function):
    logger.debug('Added %s for signal %s (last)' % (signal, function))
    _handler(signal).add_last(function)

def emit(signal, arguments):
    if signal in handlers:
        handlers[signal].emit(signal, arguments)
    else:
        logger.debug('No handlers for signal %s (params: %s)' % (signal, arguments))

def unbind_module(module):
    logger.debug("Unbinding %s" % module)
    for handler in handlers:
        handlers[handler].unbind_module(module)
