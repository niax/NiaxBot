import re

import signals
import logging
from data import Nick

class Query(object):
    def __init__(self, server, name):
        self.server = server
        self.name = name

    def is_channel(self):
        return False

    def say(self, tosay):
        self.server.privmsg(self.name, tosay)

    def ctcp(self, message):
        self.server.privmsg(self.name, '\001%s\001' % message)

    def ctcp_reply(self, message):
        self.server.notice(self.name, '\001%s\001' % message)

class IrcChannel(Query):
    namelist_split = re.compile(' *(?P<mode>[ @+%])(?P<nick>\S+)') # Match something then a non-whitespace
    def __init__(self, server, name):
        super(IrcChannel, self).__init__(server, name)
        self.nicks = {}
        signals.add_first('server name reply', self._namelist)
        signals.add_first('server name complete', self._synchronized)
        signals.add_first('server topic', self._topic)
        signals.add_first('server topic_by', self._topic_by)
        signals.add_first('event mode', self._mode)
        signals.add_first('event nick', self._nick_change)
        signals.add('command names', self._names)

    def _names(self, args):
        if args == self.name:
            for nick in self.nicks:
                logger.info("%s - %s" % (nick, self.nicks[nick]))

    def is_channel(self):
        return True

    def _namelist(self, server, params, prefix):
        if server == self.server and params[-2] == self.name: # params[0] is the channel
            nicks = [] #TODO: Make this do things
            for user in self.namelist_split.finditer(params[-1]):
                nick = user.group('nick')
                if nick in self.nicks:
                    continue # Ignore this nick
                self.nicks[nick] = Nick(server, nick, mode=user.group('mode'))
            signals.emit('channel name reply', (server, self, nicks))

    def _synchronized(self, server, params, prefix):
        if server == self.server and params[-2] == self.name:
            signals.emit('channel synchronized', (server, self))

    def _user_join(self, prefix):
        nick = prefix['nick']
        if not nick in self.nicks:
            self.nicks[nick] = Nick(self.server, nick)
            signals.emit('channel join', (self, prefix))

    def _user_part(self, prefix):
        nick = prefix['nick']
        if nick in self.nicks:
            del self.nicks[nick]
            signals.emit('channel part', (self, prefix))

    def _topic(self, server, params, prefix):
        logging.info((server, params, prefix))

    def _topic_by(self, server, params, prefix):
        logging.info((server, params, prefix))

    def _mode(self, server, params, prefix):
        logging.info((server, params, prefix))

    def _nick_change(self, server, params, prefix):
        oldnick = prefix['nick']
        (newnick,) = params
        if oldnick in self.nicks: # If this is a nick change we care about, update our Nick record
            self.nicks[newnick] = self.nicks[oldnick]
            del self.nicks[oldnick] # Remove the previous nick
            self.nicks[newnick].nick = newnick # Set the nick to the new nick


# Signal Handlers
def _process_ctcp_cmd(message):
    if message.startswith('\001') and message.endswith('\001'): # Then it's a CTCP command
        message = message[1:-1] # Trim either end
        return message
    return None

def _join_handler(server, parameters, prefix):
    if prefix['nick'] == server.nickname:
        server._add_channel(parameters[0]) # This is us joining a channel
    else:
        server._get_query(parameters[0])._user_join(prefix)

def _part_handler(server, parameters, prefix):
    target = parameters[0]
    if prefix['nick'] == server.nickname:
        server._del_channel(target)
    else:
        server._get_query(target)._user_part(prefix)


def _privmsg_handler(server, parameters, prefix):
    message = parameters[-1]
    ctcp_cmd = _process_ctcp_cmd(message)
    target = parameters[-2]
    if target  == server.nickname:
        target = prefix["nick"]
    query = server._get_query(target)
    if ctcp_cmd != None:
        split = ctcp_cmd.find(' ')
        message = ''
        if split > -1:
            message = ctcp_cmd[split:]
            ctcp_cmd = ctcp_cmd[:split]
        signals.emit('ctcp cmd', (server, ctcp_cmd, message, query, prefix))
    else:
        if type(query) == IrcChannel: # If we're in a public channel
            signals.emit('message public', (server, message, query, prefix))
        else:
            signals.emit('message private', (server, message, query, prefix))

def _mode_handler(server, parameters, prefix):
    logger.info('%s - %s' % (prefix, parameters))



logger = logging.getLogger('irc.messaging')
# Add Signal Handlerss
signals.add_first('event privmsg', _privmsg_handler)
signals.add_first('event join', _join_handler)
signals.add_first('event part', _part_handler)
signals.add_first('event mode', _mode_handler)
