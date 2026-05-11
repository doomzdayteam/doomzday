# -*- coding: utf-8 -*-

# - Converted to py3/2 and fixed for dev name


import re

try: from urlparse import parse_qs, urlparse
except ImportError: from urllib.parse import parse_qs, urlparse
try: from urllib import urlencode
except ImportError: from urllib.parse import urlencode

from six import ensure_str

from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import source_utils
from microjenscrapers.modules import log_utils


class source:
    def __init__(self):
        self.priority = 0
        self.language = ['en']
        self.domains = ['dwatchseries.to', 'swatchseries.to']
        self.base_link = 'https://www1.watch-series.la'

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('SwatchSeries - Exception', 1)
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            tit = cleantitle.get_query_(url['tvshowtitle'])
            url = '%s/episode/%s_s%s_e%s.html' % (self.base_link, tit, season, episode)
            return url
        except:
            log_utils.log('SwatchSeries - Exception', 1)
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []

            if url is None:
                return sources
            hostDict = hostprDict + hostDict
            r = client.request(url)
            links = re.compile(r'''onclick="if \(confirm\('Delete link (.+?)'\)\)''', re.DOTALL).findall(r)
            links = [x for y, x in enumerate(links) if x not in links[:y]]
            for i in links:
                try:
                    url = i
                    url = client.replaceHTMLCodes(url)
                    url = ensure_str(url)
                    h = re.findall('([\w]+[.][\w]+)$', urlparse(url.strip().lower()).netloc)[0]
                    valid, host = source_utils.is_host_valid(h, hostDict)
                    if valid:
                        sources.append({'source': host, 'quality': 'SD', 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})
                except:
                    pass

            return sources
        except:
            log_utils.log('SwatchSeries - Exception', 1)
            return sources

    def resolve(self, url):
        return url
