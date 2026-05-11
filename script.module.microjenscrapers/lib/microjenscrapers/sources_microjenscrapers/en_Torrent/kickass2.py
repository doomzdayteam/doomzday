# -*- coding: UTF-8 -*-
#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# @dev name wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################

# - Converted to py3/2 for dev name


import re

import six

from microjenscrapers import parse_qs, urljoin, urlencode, unquote, quote_plus
from microjenscrapers.modules import cache, cleantitle, client, debrid, log_utils, source_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['kick4ss.com', 'kickasstorrents.id', 'kickasstorrents.bz', 'kkickass.com', 'kkat.net', 'kickass-kat.com', 'kickasst.net', 'thekat.cc', 'kickasshydra.net', 'kickasshydra.org', 'kickass.onl', 'thekat.info', 'kickass.cm']
        self._base_link = None
        self.search_link = '/usearch/%s'

    @property
    def base_link(self):
        if self._base_link is None:
            self._base_link = cache.get(self.__get_base_url, 120, 'https://%s' % self.domains[0])
        return self._base_link

    def movie(self, imdb, title, localtitle, aliases, year):
        if debrid.status() is False:
            return

        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        if debrid.status() is False:
            return

        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        if debrid.status() is False:
            return

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
            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = cleantitle.get_query(title)

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s S%02dE%02d' % (
                title,
                int(data['season']),
                int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (
                title,
                data['year'])
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|<|>|\|)', ' ', query)
            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url)
            html = client.request(url)
            if html is None:
                return sources
            html = html.replace('&nbsp;', ' ')
            try:
                rows = client.parseDOM(html, 'tr', attrs={'id': 'torrent_latest_torrents'})
            except:
                return sources
            if rows is None:
                #log_utils.log('KICKASS - No Torrents In Search Results')
                return sources

            for entry in rows:
                try:
                    try:
                        name = re.findall('class="cellMainLink">(.+?)</a>', entry, re.DOTALL)[0]
                        name = client.replaceHTMLCodes(name)
                        # t = re.sub('(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d*|3D)(\.|\)|\]|\s|)(.+|)', '', name, flags=re.I)
                        if not cleantitle.get(title) in cleantitle.get(name):
                            continue
                    except:
                        continue

                    try:
                        y = re.findall('[\.|\(|\[|\s|\_|\-](S\d+E\d+|S\d+)[\.|\)|\]|\s|\_|\-]', name, re.I)[-1].upper()
                    except:
                        y = re.findall('[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', name, re.I)[-1].upper()
                    if not y == hdlr:
                        continue

                    try:
                        link = 'magnet%s' % (re.findall('url=magnet(.+?)"', entry, re.DOTALL)[0])
                        link = str(unquote(six.ensure_text(link)).split('&tr')[0])
                    except:
                        continue

                    quality, info = source_utils.get_release_quality(name, link)

                    try:
                        size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', entry)[-1]
                        dsize, isize = source_utils._size(size)
                    except:
                        dsize, isize = 0.0, ''

                    info.insert(0, isize)

                    info = ' | '.join(info)

                    sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en',
                                    'url': link, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': name})
                except:
                    pass

            check = [i for i in sources if not i['quality'] == 'CAM']
            if check:
                sources = check

            return sources
        except:
            log_utils.log('kickass_exc', 1)
            return sources

    def __get_base_url(self, fallback):
        try:
            for domain in self.domains:
                try:
                    url = 'https://%s' % domain
                    result = client.request(url, limit=1, timeout='4')
                    search_n = re.findall('<title>(.+?)</title>', result, re.DOTALL)[0]
                    if search_n and 'Kickass' in search_n:
                        return url
                except:
                    pass
        except:
            pass

        return fallback

    def resolve(self, url):
        return url
