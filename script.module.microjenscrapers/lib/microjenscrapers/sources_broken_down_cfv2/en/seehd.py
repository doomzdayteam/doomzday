# -*- coding: utf-8 -*-
#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# @dev name wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################



import re
import requests
import urlparse

from microjenscrapers.modules import cleantitle, source_utils
from microjenscrapers import cfScraper


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['seehd.pl']
        self.base_link = 'http://www.seehd.pl'
        self.search_link = '/?s=%s'
        self.tv_link = '/%s-%s-watch-online/'
        self.hdclub_link = 'https://www.24hd.club/api/source/'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            search = cleantitle.getsearch(imdb)
            url = urlparse.urljoin(self.base_link, self.search_link)
            url = url % (search.replace(':', ' ').replace(' ', '+'))
            r = cfScraper.get(url).content
            Yourmouth = re.compile(
                '<div class="post_thumb".+?href="(.+?)"><h2 class="thumb_title">(.+?)</h2>', re.DOTALL).findall(r)
            for Myballs, Mycock in Yourmouth:
                if cleantitle.get(title) in cleantitle.get(Mycock):
                    return Myballs
            return
        except Exception:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = cleantitle.geturl(tvshowtitle)
            return url
        except Exception:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return
            title = url
            season = '%02d' % int(season)
            episode = '%02d' % int(episode)
            se = 's%se%s' % (season, episode)
            url = self.base_link + self.tv_link % (title, se)
            return url
        except Exception:
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []
            if url is None:
                return sources
            hostDict = hostprDict + hostDict

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'}
            first_url = url
            r = cfScraper.get(first_url).content
            links = re.compile('<iframe.+?src="(.+?)://(.+?)/(.+?)"', re.DOTALL).findall(r)
            for http, host, url in links:
                host = host.replace('www.', '')
                url = '%s://%s/%s' % (http, host, url)
                if 'seehd' in url:
                    r = cfScraper.get(url).content
                    extra_link = re.compile('<center><iframe.+?src="(.+?)"', re.DOTALL).findall(r)[0]
                    valid, host = source_utils.is_host_valid(extra_link, hostDict)
                    sources.append({'source': host, 'quality': '720p', 'language': 'en', 'url': extra_link, 'direct': False, 'debridonly': False})
                elif '24hd' in url:
                    url = url.split('v/')[1]
                    post_link = urlparse.urljoin(self.hdclub_link, url)
                    payload = {'r': first_url, 'd': 'www.24hd.club'}
                    post_data = requests.post(post_link, headers=headers, data=payload)
                    response = post_data.content

                    link = re.compile('"file":"(.+?)","label":"(.+?)"', re.DOTALL).findall(response)
                    for link, quality in link:
                        link = link.replace('\/', '/')

                        if '1080p' in quality:
                            quality = '1080p'
                        elif '720p' in quality:
                            quality = '720p'
                        elif '480p' in quality:
                            quality = 'SD'
                        else:
                            quality = 'SD'

                        sources.append({'source': 'Direct', 'quality': quality, 'language': 'en', 'url': link, 'direct': True, 'debridonly': False})
                else:
                    sources.append({'source': host, 'quality': '720p', 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})

            return sources
        except Exception:
            return sources

    def resolve(self, url):
        return url
