import gevent
from gevent import monkey; monkey.patch_socket()

import socket
import re
import logging

import signals
import response_mappings
from messaging import IrcChannel, Query

class IrcServer(object):
    def __init__(self):
        self.connected = False
        self.user('niaxbot', socket.gethostname(), 'Niaxbot')
        self.welcomed = False
        self.queries = {}

    ## IRC Commands
    # Auth Commands
    def nick(self, nick):
        if self.connected:
            self.send_command('NICK',  nick)
        self.nickname = nick

    def user(self, username, hostname, realname):
        if self.connected:
            self.send_command('USER', username, hostname, self.server, realname)
        self.username = username
        self.hostname = hostname
        self.realname = realname

    # Channel Commands
    def join(self, channel, key=''):
        self.send_command('JOIN', channel, key)

    # Sending messages
    def privmsg(self, target, content):
        self.send_command('PRIVMSG', target, ':' + content)

    # Misc commands
    def ping(self):
        self.send_command('PING', ':' + self.server)

    def pong(self, parameters):
        self.send_command('PONG', ':' + ' '.join(parameters))

    ## Internal functions

    def _add_channel(self, channelname):
        channel = IrcChannel(self, channelname)
        self.queries[channelname] = channel

    def _get_query(self, target):
        # Create a query if we don't already know about it
        # It won't be a channel because it will have been created by the JOIN handler
        if not target in self.queries:
           self.queries[target] = Query(self, target)
        return self.queries[target]

    # Networking
    def connect(self, server, port=6667):
        self.server = server
        
        # Connection
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((server, port))
        self.connected = True

        # Enter read loop
        self.greenlet = gevent.spawn(self._loop)

        # Actions once connected (IDENT and NICK)
        self.user(self.username, self.hostname, self.realname)
        self.nick(self.nickname)

    def _loop(self):
        newdata = '' # Empty out newdata so we can append to it later
        while True:
            try:
                logging.getLogger('irc').debug('getting data')
                newdata = newdata + self.socket.recv(1024)
                logging.getLogger('irc').debug('got data')
                lines = newdata.split('\r\n')
                # If newdata cuts off the end of a command, store it and we'll get the rest next time through
                if not newdata.endswith('\r\n'):
                    newdata = lines.pop()
                else:
                    newdata = '' # Clear it out for the next time round

                for line in lines:
                    signals.emit('server incoming', (self, line))
            except socket.error, e:
                print e
                return

    def send_command(self, command, *args):
        message = command + ' ' +  ' '.join(args) + '\r\n'
        logging.getLogger('irc').info(message.strip())
        self.socket.send(message)

    # gevent stuff
    def wait(self):
        self.greenlet.join()


# Signal Handlers
def server_incoming(arguments):
    (server, message) = arguments
    message = message.strip()
    if message == '':
        return # Ignore empty messages
    logging.getLogger('irc').info(message)
    prefix_match = re.match('(?P<prefix>:[^ ]* )?(?P<data>.*)', message)
    prefix, data = prefix_match.group('prefix'), prefix_match.group('data')
    prefix = _process_prefix(prefix)
    signals.emit('server event', (server, data, prefix))
    

def server_event(arguments):
    (server, data, prefix) = arguments 
    data = data.strip()
    cmd_match = re.match("(?P<command>[^ ]+) (?P<params>.*)", data)
    command, params = cmd_match.group('command'), cmd_match.group('params')

    params = _process_params(params)
    signals.emit('event %s' % command.lower(), (server, params, prefix))


def _process_params(params):
    if params.startswith(':'):
        return [ params[1:] ] # This is trailing
    next_space = params.find(' ')
    if next_space != -1:
        other_params = _process_params(params[next_space + 1:])
        other_params.insert(0, params[0:next_space])
        return other_params
    else:
        return [ params ]

def _process_prefix(prefix):
    if prefix == None:
        return None
    prefix_match = re.match(r'(?P<nick>[^@!]+)(!(?P<user>[^@]+))?(@(?P<host>.+))?', prefix)
    return { 'nick': prefix_match.group('nick'),
             'user': prefix_match.group('user'),
             'host': prefix_match.group('host') }


def _ping_handler(arguments):
    (server, parameters, prefix) = arguments
    server.pong(parameters)

# Add signal handlers
signals.add_first('server incoming', server_incoming)
signals.add_first('server event', server_event)
signals.add_first('event ping', _ping_handler)
