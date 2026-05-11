# -*- coding: UTF-8 -*-

import re

from six import ensure_text

from microjenscrapers import cfScraper
from microjenscrapers import parse_qs, urljoin, urlencode, quote_plus
from microjenscrapers.modules import cleantitle, client, source_utils, log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['project-free-tv.ag','my-project-free.tv']
        self.base_link = 'https://projecfreetv.co'
        self.search_link = '/episode/%s/'


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']

            hdlr = 's%02de%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s-s%02de%02d' % (data['tvshowtitle'], int(data['season']), int(data['episode']))
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url).replace('+', '-')

            r = cfScraper.get(url).content
            r = ensure_text(r, errors='ignore')
            try:
                data = re.compile('<a href="(.+?)" target="_blank" rel="nofollow" title.+?').findall(r)
                for url in data:
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        quality, info = source_utils.get_release_quality(url, url)
                        sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})
            except:
                log_utils.log('projectfree2 - Exception', 1)
                pass
            return sources
        except:
            log_utils.log('projectfree3 - Exception', 1)
            return sources


    def resolve(self, url):
        return url

