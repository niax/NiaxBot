import signals

signal_mappings = {
    # Server info on connect
    '001': 'server welcomed',
    '002': 'server info host',
    '003': 'server info created',
    '004': 'server info modes',
    '005': 'server bounce',

    '221': 'user mode changed',
    
    # Server stats on connect
    '251': 'network count user',
    '252': 'network count op',
    '253': 'network count unknowns',
    '254': 'network count channels',
    '255': 'server count user',
    
    # Names reply
    '353': 'server name reply',
    '366': 'server name complete',
    
    # MOTD
    '372': 'server motd content',
    '375': 'server motd start',
    '376': 'server motd end',

}

def _signal_rewrite(new):
    """ Returns a function that re-emits a signal under a different name as defined by new """
    return lambda params: signals.emit(new, params)

# Add rewrite signal handlers
for mapping in signal_mappings.keys():
    signals.add_first(('event %s' % mapping), _signal_rewrite(signal_mappings[mapping]))

