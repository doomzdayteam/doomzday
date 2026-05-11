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

import re, base64

from six import ensure_text

from microjenscrapers import urljoin, quote_plus

from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import source_utils
from microjenscrapers.modules import dom_parser


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['gr']
        self.domains = ['liomenoi.com']
        self.base_link = 'http://liomenoi.gr'
        self.search_link = '?s=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = self.__search([localtitle] + source_utils.aliases_to_array(aliases), year)
            if not url and title != localtitle: url = self.__search([title] + source_utils.aliases_to_array(
                aliases),year)
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

            self.ep = int(episode)
            r = client.request(urljoin(self.base_link, url))
            r = client.parseDOM(r, 'a', ret='href')
            s = '/season/%d/' % int(season)
            r = [i for i in r if s in i]

            return source_utils.strip_domain(r[0])
        except:
            return

    def __search(self, titles, year):
        try:
            tit = [i.split(':')[0] for i in titles]
            query = [self.search_link % (quote_plus(cleantitle.getsearch(i+' '+year))) for i in tit]
            query = [urljoin(self.base_link, i) for i in query]
            t = [cleantitle.get(i) for i in set(titles) if i]
            for u in query:
                try:
                    r = client.request(u)
                    r = client.parseDOM(r, 'div', attrs={'class': 'card-content'})
                    r = dom_parser.parse_dom(r, 'a')
                    r = [(i.attrs['href'], i.content) for i in r if i]
                    r = [(i[0], i[1]) for i in r if year == re.findall('(\d{4})', i[1], re.DOTALL)[0]]
                    if len(r) == 1: return source_utils.strip_domain(r[0][0])
                    else:
                        r = [(i[0]) for i in r if cleantitle.get(i[1]) in t]
                        return source_utils.strip_domain(r[0])

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

            query = urljoin(self.base_link, url)
            r = client.request(query)

            if not 'tv-series' in query:
                links = client.parseDOM(r, 'tbody')
                links = client.parseDOM(links, 'a', ret='href')
            else:
                links = client.parseDOM(r, 'ul', attrs={'class':'collapsible'})[0]
                pattern = 'href="#">.+?%d\s*<span class="right lmn-num-of-ep">(.+?)</table></div>' % self.ep
                links = re.findall(pattern, links)
                links = client.parseDOM(links, 'a', ret='href')

            for url in links:
                try:
                    if 'liomenoi' in url:
                        url = re.findall('liomenoi.+?link=(.+?)&title', url)[0]
                        url = base64.b64decode(url)
                        url = ensure_text(url, errors='ignore')
                    if 'target' in url: continue

                    if 'redvid' in url:
                        data = client.request(url)
                        url = client.parseDOM(data, 'iframe', ret='src')[0]

                    if any(x in url for x in ['.online', 'xrysoi', 'filmer', '.bp', '.blogger', 'youtu']):
                        continue
                    if 'crypt' in url:
                        host = re.findall('embed\/(.+?)\/', url)[0]
                        url = url
                    else:
                        valid, host = source_utils.is_host_valid(url, hostDict)
                        if not valid: continue
                    quality = 'SD'
                    lang, info = 'gr', 'SUB'

                    sources.append({'source': host, 'quality': quality, 'language': lang, 'url': url, 'info': info,
                                    'direct':False,'debridonly': False})
                except:
                    pass
            return sources
        except:
            return sources

    def resolve(self, url):
        if 'crypt' in url:
            data = client.request(url)
            url = re.findall('''onclick="location.href=['"]([^"']+)["']''', data, re.DOTALL)[0]
            url = re.sub('(?:playvideo-|\?playvid)', '', url)

        return url
