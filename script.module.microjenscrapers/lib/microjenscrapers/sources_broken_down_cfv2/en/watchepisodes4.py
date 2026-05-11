# -*- coding: UTF-8 -*-
# -Cleaned and Checked on 10-16-2019 by dev name in dev name.
# -Mod'D by dev name

import re
from microjenscrapers.modules import client
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import log_utils
from microjenscrapers.modules import source_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['watchepisodes4.com']
        self.base_link = 'https://www.watchepisodes4.com/'


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            clean_title = cleantitle.geturl(tvshowtitle)
            url = self.base_link + clean_title
            return url
        except:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return
            r = client.request(url)
            r = re.compile('<a title=".+? Season ' + season + ' Episode ' + episode + ' .+?" href="(.+?)">').findall(r)
            for url in r:
                return url
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []
            if url == None:
                return sources
            hostDict = hostprDict + hostDict
            r = client.request(url)
            r = re.compile('class="watch-button" data-actuallink="(.+?)"').findall(r)
            for url in r:
                if url in str(sources):
                    continue
                quality, info = source_utils.get_release_quality(url, url)
                valid, host = source_utils.is_host_valid(url, hostDict)
                if valid:
                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})
            return sources
        except:
            log_utils.log('Watchepisodes4 Exception', 1)
            return sources


    def resolve(self, url):
        return url


