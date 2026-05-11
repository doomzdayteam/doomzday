# -*- coding: utf-8 -*-

'''
    MicroJen Scrapers module
'''

import re

from six import ensure_text

from microjenscrapers import parse_qs, urljoin, urlencode, quote_plus
from microjenscrapers.modules import debrid
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import source_utils
from microjenscrapers.modules import log_utils
#from microjenscrapers import cfScraper

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['btdig.com']
        self.base_link = 'https://www.torrentdownload.info'
        self.search_link = '/search?q=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('tdl0 - Exception', 1)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('tdl1 - Exception', 1)
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None: return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            log_utils.log('tdl2 - Exception', 1)
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if debrid.status() is False:
                return sources

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            query = '%s s%02de%02d' % (data['tvshowtitle'], int(data['season']), int(data['episode']))\
                                       if 'tvshowtitle' in data else '%s %s' % (data['title'], data['year'])
            query = re.sub(u'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query).lower()

            url = urljoin(self.base_link, self.search_link % quote_plus(query))

            r = client.request(url)
            #r = cfScraper.get(url).content
            r = ensure_text(r, errors='replace').strip()
            posts = client.parseDOM(r, 'table', attrs={'class': 'table2', 'cellspacing': '0'})[1]
            posts = client.parseDOM(posts, 'tr')[1:]
            for post in posts:
                try:
                    links = client.parseDOM(post, 'a', ret='href')[0]
                    links = client.replaceHTMLCodes(links).lstrip('/')
                    hash = links.split('/')[0]
                    name = links.split('/')[1]
                    url = 'magnet:?xt=urn:btih:{}'.format(hash)
                    if not query in cleantitle.get_title(name): continue

                    quality, info = source_utils.get_release_quality(name)
                    try:
                        size = client.parseDOM(post, 'td', attrs={'class': 'tdnormal'})[1]
                        dsize, isize = source_utils._size(size)
                    except:
                        dsize, isize = 0.0, ''

                    info.insert(0, isize)

                    info = ' | '.join(info)

                    sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': url, 'info': info,
                                    'direct': False, 'debridonly': True, 'size': dsize, 'name': name})
                except:
                    pass:

            return sources
        except:
            log_utils.log('tdl3 - Exception', 1)
            return sources

    def resolve(self, url):
        return url
