# -*- coding: utf-8 -*-
#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# @shellc0de wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################

# Addon Name: dev name
# Addon id: script.module.microjenscrapers
# Addon Provider: dev name

# - Converted to py3/2 for dev name


import re
import requests

from microjenscrapers import parse_qs, urljoin, urlencode
from microjenscrapers.modules import cleantitle, client, source_utils, log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['iwaatch.com']
        self.base_link = 'https://iwaatch.com'
        self.search_link = '/?q=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('iWAATCH - Exception', 1)
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['title']
            year = data['year']

            search_id = title.lower()
            url = urljoin(self.base_link, self.search_link % (search_id.replace(' ', '+')))
            headers = {
                'User-Agent': client.agent(),
                'Accept': '*/*',
                'Accept-Encoding': 'identity;q=1, *;q=0',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
                'DNT': '1'
            }

            response = requests.Session()
            r = response.get(url, headers=headers, timeout=5).text
            r = client.parseDOM(r, 'div', attrs={'class': 'container'})[1]
            items = client.parseDOM(r, 'div', attrs={'class': r'col-xs-12 col-sm-6 col-md-3 '})
            for item in items:
                movie_url = client.parseDOM(item, 'a', ret='href')[0]
                movie_title = re.compile('div class="post-title">(.+?)<', re.DOTALL).findall(item)[0]
                if cleantitle.get(title).lower() == cleantitle.get(movie_title).lower():

                    r = response.get(movie_url, headers=headers, timeout=5).text
                    year_data = re.findall('<h2 style="margin-bottom: 0">(.+?)</h2>', r, re.IGNORECASE)[0]
                    if year == year_data:
                        links = re.findall(r"<a href='(.+?)'>(\d+)p<\/a>", r)

                        for link, quality in links:

                            if not link.startswith('https:'):
                                link = 'https:' + link.replace('http:', '')
                            link = link + '|Referer=https://iwaatch.com/movie/' + title

                            quality, info = source_utils.get_release_quality(quality, link)

                            sources.append({'source': 'Direct', 'quality': quality, 'language': 'en', 'url': link, 'direct': True, 'debridonly': False})
            return sources
        except:
            log_utils.log('iWAATCH - Exception', 1)
            return sources

    def resolve(self, url):
        return url
