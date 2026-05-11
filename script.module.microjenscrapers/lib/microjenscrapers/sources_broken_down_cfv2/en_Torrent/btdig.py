# -*- coding: utf-8 -*-

'''
    MicroJen Scrapers module

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import re

#import requests

from six import ensure_text

from microjenscrapers import cfScraper
from microjenscrapers import parse_qs, urljoin, urlencode, quote_plus
from microjenscrapers.modules import debrid
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import source_utils
from microjenscrapers.modules import log_utils

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['btdig.com']
        self.base_link = 'https://www.btdig.com'
        self.search_link = '/search?q=%s&order=0'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('btdig0 - Exception', 1)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('btdig1 - Exception', 1)
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
            log_utils.log('btdig2 - Exception', 1)
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

            #r = client.request(url)
            #r = requests.get(url).content
            r = cfScraper.get(url).content
            r = ensure_text(r, errors='replace').replace('&nbsp;', ' ')
            r = client.parseDOM(r, 'div', attrs={'style': 'display:table;width:100%;text-align:left'})
            posts = client.parseDOM(r, 'div', attrs={'class': 'one_result'})
            #log_utils.log('posts_is: '+str(posts))
            for post in posts:

                links = client.parseDOM(post, 'div', attrs={'class': 'fa fa-magnet'})[0]
                url = client.parseDOM(links, 'a', ret='href')[0]
                url = client.replaceHTMLCodes(url).split('&tr=')[0]
                name = url.split('&dn=')[1]
                if not query in cleantitle.get_title(name): continue

                quality, info = source_utils.get_release_quality(name, url)
                try:
                    size = client.parseDOM(post, 'span', attrs={'class': 'torrent_size'})[0]
                    dsize, isize = source_utils._size(size)
                except:
                    dsize, isize = 0.0, ''

                info.insert(0, isize)

                info = ' | '.join(info)

                sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': url, 'info': info,
                                'direct': False, 'debridonly': True, 'size': dsize, 'name': name})

            return sources
        except:
            log_utils.log('btdig3 - Exception', 1)
            return sources

    def resolve(self, url):
        return url
