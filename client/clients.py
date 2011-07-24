import gevent
from gevent import monkey; monkey.patch_all()
import logging
import sys

from irc.server import IrcServer
import irc.signals
import irc.plugins

class BasicClient(object):
    VERSIONSTRING = "PyRC v0.0.1 (First Steps) - https://github.com/niax/Niaxbot"
    SETTINGSPATH = '.settings.json'

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
            'reload': self.reload_settings,
            'save': self.save_settings,
        }

        # Map commands
        for command in command_mapping:
            irc.signals.add('command %s' % command, command_mapping[command])

        self.reload_settings([]) # Pass in empty arguments

    def run(self):
        # TODO: Implement proper plugin autoload
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

        # Load auto-load plugins
        autoload_plugins = irc.settings.get('client.autoload_plugins')
        if autoload_plugins == None:
            autoload_plugins = []
            irc.settings.set('client.autoload_plugins', autoload_plugins)
        for plugin in autoload_plugins:
            irc.plugins.load_plugin(plugin)

        # Do autoconnects
        servers = irc.settings.get('client.servers')
        if servers == None: # Set servers to empty list if non-existant
            servers = []
            irc.settings.set('client.servers', servers)
        for server in servers:
            self.connect(server['name'])

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

    def reload_settings(self, args):
        self.logger.info('Loading settings')
        file = open(self.SETTINGSPATH, 'r')
        settings_str = file.read()
        irc.settings.load_json(settings_str)
        file.close()

    def save_settings(self, args):
        self.logger.info('Saving settings')
        file = open(self.SETTINGSPATH, 'w')
        settings_str = irc.settings.dump_json()
        file.write(settings_str)
        file.close()

    def on_ctcp(self, server, command, message, query, prefix):
        if command == "VERSION" and message == "": # VERSION request
            query.ctcp_reply("VERSION " + self.VERSIONSTRING)

    def nick_in_use(self, server, data, prefix):
        server.nick(server.nickname + '_')

