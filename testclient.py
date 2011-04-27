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
                    logger.error(ex)

            else:
                client.send_command(line)
        except IOError:
            sys.exc_clear()
        gevent.socket.wait_read(sys.stdin.fileno())

def on_ctcp(server, command, message, query, prefix):
    if command == "VERSION" and message == "": # VERSION request
        query.ctcp_reply("VERSION NiaxBot https://www.github.com/niax/NiaxBot")

def nick_in_use(server, data, prefix):
    server.nick(server.nickname + '_')

logger = logging.getLogger('client')

if __name__ == '__main__':
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console) # Pull the root logger
    logging.getLogger('').setLevel(logging.DEBUG)

    irc.signals.add('event 433', nick_in_use)
    irc.signals.add('ctcp cmd', on_ctcp)

    client = IrcServer()
    client.nick('Niaxbot-v2')
    client.connect('irc.multiplay.co.uk')
    gevent.spawn(localloop, client)
    client.wait()
