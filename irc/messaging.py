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

    def _namelist(self, parameters):
        (server, params, prefix) = parameters
        if server == self.server and params[-2] == self.name: # params[0] is the channel
            for user in params[-1].split(' '):
                self.users.append(user)

    def _synchronized(self, parameters):
        (server, params, prefix) = parameters
        if server == self.server and params[-2] == self.name:
            signals.emit('channel synchronized', (server, self))
            self.say(str(self.users))


# Signal Handlers
def _process_ctcp_cmd(message):
    if message.startswith('\001') and message.endswith('\001'): # Then it's a CTCP command
        message = message[1:-2] # Trim either end
        return message
    return None

def _join_handler(arguments):
    (server, parameters, prefix) = arguments
    server._add_channel(parameters[0])

def _privmsg_handler(arguments):
    (server, parameters, prefix) = arguments
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

