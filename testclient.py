import gevent
from gevent import monkey; monkey.patch_socket()
import logging
import sys

from irc.server import IrcServer
import irc.signals
import irc.plugins

def localloop(client):
    import fcntl, sys, os
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NONBLOCK) # make the file nonblocking
    while True:
        try:
            line = sys.stdin.readline()
            line = line.strip()
            if line.startswith('/'):
                linesplit = line.split(' ')
                try:
                    irc.signals.emit('command %s' % linesplit[0][1:], (' '.join(linesplit[1:]),))
                except Exception, ex:
                    logger.error(ex.message)

            else:
                client.send_command(line)
        except IOError:
            sys.exc_clear()
        gevent.socket.wait_read(sys.stdin.fileno())


def nick_in_use(server, data, prefix):
    server.nick(server.nickname + '_')

logger = logging.getLogger('irc')

if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    irc.signals.add('event 433', nick_in_use)

    client = IrcServer()
    client.nick('Niaxbot-v2')
    client.connect('irc.multiplay.co.uk')
    gevent.spawn(localloop, client)
    client.wait()
