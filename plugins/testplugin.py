import irc.signals
import logging

def private(server, message, query, prefix):
    if query.is_channel():
        logger.info('%s %s: %s' % (query.name, prefix['nick'], message))
    else:
        logger.info('PM %s: %s' % (prefix['nick'], message))
        for i in range(10):
            server.privmsg(prefix['nick'], message)

def ctcp_cmd(server, message, query, prefix):
    if query.is_channel():
        logger.info('CTCP %s %s: %s' % (query.name, prefix['nick'], message))
    else:
        logger.info('PM CTCP %s: %s' % (prefix['nick'], message))

logger = logging.getLogger('irc')

irc.signals.add('message private', private)
irc.signals.add('ctcp cmd', ctcp_cmd)
