import gevent
from gevent import monkey; monkey.patch_socket()

from connection import IrcConnection
import socket
import re

class IrcServer(IrcConnection):
    def __init__(self):
        super(IrcServer, self).__init__()
        self.user('niaxbot', socket.gethostname(), 'Niaxbot')
        self.welcomed = False
        self.add_protocol_handler('376', self._motd_end)
    

    # Server responses
    def _motd_end(self, connection, prefix, command, parameters):
        self.welcomed = True

    def _privmsg(self, connection, prefix, command, parameters):
        pass 

    # IRC Commands
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

    def join(self, channel, key=''):
        self.send_command('JOIN', channel, key)

    def part(self, channel):
        self.send_command('PART', channel)


    # Networking
    def connect(self, server, port=6667):
        self._connect(server, port)

        # Actions once connected (IDENT and NICK)
        self.user(self.username, self.hostname, self.realname)
        self.nick(self.nickname)

    # gevent stuff
    def wait(self):
        self.greenlet.join()


def localloop(client):
    import fcntl, sys, os
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NONBLOCK) # make the file nonblocking
    while True:
        try:
            line = sys.stdin.readline()
            client.send_command(line)
        except IOError:
            sys.exc_clear()
        gevent.socket.wait_read(sys.stdin.fileno())

if __name__ == '__main__':
    client = IrcServer()
    client.nick('Niaxbot-v2')
    client.connect('irc.multiplay.co.uk')
    gevent.spawn(localloop, client)
    client.wait()
