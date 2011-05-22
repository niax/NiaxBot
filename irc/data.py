
class Nick:
    def __init__(self, server, nick, mode=' '):
        self.server = server
        self.nick = nick
        self.op = False
        self.voice = False
        self.halfop = False
        if mode == '@':
            self.op = True
        elif mode == '+':
            self.voice = True
        elif mode == '%':
            self.halfop = True

    def __repr__(self):
        modestr = ' '
        if self.op:
            modestr = '@'
        elif self.halfop:
            modestr = '%'
        elif self.voice:
            modestr = '+'
        return 'NICK: ' + modestr + self.nick 

