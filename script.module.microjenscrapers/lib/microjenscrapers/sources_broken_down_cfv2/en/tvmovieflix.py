# -*- coding: utf-8 -*-
# -Cleaned and Checked on 07-23-2019 by dev name in dev name.

import re,requests
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import source_utils
from microjenscrapers import cfScraper


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['tvmovieflix.com']
        self.base_link = 'http://tvmovieflix.com'


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            mtitle = cleantitle.geturl(title)
            url = self.base_link + '/movies/%s' % (mtitle)
            return url
        except:
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = cleantitle.geturl(tvshowtitle)
            return url
        except:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url == None:
                return
            tvshowtitle = url
            url = self.base_link + '/show/%s/season/%s/episode/%s' % (tvshowtitle, season, episode)
            return url
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []
            if url == None:
                return sources
            hostDict = hostDict + hostprDict
            r = cfScraper.get(url).content
            match = re.compile('<a href="http://www.tvmovieflix.com/report-.+?/(.+?)" target="_blank"><span class="a">Report Broken</span></a></li>', re.DOTALL | re.M).findall(r)
            for link in match:
                if "/show/" in url:
                    surl = "http://www.tvmovieflix.com/e/" + link
                else:
                    surl = "http://www.tvmovieflix.com/m/" + link
                i = cfScraper.get(surl).content
                match = re.compile('<IFRAME.+?SRC="(.+?)"', re.DOTALL | re.IGNORECASE).findall(i)
                for link in match:
                    if "realtalksociety.com" in link:
                        r = requests.get(link).content
                        match = re.compile('<source src="(.+?)" type="video/mp4">', re.DOTALL | re.IGNORECASE).findall(r)
                        for url in match:
                            valid, host = source_utils.is_host_valid(url, hostDict)
                            quality, info = source_utils.get_release_quality(url, url)
                            sources.append({'source': host, 'quality': quality, 'language': 'en', 'info': info, 'url': url, 'direct': True, 'debridonly': False})
                    else:
                        valid, host = source_utils.is_host_valid(link, hostDict)
                        quality, info = source_utils.get_release_quality(link, link)
                        sources.append({'source': host, 'quality': quality, 'language': 'en', 'info': info, 'url': link, 'direct': False, 'debridonly': False})
            return sources
        except:
            return sources


    def resolve(self, url):
        return url


