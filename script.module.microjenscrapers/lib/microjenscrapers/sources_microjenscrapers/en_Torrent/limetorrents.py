# -*- coding: utf-8 -*-
# -Cleaned and Checked on 03-04-2019 by dev name in dev name.

import re

from six import ensure_text

from microjenscrapers import cfScraper
from microjenscrapers import parse_qs, urljoin, urlencode, quote
from microjenscrapers.modules import cache
from microjenscrapers.modules import client
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import debrid
from microjenscrapers.modules import source_utils
from microjenscrapers.modules import log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['limetorrents.info', 'limetor.com', 'limetor.pro', 'limetorrents.co', 'limetorrents.asia', 'limetorrents.lol']
        self._base_link = None
        self.tvsearch = '/search/tv/{0}/'
        self.moviesearch = '/search/movies/{0}/'


    @property
    def base_link(self):
        if not self._base_link:
            self._base_link = cache.get(self.__get_base_url, 120, 'https://%s' % self.domains[0])
        return self._base_link


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            hostDict = hostDict + hostprDict
            if url is None:
                return sources
            if debrid.status() is False: return
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = cleantitle.get_query(title)
            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']
            query = '%s S%02dE%02d' % (title, int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (title, data['year'])
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            if 'tvshowtitle' in data:
                url = self.tvsearch.format(quote(query))
                url = urljoin(self.base_link, url)
            else:
                url = self.moviesearch.format(quote(query))
                url = urljoin(self.base_link, url)

            r = cfScraper.get(url).content
            r = ensure_text(r, errors='ignore')
            posts = client.parseDOM(r, 'table', attrs={'class': 'table2'})[0]
            posts = client.parseDOM(posts, 'tr')
            for post in posts:
                try:
                    link = client.parseDOM(post, 'a', ret='href')[0]
                    hash = re.findall(r'(\w{40})', link, re.I)
                    if hash:
                        url = 'magnet:?xt=urn:btih:' + hash[0]
                        name = link.split('title=')[1]
                        t = name.split(hdlr)[0]
                        if not cleantitle.get(re.sub('(|)', '', t)) == cleantitle.get(title): continue
                        try:
                            y = re.findall('[\.|\(|\[|\s|\_|\-](S\d+E\d+|S\d+)[\.|\)|\]|\s|\_|\-]', name, re.I)[-1].upper()
                        except:
                            y = re.findall('[\.|\(|\[|\s\_|\-](\d{4})[\.|\)|\]|\s\_|\-]', name, re.I)[-1].upper()
                        if not y == hdlr: continue
                        quality, info = source_utils.get_release_quality(name)
                        try:
                            size = re.findall('((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GiB|MiB|GB|MB))', post)[0]
                            dsize, isize = source_utils._size(size)
                        except:
                            dsize, isize = 0.0, ''
                        info.insert(0, isize)
                        info = ' | '.join(info)
                        sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False,
                                        'debridonly': True, 'size': dsize, 'name': name})
                except:
                    pass
            return sources
        except:
            log_utils.log('lime0 - Exception', 1)
            return sources


    def resolve(self, url):
        return url


    def __get_base_url(self, fallback):
        try:
            for domain in self.domains:
                try:
                    url = 'https://%s' % domain
                    #result = client.request(url, limit=1, timeout='5')
                    result = cfScraper.get(url, timeout=4).content
                    result = ensure_text(result, errors='ignore')
                    search_n = re.findall('<title>(.+?)</title>', result, re.DOTALL)[0]
                    if result and 'LimeTorrents' in search_n:
                        return url
                except:
                    pass
        except:
            pass
        return fallback

