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

import re

from microjenscrapers import parse_qs, urlencode, quote, quote_plus
from microjenscrapers.modules import debrid
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import workers
from microjenscrapers.modules import source_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['torrentdownloads.me', 'torrentsdl1.unblocked.lol']
        self.base_link = 'https://www.torrentdownloads.me/'
        self.search = 'https://www.torrentdownloads.me/rss.xml?new=1&type=search&cid={0}&search={1}'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except BaseException:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except BaseException:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None: return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except BaseException:
            return

    def sources(self, url, hostDict, hostprDict):
        self._sources = []
        try:
            if url is None:
                return self._sources

            if debrid.status() is False:
                return self._sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            self.title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            self.title = cleantitle.get_query(self.title)
            self.hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s S%02dE%02d' % (self.title, int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (self.title, data['year'])
            query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            if 'tvshowtitle' in data:
                url = self.search.format('8', quote(query))
            else:
                url = self.search.format('4', quote(query))

            self.hostDict = hostDict + hostprDict
            headers = {'User-Agent': client.agent()}
            _html = client.request(url, headers=headers)
            threads = []
            for i in re.findall(r'<item>(.+?)</item>', _html, re.DOTALL):
                threads.append(workers.Thread(self._get_items, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

            return self._sources
        except BaseException:
            return self._sources

    def _get_items(self, r):
        try:
            size = re.search(r'<size>([\d]+)</size>', r).groups()[0]
            seeders = re.search(r'<seeders>([\d]+)</seeders>', r).groups()[0]
            _hash = re.search(r'<info_hash>([a-zA-Z0-9]+)</info_hash>', r).groups()[0]
            name = re.search(r'<title>(.+?)</title>', r).groups()[0]
            url = 'magnet:?xt=urn:btih:%s&dn=%s' % (_hash.upper(), quote_plus(name))
            url = url.split('&tr')[0]
            t = name.split(self.hdlr)[0]

            try:
                y = re.findall(r'[\.|\(|\[|\s|\_|\-](S\d+E\d+|S\d+)[\.|\)|\]|\s|\_|\-]', name, re.I)[-1].upper()
            except BaseException:
                y = re.findall(r'[\.|\(|\[|\s\_|\-](\d{4})[\.|\)|\]|\s\_|\-]', name, re.I)[-1].upper()

            quality, info = source_utils.get_release_quality(name, url)

            try:
                div = 1000 ** 3
                dsize = float(size) / div
                isize = '%.2f GB' % dsize
            except BaseException:
                dsize, isize = 0.0, ''

            info.insert(0, isize)

            info = ' | '.join(info)

            if cleantitle.get(re.sub('(|)', '', t)) == cleantitle.get(self.title):
                if y == self.hdlr:
                    self._sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': name})

        except BaseException:
            pass

    def resolve(self, url):
        return url
