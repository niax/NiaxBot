import gevent
from gevent import monkey; monkey.patch_socket()

import socket
import re

class IrcConnection(object):
    def __init__(self):
        self.connected = False
        self.protocol_handlers = []
        self.add_protocol_handler('PING', self._ping_handler)
 
    # Protocol Handlers
    def add_protocol_handler(self, command, function):
        self.protocol_handlers.append((re.compile(command), function))

    def _ping_handler(self, connection, prefix, command, parameters):
        self.send_command('PONG', ':' + parameters[0])

    def _connect(self, server, port):
        self.server = server
        
        # Connection
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((server, port))
        self.connected = True

        # Enter read loop
        self.greenlet = gevent.spawn(self._loop)

    def _loop(self):
        newdata = '' # Empty out newdata so we can append to it later
        while True:
            try:
                newdata = newdata + self.socket.recv(1024)
                lines = newdata.split('\r\n')
                # If newdata cuts off the end of a command, store it and we'll get the rest next time through
                if not newdata.endswith('\r\n'):
                    newdata = lines.pop()

                for line in lines:
                    self.process(line)
            except socket.error, e:
                print e
                return

    def send_command(self, command, *args):
        message = command + ' ' +  ' '.join(args) + '\r\n'
        print message.strip()
        self.socket.send(message)

    def process(self, message):
        message = message.strip()
        if message == '':
            return # Ignore empty messages
        cmd_match = re.match("(?P<prefix>:[^ ]* )?(?P<command>[^ ]+) (?P<params>.*)", message)
        prefix, command, params = cmd_match.group('prefix'), cmd_match.group('command'), cmd_match.group('params')

        params = self._process_params(params)
        print params

        has_matched = False
        for handler in self.protocol_handlers:
            (regex, function) = handler
            if regex.match(command):
                function(self, prefix, command, params)
                has_matched = True
        if not has_matched:
            print message

    def _process_params(self, params):
        if params.startswith(':'):
            return [ params[1:] ] # This is trailing
        next_space = params.find(' ')
        if next_space != -1:
            other_params = self._process_params(params[next_space + 1:])
            other_params.insert(0, params[0:next_space])
            return other_params
        else:
            return [ params ]
