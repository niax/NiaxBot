import gevent
import gevent.socket

import socket
import re
import logging

import signals
import response_mappings
import settings
from messaging import IrcChannel, Query

class IrcServer(object):
    def __init__(self):
        self.connected = False
        self.user('niaxbot', socket.gethostname(), 'Niaxbot')
        self.welcomed = False
        self.queries = {}
        self.logger = logging.getLogger('irc.server')
        self.raw_logger = logging.getLogger('irc.server.raw')

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

    def notice(self, target, content):
        self.send_command('NOTICE', target, ':' + content)

    # Misc commands
    def ping(self):
        self.send_command('PING', ':' + self.server)

    def pong(self, parameters):
        self.send_command('PONG', ':' + ' '.join(parameters))

    def quit(self, message):
        self.send_command('QUIT', message)

    ## Internal functions

    def _add_channel(self, channelname):
        channel = IrcChannel(self, channelname)
        self.queries[channelname] = channel
        signals.emit('server channel joined', (self, channel))

    def _del_channel(self, channelname):
        channel = self.queries[channelname]
        del self.queries[channelname]
        signals.emit('server channel parted', (self, channel))

    def _get_query(self, target):
        # Create a query if we don't already know about it
        # It won't be a channel because it will have been created by the JOIN handler
        if not target in self.queries:
           self.queries[target] = Query(self, target)
        return self.queries[target]

    # Networking
    def connect(self, server, port=6667):
        self.server = server

        # Change logger so we have per-server loging
        self.logger = logging.getLogger('irc.server (%s:%s)' % (server, port))
        self.raw_logger = logging.getLogger('irc.server.raw (%s:%s)' % (server, port))
        
        # Connection
        self.socket = gevent.socket.create_connection((server, port))
        self.connected = True

        # Enter read loop
        self.greenlet = gevent.spawn(self._loop)

        # Actions once connected (IDENT and NICK)
        self.user(self.username, self.hostname, self.realname)
        self.nick(self.nickname)

    def disconnect(self, message=''):
        if not self.connected:
            return # We can't disconnect as we're not connected

        self.connected = False
        self.quit(message)

        try:
            self.socket.close()
        except socket.error, e:
            self.logger.exception("Error at disconnection")

        self.socket = None
        signals.emit('server disconnect', (self, message))

    def _loop(self):
        previous_buffer = ''
        while self.connected:
            try:
                gevent.sleep() # Force a yield. We want to be fair to other connections
                newdata = self.socket.recv(512)
                lines = (previous_buffer + newdata).split('\r\n')

                if not newdata:
                    # No data returned from recv - assume connection is broken
                    self.disconnect('Connection reset by peer')
                    continue
                # If newdata cuts off the end of a command, store it and we'll get the rest next time through
                if not newdata.endswith('\r\n'):
                    previous_buffer = lines.pop()
                else:
                    previous_buffer = '' # Clear it out for the next time round

                for line in lines:
                    message = line.strip()
                    if message == '':
                        continue # Ignore empty messages
                    self.raw_logger.debug('<' + message)
                    signals.emit('server incoming', (self, line))
            except socket.error, e:
                self.disconnect(e[1]) # Element 1 is the error message
                continue
        self.logger.info("Server loop exiting")

    def send_command(self, command, *args):
        message = command + ' ' +  ' '.join(args) + '\r\n'
        self.raw_logger.debug('>' + message.strip())
        try:
            self.socket.send(message)
        except socket.error, e:
            self.disconnect(e[1]) # Disconnect because of the error.

    # gevent stuff
    def wait(self):
        self.logger.debug("Waiting for main server loop to end")    
        self.greenlet.join()
        self.logger.debug("Done waiting for main server loop to end")    


# Signal Handlers
def server_incoming(server, message):
    message = message.strip()
    prefix_match = re.match('(?P<prefix>:[^ ]* )?(?P<data>.*)', message)
    prefix, data = prefix_match.group('prefix'), prefix_match.group('data')
    prefix = _process_prefix(prefix)
    signals.emit('server event', (server, data, prefix))
    

def server_event(server, data, prefix):
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
    prefix_match = re.match(r':(?P<nick>[^@!]+)(!(?P<user>[^@]+))?(@(?P<host>.+))?', prefix)
    return { 'nick': prefix_match.group('nick'),
             'user': prefix_match.group('user'),
             'host': prefix_match.group('host') }


def _ping_handler(server, parameters, prefix):
    server.pong(parameters)

# Add signal handlers
signals.add_first('server incoming', server_incoming)
signals.add_first('server event', server_event)
signals.add_first('event ping', _ping_handler)
