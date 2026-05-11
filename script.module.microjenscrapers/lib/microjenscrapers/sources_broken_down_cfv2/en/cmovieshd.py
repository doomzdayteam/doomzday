# -*- coding: UTF-8 -*-
# -Cleaned and Checked on 08-24-2019 by dev name in dev name.
# Created by dev name

import re
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import source_utils
from microjenscrapers import cfScraper


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['cmovieshd.bz']
        self.base_link = 'https://www2.cmovies.ac/'
        self.search_link = '/film/%s/watching.html?ep=0'


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            title = cleantitle.geturl(title).replace('--', '-')
            url = self.base_link + self.search_link % title
            return url
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []
            hostDict = hostprDict + hostDict
            r = cfScraper.get(url).content
            qual = re.compile('class="quality">(.+?)</span>').findall(r)
            for i in qual:
                info = i
                if '1080' in i:
                    quality = '1080p'
                elif '720' in i:
                    quality = '720p'
                else:
                    quality = 'SD'
            u = re.compile('data-video="(.+?)"').findall(r)
            for url in u:
                if not url.startswith('http'):
                    url =  "https:" + url
                if 'vidcloud' in url:
                    r = cfScraper.get(url).content
                    t = re.compile('data-video="(.+?)"').findall(r)
                    for url in t:
                        if not url.startswith('http'):
                            url =  "https:" + url
                        valid, host = source_utils.is_host_valid(url, hostDict)
                        if valid and 'vidcloud' not in url:
                            sources.append({'source': host, 'quality': quality, 'language': 'en', 'info': info, 'url': url, 'direct': False, 'debridonly': False})
                valid, host = source_utils.is_host_valid(url, hostDict)
                if valid:
                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'info': info, 'url': url, 'direct': False, 'debridonly': False})
            return sources
        except:
            return sources


    def resolve(self, url):
        return url


