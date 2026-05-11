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

import re, traceback

try: from urlparse import parse_qs
except ImportError: from urllib.parse import parse_qs
try: from urllib import urlencode
except ImportError: from urllib.parse import urlencode

from six import ensure_text

from microjenscrapers.modules import cleantitle, client, source_utils, log_utils
from microjenscrapers import cfScraper


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['ganool.ws', 'ganol.si', 'ganool123.com', 'fmovies.tw']
        self.base_link = 'https://0123movies.in'
        self.search_link = '/s=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            failure = traceback.format_exc()
            log_utils.log('Ganool Testing - Exception: \n' + str(failure))
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            q = '%s' % cleantitle.get_gan_url(data['title'])
            url = self.base_link + self.search_link % q
            r = cfScraper.get(url).content
            r = ensure_text(r)
            v = re.compile('<a href="(.+?)" class="ml-mask jt" title="(.+?)">\s+<span class=".+?">(.+?)</span>').findall(r)
                            #<a href="https://0123movies.in/695/1917-2/" data-url="" class="ml-mask jt" data-hasqtip="0" oldtitle="1917" title="" aria-describedby="qtip-0"> <span class="mli-quality">4K</span><img data-original="https://0123movies.in/wp-content/uploads/2020/09/iZf0KyrE25z1sage4SYFLCCrMi9.jpg" class="lazy thumb mli-thumb" alt="1917" src="https://0123movies.in/wp-content/uploads/2020/09/iZf0KyrE25z1sage4SYFLCCrMi9.jpg" style="display: inline-block;"><span class="mli-info"><h2>1917</h2></span></a>
            for url, check, qual in v:
                t = '%s (%s)' % (data['title'], data['year'])
                if t in check:
                    #key = url.split('-hd')[1]
                    #url = '0123movies.in/moviedownload.php?q=%s' % key
                    r = cfScraper.get(url).content
                    r = ensure_text(r)
                    r = re.compile('<a rel=".+?" href="(.+?)" target=".+?">').findall(r)
                    for url in r:
                        if any(x in url for x in ['.rar']): continue
                        #quality, _ = source_utils.get_release_quality(qual, url)
                        valid, host = source_utils.is_host_valid(url, hostDict)
                        if valid:
                            #info = ' | '.join(info)
                            sources.append(
                                {'source': host, 'quality': '720p', 'language': 'en', 'url': url,
                                 'direct': False, 'debridonly': False})
            return sources
        except:
            failure = traceback.format_exc()
            log_utils.log('Ganool Testing - Exception: \n' + str(failure))
            return sources

    def resolve(self, url):
        return url
