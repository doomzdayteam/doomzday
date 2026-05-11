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
from microjenscrapers.modules import dom_parser



class source:
    def __init__(self):
        self.priority = 1
        self.language = ['gr']
        self.domains = ['gamatotv.me']
        self.base_link = 'https://gamatotv.site'
        self.search_link = '/groups/group/search?q=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = self.__search([localtitle] + source_utils.aliases_to_array(aliases), year)
            if not url and title != localtitle: url = self.__search([title] + source_utils.aliases_to_array(aliases),year)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = self.__search([localtvshowtitle] + source_utils.aliases_to_array(aliases), year)
            if not url and tvshowtitle != localtvshowtitle: url = self.__search(
                [tvshowtitle] + source_utils.aliases_to_array(aliases), year)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return
            url = [{'url': url, 'season': season, 'episode': episode}]
            return url
        except:
            return

    def __search(self, titles, year):
        try:
            query = [self.search_link % (quote_plus(cleantitle.getsearch(i +' '+year))) for i in titles]

            query = [urljoin(self.base_link, i) for i in query]
            t = [cleantitle.get(i) for i in set(titles) if i]
            
            for u in query:
                try:
                    r = client.request(u)
                    r = client.parseDOM(r, 'div', attrs={'class': 'bd'})
                    for i in r:
                        r = dom_parser.parse_dom(i, 'h3')
                        r = dom_parser.parse_dom(r, 'a')
                        title = r[0][1]
                        y = re.findall('(\d{4})', title, re.DOTALL)[0]
                        if year == y:
                            return source_utils.strip_domain(r[0][0]['href'])
                except: 
                    pass
            return
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []

        try:
            if not url:
                return sources

            if type(url) is list:
                url = url[0]
                query, season, episode = url['url'], url['season'], url['episode']
                query = urljoin(self.base_link, query)
                data = client.request(query)
                data = client.parseDOM(data, 'div', attrs={'class': 'xg_module_body xg_user_generated'})[0]

                pattern = '>season\s*%d</(.+?)(?:</strong><br/>\s*<br/>|<strong><span)' % int(season)
                data  = re.findall(pattern, data, re.DOTALL|re.I)

                links = dom_parser.parse_dom(data, 'a')
                links = [i.attrs['href'] for i in links if int(episode) == int(i.content)]
                for url in links:
                    if 'youtube' in url: raise Exception()
                    quality = 'SD'
                    lang, info = 'gr', 'SUB'
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if 'hdvid' in host: valid = True
                    if not valid: continue

                    sources.append({'source': host, 'quality': quality, 'language': lang, 'url': url, 'info': info,
                                    'direct': False, 'debridonly': False})

            else:
                query = urljoin(self.base_link, url)
                r = client.request(query)
                links = client.parseDOM(r, 'div', attrs={'class': 'xg_user_generated'})
                links = dom_parser.parse_dom(links, 'a')

                for i in links:
                    url = i[0]['href']
                    if 'youtube' in url: continue
                    quality = 'SD'
                    lang, info = 'gr', 'SUB'
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if 'hdvid' in host: valid = True
                    if not valid: continue

                    sources.append({'source': host, 'quality': quality, 'language': lang, 'url': url, 'info': info,
                                    'direct':False,'debridonly': False})

            return sources
        except:
            return sources

    def resolve(self, url):
        return url
