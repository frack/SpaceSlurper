#!/usr/bin/python
"""MediaWiki changes slurper."""
__author__ = 'Elmer de Looff <elmer.delooff@gmail.com>'
__version__ = '0.2'

# Built-in modules
import feedparser
import logging
import Queue
import threading
import time

WIKIS = {
        # Belgium
        'UrlLab': 'http://urlab.be/',
        'Void Warranties': 'http://www.voidwarranties.be/index.php/',
        'WhiteSpace': 'http://www.0x20.be/',
        # Luxemburg
        'syn2cat': 'http://wiki.hackerspace.lu/wiki/',
        # Netherlands
        'ACKspace': 'https://ackspace.nl/wiki/',
        'Bitlair': 'https://wiki.bitlair.nl/Pages/',
        'Frack': 'frack.nl/wiki/',
        'Hack42': 'https://hack42.nl/wiki/',
        'NURDSpace': 'http://nurdspace.nl/',
        'RevSpace': 'https://revspace.nl/',
        'Sk1llz': 'http://wiki.sk1llz.nl/',
        'Technologia Incognita': 'http://wiki.techinc.nl/index.php/',
        'TkkrLab': 'http://tkkrlab.nl/wiki/'}


class MediaWikiUpdateSlurper(threading.Thread):
    """Fetches MediaWiki changes and dumps article updates on a queue."""
    def __init__(self, space, wiki_url, queue, interval=300):
        super(MediaWikiUpdateSlurper, self).__init__(
            name='MediaWikiUpdateSlurper %s' % space)
        self.space = space
        self.wiki_base = wiki_url
        self.wiki_feed = wiki_url + 'Special:RecentChanges?feed=atom' # Hacky...
        self.update_interval = interval
        self.last_update_time = time.gmtime()
        self.queue = queue
        self.daemon = True
        self.start()

    def run(self):
        """Processes wiki changes and add them to the output queue."""
        while True:
            try:
                self.process_changes()
            except feedparser.xml.sax.SAXException:
                logging.warning('Could not process changes for %s', self.space)
            time.sleep(self.update_interval)

    def process_changes(self):
        """Process wiki changes, put article updates on the queue.

        We only consider changes that have a diff in the link. Changes without a
        diff seem to be changes like user creation / permission changes.
        """
        for change in self.wiki_changes():
            if 'diff' in change['link']:
                article_link = self.wiki_base + change['title']
                self.queue.put({
                    'article': article_link.replace(' ', '_'),
                    'author': change['author'],
                    'diff': change['link'],
                    'space': self.space,
                    'timestamp': int(time.mktime(change['updated_parsed'])),
                    'title': change['title']})

    def wiki_changes(self):
        """Yields all recent changes in chronological order."""
        for change in reversed(feedparser.parse(self.wiki_feed)['items']):
            if change['updated_parsed'] > self.last_update_time:
                self.last_update_time = change['updated_parsed']
                yield change


def format_wiki_update(change):
    """Returns a human readable change notification."""
    return """A new wiki update at %(space)s!
        %(author)s made a change to the article %(title)s
        Link: %(article)s
        Diff: %(diff)s
        """ % change

def wiki_update_printer(interval=300, pause=2):
    """Prints wiki updates for all the hackerspaces in the BeNeLux."""
    queue = Queue.Queue()
    for name, wiki in WIKIS.iteritems():
        MediaWikiUpdateSlurper(name, wiki, queue, interval=interval)
    while True:
        try:
            print format_wiki_update(queue.get(timeout=0.2))
            time.sleep(pause)
        except Queue.Empty:
            # This exists so that people can still interrupt this program
            pass


def main():
    """Start the commandline demonstration application."""
    import optparse
    import sys
    parser = optparse.OptionParser()
    parser.add_option('-i', '--interval', type='int', default=300,
                      help='Interval between wiki recent change feed updates.')
    parser.add_option('-p', '--pause', type='float', default=2,
                      help='Pause between subsequent updates.')
    options, _arguments = parser.parse_args()
    try:
        wiki_update_printer(options.interval, options.pause)
    except KeyboardInterrupt:
        print '\nThanks for playing!'
        sys.exit()


if __name__ == '__main__':
    main()
