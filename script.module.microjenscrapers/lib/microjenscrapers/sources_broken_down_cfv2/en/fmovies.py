# -*- coding: UTF-8 -*-
# -Cleaned and Checked on 05-06-2019 by dev name in dev name.

#  ..#######.########.#######.##....#..######..######.########....###...########.#######.########..######.
#  .##.....#.##.....#.##......###...#.##....#.##....#.##.....#...##.##..##.....#.##......##.....#.##....##
#  .##.....#.##.....#.##......####..#.##......##......##.....#..##...##.##.....#.##......##.....#.##......
#  .##.....#.########.######..##.##.#..######.##......########.##.....#.########.######..########..######.
#  .##.....#.##.......##......##..###.......#.##......##...##..########.##.......##......##...##........##
#  .##.....#.##.......##......##...##.##....#.##....#.##....##.##.....#.##.......##......##....##.##....##
#  ..#######.##.......#######.##....#..######..######.##.....#.##.....#.##.......#######.##.....#..######.

import re, traceback
import urlparse

from microjenscrapers.modules import cleantitle
#from microjenscrapers.modules import client
from microjenscrapers.modules import log_utils
from microjenscrapers.modules import source_utils
from microjenscrapers import cfScraper


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['fmoviesto.to']
        self.base_link = 'https://www6.fmovies2.io'
        self.search_link = '/search.html?keyword=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            search_id = cleantitle.getsearch(title)
            url = urlparse.urljoin(self.base_link, self.search_link)
            url = url % (search_id.replace(' ', '+'))
            #search_results = client.request(url)
            search_results = cfScraper.get(url).content
            log_utils.log('fmovies0 - search_results: \n' + str(search_results))
            match = re.compile(r'<a href="/watch/(.+?)" title="(.+?)">', re.DOTALL).findall(search_results)
            for row_url, row_title in match:
                row_url = self.base_link + '/watch/%s' % row_url
                if cleantitle.get(title) in cleantitle.get(row_title):
                    return row_url
            return
        except:
            failure = traceback.format_exc()
            log_utils.log('fmovies0 - Exception: \n' + str(failure))
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []
            if url == None:
                return sources
            #html = client.request(url)
            html = cfScraper.get(url).content
            quality = re.compile('<div>Quanlity: <span class="quanlity">(.+?)</span></div>', re.DOTALL).findall(html)
            for qual in quality:
                quality = source_utils.check_url(qual)
                info = qual
            links = re.compile('var link_.+? = "(.+?)"', re.DOTALL).findall(html)
            for url in links:
                if not url.startswith('http'):
                    url = "https:" + url
                valid, host = source_utils.is_host_valid(url, hostDict)
                if valid:
                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'info': info, 'url': url,
                                    'direct': False, 'debridonly': False})
            return sources
        except:
            failure = traceback.format_exc()
            log_utils.log('fmovies1 - Exception: \n' + str(failure))
            return sources

    def resolve(self, url):
        if 'vidcloud' in url:
            #r = client.request(url)
            r = cfScraper.get(url).content
            url = re.compile('(?:file|source)(?:\:)\s*(?:\"|\')(.+?)(?:\"|\')').findall(r)[0]
        return url
