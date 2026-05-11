# -*- coding: utf-8 -*-

'''
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

from microjenscrapers import urljoin, quote_plus

from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import source_utils
from microjenscrapers.modules import dom_parser



class source:
    def __init__(self):
        self.priority = 1
        self.language = ['gr']
        self.domains = ['tainiesonline.top']
        self.base_link = 'https://tainiesonline.top'
        self.search_link = 'search/?q=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = self.__search([localtitle] + source_utils.aliases_to_array(aliases), year, 'movies')
            if not url and title != localtitle: url = self.__search([title] + source_utils.aliases_to_array(
                aliases),year, 'movies')
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = self.__search([localtvshowtitle] + source_utils.aliases_to_array(aliases), year, 'series')
            if not url and tvshowtitle != localtvshowtitle: url = self.__search(
                [tvshowtitle] + source_utils.aliases_to_array(aliases), year, 'series')
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return

            url = url[:-1] if url.endswith('/') else url
            url += '/seasons/%d/episodes/%d' % (int(season), int(episode))
            return url
        except:
            return

    def __search(self, titles, year, content):
        try:

            query = [self.search_link % (quote_plus(cleantitle.getsearch(i))) for i in titles]

            query = [urljoin(self.base_link, i) for i in query]

            t = [cleantitle.get(i) for i in set(titles) if i] #cleantitle.get(titles[0])

            for u in query:
                try:
                    r = client.request(u)

                    r = client.parseDOM(r, 'div', attrs={'class': 'tab-content clearfix'})

                    if content == 'movies':
                        r = client.parseDOM(r, 'div', attrs={'id': 'movies'})
                    else:
                        r = client.parseDOM(r, 'div', attrs={'id': 'series'})

                    r = [dom_parser.parse_dom(i, 'figcaption') for i in r]
                    data = [(i[0].attrs['title'], dom_parser.parse_dom(i[0].content, 'a', req='href')) for i in r if i]
                    data = [i[1][0].attrs['href'] for i in data if cleantitle.get(i[0]) in t]
                    if data: return source_utils.strip_domain(data[0])
                    else:
                        url = [dom_parser.parse_dom(i[0].content, 'a', req='href') for i in r]
                        data = client.request(url[0][0]['href'])
                        data = re.findall('<h1><a.+?">(.+?)\((\d{4})\).*?</a></h1>', data, re.DOTALL)[0]
                        if titles[0] in data[0] and year == data[1]: return source_utils.strip_domain(url[0][0]['href'])
                except:pass

            return
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []

        try:
            if not url:
                return sources

            query = urlparse.urljoin(self.base_link, url)
            r = client.request(query)
            links = client.parseDOM(r, 'tr', attrs={'data-id': '\d+'})
            for i in links:
                url = re.findall( "data-bind=.+?site\(\'([^']+)\'", i, re.DOTALL)[0]
                quality = 'SD'
                lang, info = 'gr', 'SUB'
                valid, host = source_utils.is_host_valid(url, hostDict)

                sources.append({'source': host, 'quality': quality, 'language': lang, 'url': url, 'info': info,
                                'direct':False,'debridonly': False})

            return sources
        except:
            return sources

    def resolve(self, url):
        return url
