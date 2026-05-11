# -*- coding: UTF-8 -*-

# - rewritten to be less greedy, fixed tvshows and converted to py3/2 for dev name

import re, traceback

try: from urlparse import parse_qs, urljoin
except ImportError: from urllib.parse import parse_qs, urljoin
try: from urllib import urlencode, quote_plus
except ImportError: from urllib.parse import urlencode, quote_plus

from six import ensure_text
from six.moves import zip

from microjenscrapers.modules import client
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import source_utils
from microjenscrapers.modules import log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['5movies.to']  # Old  tinklepad.is  movie25.hk
        self.base_link = 'https://5movies.to'
        self.search_link = '/search.php?q=%s'
        self.video_link = '/getlink.php?Action=get&lk=%s'


    def matchAlias(self, title, aliases):
        try:
            for alias in aliases:
                if cleantitle.get(title) == cleantitle.get(alias['title']):
                    return True
        except:
            return False


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            aliases.append({'country': 'us', 'title': title})
            url = {'imdb': imdb, 'title': title, 'year': year, 'aliases': aliases}
            url = urlencode(url)
            return url
        except:
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            aliases.append({'country': 'us', 'title': tvshowtitle})
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year, 'aliases': aliases}
            url = urlencode(url)
            return url
        except:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url == None:
                return
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            return


    def _search(self, title, year, aliases, headers):
        try:
            q = urljoin(self.base_link, self.search_link % quote_plus(cleantitle.getsearch(title)))
            r = client.request(q)
            r = client.parseDOM(r, 'div', attrs={'class':'ml-img'})
            r = zip(client.parseDOM(r, 'a', ret='href'), client.parseDOM(r, 'img', ret='alt'))
            url = [i for i in r if cleantitle.get(title) in cleantitle.get(i[1]) and year in i[1]][0][0]
            return url
        except:
            failure = traceback.format_exc()
            log_utils.log('5movies - Exception: \n' + str(failure))
            pass


    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url == None:
                return sources
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            aliases = eval(data['aliases'])
            headers = {}
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            year = data['year']
            if 'tvshowtitle' in data:
                episode = data['episode']
                season = data['season']
                url = self._search(title, year, aliases, headers)
                if url.endswith('/'):
                    url = url.rstrip('/')
                url += '-s%se%s/' % (season, episode)
            else:
                episode = None
                year = data['year']
                url = self._search(data['title'], data['year'], aliases, headers)
            url = url if 'http' in url else urljoin(self.base_link, url)
            result = client.request(url)
            result = ensure_text(result)
            items = client.parseDOM(result, 'div', attrs={'class':'links'})
            r = zip(client.parseDOM(items, 'li', attrs={'class':'link-button'}), re.findall(r'link-name">(.+?)</', items[0], re.DOTALL))
            r = [(i[0], i[1]) for i in r]
            for u, h in r:
                l = client.parseDOM(u, 'a', ret='href')[0]
                l = l.split('=')[1]
                url = urljoin(self.base_link, self.video_link % l)
                h = h.strip()
                valid, host = source_utils.is_host_valid(h, hostDict)
                if valid:
                    sources.append({'source': host, 'quality': 'sd', 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})
            return sources
        except:
            failure = traceback.format_exc()
            log_utils.log('5movies - Exception: \n' + str(failure))
            return sources


    def resolve(self, url):
        result = client.request(url, post={}, headers={'Referer':url})
        url = result if 'http' in result else 'https:' + result
        if ' href' in url:
            url = 'https:' + re.compile(r" href='(.+?)'").findall(url)[0]
        url = ensure_text(url, errors='ignore')
        return url


