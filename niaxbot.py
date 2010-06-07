from ircbot import SingleServerIRCBot
from irclib import nm_to_n, nm_to_h, irc_lower, ip_numstr_to_quad, ip_quad_to_numstr
from httplib import HTTPConnection
from string import Template
import re

class Config:
	class ParseState:
		NoState = 0	
		Channels = 1
		PM = 2
		Public = 3
		Action = 4
		
		@staticmethod
		def state(l):
			if l == "===PM===":
				return Config.ParseState.PM
			elif l == "===Public===":
				return Config.ParseState.Public
			elif l == "===ACTION===":
				return Config.ParseState.Action
			elif l == "===Channels===":
				return Config.ParseState.Channels
			
	
	def __init__(self):
		self.channels = {}
		self.actions = {}
		self.public = {}
		self.pm = {}
	
	def parse(self, config):
		state = Config.ParseState.NoState
		self.channels = {}
		self.actions = {}
		self.public = {}
		self.pm = {}
		lastline = ""
		for l in config.split('\n'):
			l = l.strip()
			if l.startswith("#") or l == "":
				continue
			print l

			if l.startswith("==="):
				state = Config.ParseState.state(l)
			elif state == Config.ParseState.Channels:
				split = l.split()
				if len(split) == 1:
					self.channels["#%s" % split[0]] = ""
				else:
					self.channels["#%s" % split[0]] = split[1]
			else:
				if lastline != "":
					if state == Config.ParseState.Public:
						self.public[lastline] = l		
					elif state == Config.ParseState.PM:
						self.pm[lastline] = l
					elif state == Config.ParseState.Action:
						self.actions[lastline] = l
					lastline = ""
				else:
					lastline = l
		
		

class NiaxBot(SingleServerIRCBot):
	def __init__(self, refresh, nickname, server, port=6667):
		rSplit = refresh.split('/')
		self.refreshHost = rSplit[0]
		self.refreshTarget = '/'.join(rSplit[1:])
		self.config = Config()
		print "Target is on %s at %s" % (self.refreshHost, self.refreshTarget)
		SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)

	def on_nicknameinuse(self, connection, event):
		print "Nick in use"
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, connection, event):
		print "Wecomed"
		self.do_update(connection)

	def on_privmsg(self, connection, event):
		cmd = event.arguments()[0]
		if cmd == "reload":
			self.do_update(connection)
		self.do_receive(connection, event, self.config.pm, nm_to_n(event.source()), cmd)

	def on_pubmsg(self, connection, event):
		self.do_receive(connection, event, self.config.public, event.target(), event.arguments()[0])

	def on_dccmsg(self, connection, event):
		print "DCC Message"
		c.privmsg("You said: " + event.arguments()[0])

	def on_dccchat(self, connection, event):
		print "DCC Chat"
		if len(event.arguments()) != 2:
			return
		args = events.arguments()[1].split()
		if len(args) == 4:
			try:
				address = ip_numstr_to_quad(args[2])
				port = int(args[3])
			except ValueError:
				return
			self.dcc_connect(address, port)

	def on_ctcp(self, connection, event):
		if event.arguments()[0] == "ACTION":
			self.do_receive(connection, event, self.config.actions, event.target(), event.arguments()[1])

		
	def do_update(self, connection):
		httpcon = HTTPConnection(self.refreshHost)
		httpcon.request("GET", "/%s" % self.refreshTarget)
		httpresponse = httpcon.getresponse()
		self.config.parse(httpresponse.read())
		for i in self.config.channels:
			if self.config.channels[i] == "":
				print "Joining %s" % i
				connection.join(i)
			else:
				print "Joining %s with pass %s" % (i, self.config.channels[i])
				connection.join(i, self.config.channels[i])		

	def do_receive(self, connection, event, matches, source, string):
		string = string.strip()
		print "From %s: %s" % (source, string)
		params = { 'user': nm_to_n(event.source()) }
		httpcon = HTTPConnection(self.refreshHost)
		target = ""
		for r in matches:
			regex = re.compile(r)
			if regex.match(string) != None:
				target = regex.sub(matches[r], string)
				break
		if target != "":
			httpcon.request("GET", "/%s" % target)
			print "Requesting %s" % target
			httpresponse = httpcon.getresponse()
			data = httpresponse.read()
			for line in data.split('\n'):
				s = Template(line)
				line = s.safe_substitute(params)
				print "To %s: %s" % (source, line)
				connection.privmsg(source, line)


def main():
	import sys
	if len(sys.argv) < 4:
		print "Usage: NiaxBot <server[:port]> <nickname> <refresh>"
		sys.exit(1)

	s = sys.argv[1].split(":", 1)
	server = s[0]
	if len(s) == 2:
		try:
			port = int(s[1])
		except ValueError:
			print "Error: Erroneous port."
			sys.exit(1)
	else:
		port = 6667

	nickname = sys.argv[2]
	refresh = sys.argv[3]
	bot = NiaxBot(refresh, nickname, server, port)
	bot.start()

if __name__ == "__main__":
	main()
