import gevent
from gevent import monkey; monkey.patch_socket()
import logging
import sys

#import curses
#import curses.wrapper # Wraps curses stuff to ensure terminal returns to the correct state
#import curses.ascii
import urwid

from irc.server import IrcServer
import irc.signals
import irc.plugins

from client.widgets import MainWidget, GEventEventLoop

class BasicClient(object):
    VERSIONSTRING = "PyRC v0.0.1 (First Steps) - https://github.com/niax/Niaxbot"

    def __init__(self):
        self.servers = {}
        self.activeserver = None
        self.logger = logging.getLogger('client')
        self.running = False

        irc.signals.add('event 433', self.nick_in_use)
        irc.signals.add('ctcp cmd', self.on_ctcp)

        # Mapping between commands and functions
        command_mapping = {
            'select': self.select_server,
            'connect' : self.connect,
            'quit': self.quit,
        }

        # Map commands
        for command in command_mapping:
            irc.signals.add('command %s' % command, command_mapping[command])

    def run(self):
        self.running = True
        try:
            loop = gevent.spawn(self.localloop)
            loop.join() # Wait for loop to quit
            self.logger.info("Exiting normally")
        except:
            self.logger.exception("Error at blocking!")

    def localloop(self):
        import fcntl, sys, os
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NONBLOCK) # make the file nonblocking

        while self.running:
            try:
                gevent.socket.wait_read(sys.stdin.fileno()) # Wait for input
                line = sys.stdin.readline()
                self.process_line(line)
            except IOError:
                sys.exc_clear()

    def process_line(self, line):
        line = line.strip()
        if line.startswith('/'):
            linesplit = line.split(' ')
            try:
                irc.signals.emit('command %s' % linesplit[0][1:], (' '.join(linesplit[1:]),))
            except Exception, ex:
                self.logger.error(ex)

        else:
            if self.activeserver != None:
                self.activeserver.send_command(line)


    def select_server(self, arg):
        if arg in servers:
            self.activeserver = servers[arg]
        else:
            self.logger.error("Server %s is not connected")

    def connect(self, args):
        if args in self.servers:
            self.logger.error("Server already connected")
        else:
            server = IrcServer()
            server.nick('Niaxbot-v2')
            server.connect(args)
            self.servers[args] = server
            self.activeserver = server # Newly connected servers become active server

    def quit(self, args):
        # If we don't have a quit message, set a default
        self.logger.info("Client quitting")
        if args == '':
            args = "Quitting"
        for servername in self.servers:
            # Disconnect from server and wait for it to disconnect
            self.servers[servername].disconnect(args)
            self.servers[servername].wait()
        self.running = False

    def on_ctcp(self, server, command, message, query, prefix):
        if command == "VERSION" and message == "": # VERSION request
            query.ctcp_reply("VERSION " + self.VERSIONSTRING)

    def nick_in_use(self, server, data, prefix):
        server.nick(server.nickname + '_')



class CursesClient(BasicClient):
    def __init__(self):
        super(CursesClient, self).__init__()
        irc.signals.add('server motd content', self._motd)


    def localloop(self):

        self.mainwidget = MainWidget(self)
        self.palette = [
            ('status', 'white', 'dark blue'),
            ('status-seperator', 'light blue', 'dark blue'),
            ('title', 'white', 'dark blue'),
        ]

        self.mainloop = urwid.MainLoop(self.mainwidget, palette = self.palette, event_loop = GEventEventLoop(), unhandled_input = self.unhandled, handle_mouse=False)
        self.mainloop.run()

    def quit(self, args):
        super(CursesClient, self).quit(args)
        self.mainloop.event_loop.stop()

    def unhandled(self, k):
        self.logger.debug("Unhandled key: %s" % str(k))

    def _motd(self, server, params, prefix):
        self.mainwidget.statuswindow.add_line('[%s] %s' % (server.server, params[-1]))
