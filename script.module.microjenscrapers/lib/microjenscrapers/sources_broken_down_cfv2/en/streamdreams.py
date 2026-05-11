# -*- coding: utf-8 -*-

"""
    **Created by dev name**
    Thanks dev name For the fix
"""

from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import source_utils
from microjenscrapers.modules import client
from microjenscrapers import cfScraper


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['streamdreams.org']
        self.base_link = 'https://streamdreams.org'
        self.search_movie = '/movies/nnn-%s/'
        self.search_tv = '/shows/nnn-%s/'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            title = cleantitle.geturl(title)
            url = self.base_link + self.search_movie % title
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            tvtitle = cleantitle.geturl(tvshowtitle)
            url = self.base_link + self.search_tv % tvtitle
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return
            url = url + '?session=%s&episode=%s' % (season, episode)
            return url
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources
            hostDict = hostprDict + hostDict
            #headers = {'Referer': url}
            r = cfScraper.get(url).content
            u = client.parseDOM(r, "span", attrs={"class": "movie_version_link"})
            for t in u:
                match = client.parseDOM(t, 'a', ret='data-href')
                for url in match:
                    if url in str(sources):
                        continue
                    quality, info = source_utils.get_release_quality(url, url)
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        sources.append({'source': host, 'quality': quality, 'language': 'en', 'info': info, 'url': url, 'direct': False, 'debridonly': False})
            return sources
        except:
            return sources

    def resolve(self, url):
        return url
