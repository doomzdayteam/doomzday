# -*- coding: UTF-8 -*-
#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# @dev name wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################



import re

from microjenscrapers import parse_qs, urljoin, urlencode, quote_plus
from microjenscrapers.modules import cache, cleantitle, client, debrid, source_utils, log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['eztv.re', 'eztv.ag', 'eztv.it', 'eztv.ch', 'eztv.tf', 'eztv.yt', 'eztv.unblockit.dev']
        self._base_link = None
        self.search_link = '/search/%s'

    @property
    def base_link(self):
        if self._base_link is None:
            self._base_link = cache.get(self.__get_base_url, 120, 'https://%s' % self.domains[0])
        return self._base_link

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        if debrid.status() is False:
            return

        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
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
        except Exception:
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle']
            title = cleantitle.get_query(title)

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode']))

            query = '%s S%02dE%02d' % (
                title,
                int(data['season']),
                int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (
                title,
                data['year'])
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|<|>|\|)', ' ', query)

            url = self.search_link % (quote_plus(query).replace('+', '-'))
            url = urljoin(self.base_link, url)
            html = client.request(url)

            try:
                results = client.parseDOM(html, 'table', attrs={'class': 'forum_header_border'})
                for result in results:
                    if 'magnet:' in result:
                        results = result
                        break
            except Exception:
                return sources
            rows = re.findall('<tr name="hover" class="forum_header_border">(.+?)</tr>', results, re.DOTALL)
            if rows is None:
                return sources

            for entry in rows:
                try:
                    try:
                        columns = re.findall('<td\s.+?>(.+?)</td>', entry, re.DOTALL)
                        derka = re.findall('href="magnet:(.+?)" class="magnet" title="(.+?)"', columns[2], re.DOTALL)[0]
                        name = derka[1]
                        link = 'magnet:%s' % (str(client.replaceHTMLCodes(derka[0]).split('&tr')[0]))
                        t = name.split(hdlr)[0]
                        if not cleantitle.get(re.sub('(|)', '', t)) == cleantitle.get(title):
                            continue
                    except Exception:
                        continue
                    y = re.findall('[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', name)[-1].upper()
                    if not y == hdlr:
                        continue

                    quality, info = source_utils.get_release_quality(name, name)

                    try:
                        size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', name)[-1]
                        dsize, isize = source_utils._size(size)
                    except Exception:
                        dsize, isize = 0.0, ''

                    info.insert(0, isize)

                    info = ' | '.join(info)
                    sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en',
                                    'url': link, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': name})
                except Exception:
                    continue

            check = [i for i in sources if not i['quality'] == 'CAM']
            if check:
                sources = check

            return sources
        except:
            log_utils.log('eztv_exc', 1)
            return sources

    def __get_base_url(self, fallback):
        try:
            for domain in self.domains:
                try:
                    url = 'https://%s' % domain
                    result = client.request(url, limit=1, timeout='4')
                    search_n = re.findall('<title>(.+?)</title>', result, re.DOTALL)[0]
                    if search_n and 'EZTV' in search_n:
                        return url
                except Exception:
                    pass
        except Exception:
            pass

        return fallback
    def resolve(self, url):
        return url
