#!/usr/bin/python
"""Twitter stream slurper."""
__author__ = 'Elmer de Looff <elmer.delooff@gmail.com>'
__version__ = '0.1'

# Built-in modules
import logging

# Thirdparty modules
import requests
import simplejson


API_DIRECTORY = 'http://openspace.slopjong.de/directory.json'


def all_space_info():
    """Returns a combined dictionary of all space APIs."""
    spaces = {}
    for name, api_url in requests.get(API_DIRECTORY).json().iteritems():
        status = get_space_api(name, api_url)
        if status is not None:
            spaces[name] = status
    return spaces


def get_space_api(name, api_url, connect_timeout=1):
    """Returns the space API if it is available."""
    try:
        return requests.get(api_url, timeout=connect_timeout).json()
    except requests.exceptions.RequestException:
        logging.warning('Could not request status for %s', name)
    except simplejson.scanner.JSONDecodeError:
        logging.warning('SpaceAPI request from %s is not JSON :(', name)


def twitter_report():
    """Reports twitter usage of the various spaces."""
    spaces = all_space_info()
    for name in sorted(spaces, key=lambda name: name.lower()):
        info = spaces[name]
        if 'contact' in info and 'twitter' in info['contact']:
            format_string = '[%s] is on Twitter: %s'
            print format_string % (name, status['contact']['twitter'])


def main():
    """Simple commandline application that dumps tweets."""
    twitter_report()


if __name__ == '__main__':
    main()
