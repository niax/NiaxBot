import gevent
from gevent import monkey; monkey.patch_socket()
import logging

from irc.server import IrcServer
import irc.signals

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

def private(server, message, query, prefix):
    if query.is_channel():
        logger.info('%s %s: %s' % (query.name, prefix['nick'], message))
    else:
        logger.info('PM %s: %s' % (prefix['nick'], message))

def ctcp_cmd(server, message, query, prefix):
    if query.is_channel():
        logger.info('CTCP %s %s: %s' % (query.name, prefix['nick'], message))
    else:
        logger.info('PM CTCP %s: %s' % (prefix['nick'], message))


logger = logging.getLogger('irc')

if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    irc.signals.add('message private', private)
    irc.signals.add('ctcp cmd', ctcp_cmd)
    

    client = IrcServer()
    client.nick('Niaxbot-v2')
    client.connect('irc.multiplay.co.uk')
    gevent.spawn(localloop, client)
    client.wait()
