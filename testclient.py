import gevent
from gevent import monkey; monkey.patch_socket()

from irc.server import IrcServer

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
