import logging
import twitter
import oauth2 as oauth
from cgi import parse_qsl

import irc.signals
import irc.settings

request_token_url = 'https://api.twitter.com/oauth/request_token'
access_token_url = 'https://api.twitter.com/oauth/access_token'
authorization_url = 'https://api.twitter.com/oauth/authorize'
signin_url = 'https://api.twitter.com/oauth/authenticate'


def cmd_authorize(args): 
    # Use sample from get_access_token.py in python-twitter
    consumer = get_consumer()
    if consumer == None:
        return
    client = oauth.Client(consumer)

    logger.debug('Requesting temp token from Twitter')
    resp, content = client.request(request_token_url,  'GET')
    if resp['status'] != '200':
        logger.error('Failed to get temp token from Twitter. Response code %s' % resp['status'])
        return

    # Global this so we can get it when we come back
    global request_token
    request_token = dict(parse_sql(content))
    logger.info('To authorize this, go to %s?oauth_token=%s' % (authorization_url, request_token['oauth_token'])
    logger.info('And then use /twitter_auth_complete <pin> to complete')

def cmd_authorize_complete(args):
    pin = args[0]
    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
    token.set_verifier(pincode)
    consumer = get_consumer()
    if consumer == None:
        return
    client = oauth.Client(consumer, token)
    resp, content = client.request(access_token_url, 'POST')
    access_token = dict(parse_qsl(content))
    irc.settings.set('twitter.oauth.access_token', access_token['oauth_token'])
    irc.settings.set('twitter.oauth.access_secret', access_token['oauth_token_secret'])

def get_consumer():
    consumer_key = irc.settings.get('twitter.oauth.consumer_key')
    if consumer_key == None:
        logger.error('Must set twitter.oauth.consumer_key')
        return None

    consumer_secret = irc.settings.get('twitter.oauth.consumer_secret)
    if consumer_secret == None:
        logger.error('Must set twitter.oauth.consumer_secret')
        return None

    return oauth.Consumer(key=consumer_key, secret=consumer_secret)


irc.signals.add('twitter_auth', cmd_authorize)
irc.signals.add('twitter_auth_complete', cmd_authorize_complete)


logger = logging.getLogger('twitter')
