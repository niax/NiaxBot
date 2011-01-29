import signals

class Query(object):
    def __init__(self, server, name):
        self.server = server
        self.name = name

    def is_channel(self):
        return False

    def say(self, tosay):
        self.server.privmsg(self.name, tosay)

class IrcChannel(Query):
    def __init__(self, server, name):
        super(IrcChannel, self).__init__(server, name)
        self.users = []
        signals.add_first('server name reply', self._namelist)
        signals.add_first('server name complete', self._synchronized)

    def is_channel(self):
        return True

    def _namelist(self, server, params, prefix):
        if server == self.server and params[-2] == self.name: # params[0] is the channel
            for user in params[-1].split(' '):
                self.users.append(user)

    def _synchronized(self, server, params, prefix):
        if server == self.server and params[-2] == self.name:
            signals.emit('channel synchronized', (server, self))

    def _user_join(self, prefix):
        self.users.append(prefix['nick'])
        signals.emit('channel join', (self, prefix))

    def _user_part(self, prefix):
        self.users.remove(prefix['nick'])
        signals.emit('channel part', (self, prefix))


# Signal Handlers
def _process_ctcp_cmd(message):
    if message.startswith('\001') and message.endswith('\001'): # Then it's a CTCP command
        message = message[1:-2] # Trim either end
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
        signals.emit('ctcp cmd', (server, message, query, prefix))
    else:
        signals.emit('message private', (server, message, query, prefix))


# Add Signal Handlerss
signals.add_first('event privmsg', _privmsg_handler)
signals.add_first('event join', _join_handler)
signals.add_first('event part', _part_handler)
