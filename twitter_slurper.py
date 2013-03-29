#!/usr/bin/python
"""Twitter stream slurper."""
__author__ = 'Elmer de Looff <elmer.delooff@gmail.com>'
__version__ = '0.1'

# Built-in modules
import datetime
import logging
import Queue
import threading
import time

# Thirdparty modules
import requests
import simplejson

# Twitter keys
import twitter_credentials

API_DIRECTORY = 'http://openspace.slopjong.de/directory.json'


class TwitterError(Exception):
    """The Twitter API returned an error response."""


class TwitterFeedSlurper(threading.Thread):
    """Collects all new tweets by a user and puts them on a queue."""
    def __init__(self, space, twitter_name, queue, token, interval=300):
        super(TwitterFeedSlurper, self).__init__(
            name='TwitterFeedSlurper %s' % space)
        self.space = space
        self.twitter_name = twitter_name
        self.token = token
        self.check_interval = interval
        self.cutoff_date = datetime.datetime.now()
        self.cutoff_date -= datetime.timedelta(minutes=30)
        self.last_tweet_id = 1
        self.queue = queue
        self.daemon = True
        self.start()

    def run(self):
        """Periodically process tweets and then sleep again."""
        while True:
            try:
                self.process_tweets()
            except TwitterError, error:
                logging.warning('Twitter error: %s', error)
            time.sleep(self.check_interval)

    def process_tweets(self):
        """Loops through all received tweets and puts relevant info on a queue
        """
        for tweet in self.new_tweets():
            self.last_tweet_id = tweet['id']
            tweet['created_at'] = datetime.datetime.strptime(
                tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')
            if tweet['created_at'] > self.cutoff_date:
                link = 'https://twitter.com/%s/status/%d' % (
                    tweet['user']['screen_name'], tweet['id'])
                self.queue.put({'space': self.space,
                                'link': link,
                                'time': tweet['created_at'],
                                'text': tweet['text']})

    def new_tweets(self):
        """Returns a list of tweets in chronological order.

        The `since_id` parameter is provided to the API so that tweets that
        have already been collected once aren't collected again and again.
        """
        response = requests.get(
            'https://api.twitter.com/1.1/statuses/user_timeline.json',
            params={'screen_name': self.twitter_name,
                    'since_id': self.last_tweet_id},
            headers={'authorization': 'Bearer %s' % self.token}).json()
        if 'errors' in response:
            error = response['errors'][0]  # Only raise the first error
            raise TwitterError('%(code)d: %(message)s' % error)
        return reversed(response)


def all_space_info():
    """Returns a combined dictionary of all space APIs."""
    spaces = {}
    for name, api_url in requests.get(API_DIRECTORY).json().iteritems():
        status = get_space_api(name, api_url)
        if status is not None:
            spaces[name] = status
    return spaces


def format_twitter_update(tweet):
    """Returns a human readable update notification."""
    return """A new tweet by %(space)s!
        At %(time)s - %(link)s
        Tweet: %(text)s\n""" % tweet


def get_space_api(name, api_url, connect_timeout=1):
    """Returns the space API result if it is available."""
    try:
        return requests.get(api_url, timeout=connect_timeout).json()
    except requests.exceptions.RequestException:
        logging.warning('Could not request status for %s', name)
    except simplejson.scanner.JSONDecodeError:
        logging.warning('SpaceAPI request from %s is not JSON :(', name)


def get_twitter_bearer_token(consumer_key, consumer_secret):
    """Returns a Twitter OATH2 bearer token using the given key and secret.

    This uses the application-only authentication as explained on
    https://dev.twitter.com/docs/auth/application-only-auth
    """
    response = requests.post('https://api.twitter.com/oauth2/token',
                             auth=(consumer_key, consumer_secret),
                             data={'grant_type': 'client_credentials'}).json()
    if 'errors' in response:
        error = response['errors'][0]  # Only raise the first error
        raise TwitterError('%(label)s (%(code)d): %(message)s' % error)
    return response['access_token']


def twitter_report(token, interval=200, pause=.1):
    """Reports updates of all spaces that have a Twitter account listed."""
    queue = Queue.Queue()
    spaces = all_space_info()
    for space_name in sorted(spaces, key=lambda name: name.lower()):
        info = spaces[space_name]
        if 'contact' in info and 'twitter' in info['contact']:
            twitter_name = info['contact']['twitter']
            print '[%s] is on Twitter: %s' % (space_name, twitter_name)
            TwitterFeedSlurper(
                space_name, twitter_name, queue, token, interval=interval)
    while True:
        try:
            print format_twitter_update(queue.get(timeout=0.2))
            time.sleep(pause)
        except Queue.Empty:
            # This exists so that people can still interrupt this program
            pass


def main():
    """Simple commandline application that dumps tweets."""
    bearer_token = get_twitter_bearer_token(
        twitter_credentials.CONSUMER_KEY, twitter_credentials.CONSUMER_SECRET)
    twitter_report(bearer_token)


if __name__ == '__main__':
    main()
