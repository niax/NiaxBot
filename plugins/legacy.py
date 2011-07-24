import irc.signals
import irc.settings
from httplib import HTTPConnection
from string import Template
from time import time
import urllib
import re
import logging

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

logger = logging.getLogger("legacy")
config = Config()
floodProtect = {}
        
def welcomed(server, arg):
    # At this point we're properly connected to the server, so let's grab the config file and go from there
    do_update(server)

def on_privmsg(server, message, query, prefix):
    # Received a private message
    # Special hardcoded PM trigger, forces config reload
    if message == "reload":
        do_update(server)
    else:
        do_receive(server, message, query, prefix, config.pm)

def on_pubmsg(server, message, query, prefix):
    # Received a message in a channel
    do_receive(server, message, query, prefix, config.public)

#def on_ctcp(server, message, query, prefix):
def on_ctcp(server, command, message, query, prefix):
    # Handle CTCP ACTION (/me) commands
    if command == "ACTION":
        do_receive(server, message, query, prefix, config.actions)

def do_update(server):
    """Pull in a new configuration file"""
    # Create the connection and request the target
    try:
        refreshHost = irc.settings.get('legacy_refreshHost')
        refreshTarget = irc.settings.get('legacy_refreshTarget')

        if refreshHost == None:
            logger.warn("Refresh Host is not set (please set legacy_refreshHost)")
            return
        if refreshTarget == None:
            logger.warn("Refresh Target is not set (please set legacy_refreshTarget)")
            return
        httpcon = HTTPConnection(refreshHost)
        httpcon.request("GET", "/%s" % refreshTarget)
        # Get the response and parse it
        httpresponse = httpcon.getresponse()
        config.parse(httpresponse.read())
    except Exception, ex:
        logger.exception("Error updating config")

    # Join all the channels in the config
    for i in config.channels:
        if config.channels[i] == "":
            server.join(i)
        else:
            server.join(i, key=config.channels[i])        

def do_receive(server, message, query, prefix, matches):
    """Handles receiving messages from any source"""
    # Grab the time immediately so we know exactly when this message was received (or at least as close as we can get)
    timeRecv = time()    
    # Filter out the crap
    message = message.strip()
    # Create the POST params
    params = { 'user': prefix['nick'] }
    target = ""
    # For all of the regex it could be, see if it matches, and if it is set the target given the replacement string.
    for r in matches:
        regex = re.compile(r)
        if regex.match(message) != None:
            logger.debug("Matches against: " + r)
            target = regex.sub(matches[r], message)
            break
    if target != "":
        # We have a target, check if the source is under flood protection
        if query.name in floodProtect:
            timeDiff = timeRecv - floodProtect[query.name]
            if timeDiff < 5: # Hardcoded 5 second anti-flood per channel - change here if required
                return
        # Update the antiflood mapping
        floodProtect[query.name] = timeRecv
        # Do the request
        params = urllib.urlencode(params)
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        try:
            refreshHost = irc.settings.get('legacy_refreshHost')
            if refreshHost == None:
                logger.warn("Refresh Host is not set (please set legacy_refreshHost)")
                return
            # Set up the connection
            httpcon = HTTPConnection(refreshHost)
            httpcon.request("POST", "/%s" % target, params, headers)
            logger.info("Requesting %s" % target)
            httpresponse = httpcon.getresponse()
            data = httpresponse.read()
            if httpresponse.status != 200:
                # The server returned something other than 200 (OK) so print out what happened
                logger.warn("Returned status code %d" % httpresponse.status)
                logger.warn("Content:\n%s" % data)
            else:    
                # The server returned OK so put that to the channel, line by line
                for line in data.split('\n'):
                    line = line.strip()
                    if len(line) == 0:
                        continue
                    query.say(line)
        except Exception, ex:
            logger.exception("Error fetching")

irc.signals.add('server motd end', welcomed)
irc.signals.add('message private', on_privmsg)
irc.signals.add('message public', on_pubmsg)
irc.signals.add('ctcp cmd', on_ctcp)
