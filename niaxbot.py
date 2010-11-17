from ircbot import SingleServerIRCBot
from irclib import nm_to_n, nm_to_h, irc_lower, ip_numstr_to_quad, ip_quad_to_numstr
from httplib import HTTPConnection
from string import Template
from time import time
import urllib
import re

class Config:
	"""Config Parser, works on a state basis with the states being defined as ParseState"""
	class ParseState:
		"""States that the config parser can be in."""
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
		"""Parse a config file into the fields of this instance"""
		# Clear everything out.
		state = Config.ParseState.NoState
		self.channels = {}
		self.actions = {}
		self.public = {}
		self.pm = {}
		# lastline is used to remember the previous line. If it is blank then a pair has just been found or no pairs have been found
		lastline = ""
		# For every line...
		for l in config.split('\n'):
			# Strip off the whitespace
			l = l.strip()
			# Remove empty lines or comments
			if l.startswith("#") or l == "":
				continue
			print l

			# If it starts with === then it's a state change (section marker)
			if l.startswith("==="):
				state = Config.ParseState.state(l)
			elif state == Config.ParseState.Channels:
				# If not and we're in the channel state, then read in the channels
				split = l.split()
				if len(split) == 1:
					# Means there's no password, so put as blank
					self.channels["#%s" % split[0]] = ""
				else:
					# Include the password
					self.channels["#%s" % split[0]] = split[1]
			else:
				if lastline != "":
					# This line has a pair (a regex trigger, this line being the target) so put it in the correct trigger set.
					if state == Config.ParseState.Public:
						self.public[lastline] = l		
					elif state == Config.ParseState.PM:
						self.pm[lastline] = l
					elif state == Config.ParseState.Action:
						self.actions[lastline] = l
					lastline = "" # Reset the lastline for the next pairing
				else:
					lastline = l
		
		

class NiaxBot(SingleServerIRCBot):
	"""A simple IRC bot which gets its config and responses through HTTP"""
	def __init__(self, refresh, nickname, server, port=6667, password=None):
		# Split the refresh path such that we have the host and a target
		rSplit = refresh.split('/')
		self.refreshHost = rSplit[0]
		self.refreshTarget = '/'.join(rSplit[1:])
		self.config = Config() # Init the config parser
		self.floodProtect = {} # Dictionary for flood protect goes source->last time triggered
		print "Target is on %s at %s" % (self.refreshHost, self.refreshTarget)
		SingleServerIRCBot.__init__(self, [(server, port, password)], nickname, nickname)

	def on_nicknameinuse(self, connection, event):
		# Nickname in use so add an _ and try again
		print "Nick in use"
		connection.nick(connection.get_nickname() + "_")

	def on_welcome(self, connection, event):
		# At this point we're properly connected to the server, so let's grab the config file and go from there
		print "Wecomed"
		self.do_update(connection)

	def on_privmsg(self, connection, event):
		# Received a private message
		cmd = event.arguments()[0]
		# Special hardcoded PM trigger, forces config reload
		if cmd == "reload":
			self.do_update(connection)
		self.do_receive(connection, event, self.config.pm, nm_to_n(event.source()), cmd)

	def on_pubmsg(self, connection, event):
		# Received a message in a channel
		self.do_receive(connection, event, self.config.public, event.target(), event.arguments()[0])

	def on_dccmsg(self, connection, event):
		# Received a DCC Message (just echo back)
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
		# Handle CTCP ACTION (/me) commands
		if event.arguments()[0] == "ACTION":
			self.do_receive(connection, event, self.config.actions, event.target(), event.arguments()[1])

		
	def do_update(self, connection):
		"""Pull in a new configuration file"""
		# Create the connection and request the target
		httpcon = HTTPConnection(self.refreshHost)
		httpcon.request("GET", "/%s" % self.refreshTarget)
		# Get the response and parse it
		httpresponse = httpcon.getresponse()
		self.config.parse(httpresponse.read())

		# Join all the channels in the config
		for i in self.config.channels:
			if self.config.channels[i] == "":
				print "Joining %s" % i
				connection.join(i)
			else:
				print "Joining %s with pass %s" % (i, self.config.channels[i])
				connection.join(i, self.config.channels[i])		

	def do_receive(self, connection, event, matches, source, string):
		"""Handles receiving messages from any source"""
		# Grab the time immediately so we know exactly when this message was received (or at least as close as we can get)
		timeRecv = time()	
		# Filter out the crap
		string = string.strip()
		print "From %s: %s" % (source, string)
		# Create the POST params
		params = { 'user': nm_to_n(event.source()) }
		# Set up the connection
		httpcon = HTTPConnection(self.refreshHost)
		target = ""
		# For all of the regex it could be, see if it matches, and if it is set the target given the replacement string.
		for r in matches:
			regex = re.compile(r)
			if regex.match(string) != None:
				target = regex.sub(matches[r], string)
				break
		if target != "":
			# We have a target, check if the source is under flood protection
			if source in self.floodProtect:
				timeDiff = timeRecv - self.floodProtect[source]
				if timeDiff < 30: # Hardcoded 30 second anti-flood per channel - change here if required
					return
			# Update the antiflood mapping
			self.floodProtect[source] = timeRecv
			# Do the request
			params = urllib.urlencode(params)
			headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
			httpcon.request("POST", "/%s" % target, params, headers)
			print "Requesting %s" % target
			httpresponse = httpcon.getresponse()
			data = httpresponse.read()
			if httpresponse.status != 200:
				# The server returned something other than 200 (OK) so print out what happened
				print "Returned status code %d" % httpresonse.status
				print "Content:"
				print data
			else:	
				# The server returned OK so put that to the channel, line by line
				for line in data.split('\n'):
					line = line.strip()
					if len(line) == 0:
						continue
					print "To %s: %s" % (source, line)
					connection.privmsg(source, line)


def main():
	import sys
	if len(sys.argv) < 4:
		print "Usage: NiaxBot <server[:port[:password]]> <nickname> <refresh>"
		sys.exit(1)

	s = sys.argv[1].split(":")
	server = s[0]
	password = None
	if len(s) > 1:
		try:
			port = int(s[1].strip(':'))
		except ValueError:
			print "Error: Erroneous port (%s)." % s[1]
			sys.exit(1)
		if len(s) == 3:
			password = s[2]
	else:
		port = 6667

	nickname = sys.argv[2]
	refresh = sys.argv[3]
	bot = NiaxBot(refresh, nickname, server, port, password)
	bot.start()

if __name__ == "__main__":
	main()
