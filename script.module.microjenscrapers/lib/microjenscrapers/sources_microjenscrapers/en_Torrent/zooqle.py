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

from microjenscrapers import parse_qs, urljoin, urlencode, quote_plus
from microjenscrapers.modules import cleantitle, client, debrid, log_utils, source_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['zooqle.com']
        self.base_link = 'https://zooqle.com'
        self.search_link = '/search?q=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        if debrid.status() is False:
            return

        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('ZOOGLE - Exception', 1)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        if debrid.status() is False:
            return

        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('ZOOGLE - Exception', 1)
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
            log_utils.log('ZOOGLE - Exception', 1)
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

            category = '+category%3ATV' if 'tvshowtitle' in data else '+category%3AMovies'

            query = '%s S%02dE%02d' % (
                title,
                int(data['season']),
                int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (
                title,
                data['year'])
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|<|>|\|)', ' ', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url) + str(category)
            html = client.request(url)
            html = html.replace('&nbsp;', ' ')
            try:
                results = client.parseDOM(html, 'table', attrs={'class': 'table table-condensed table-torrents vmiddle'})[0]
            except Exception:
                return sources
            rows = re.findall('<tr(.+?)</tr>', results, re.DOTALL)
            if rows is None:
                return sources
            for entry in rows:
                try:
                    try:
                        name = re.findall('<a class=".+?>(.+?)</a>', entry, re.DOTALL)[0]
                        name = client.replaceHTMLCodes(name).replace('<hl>', '').replace('</hl>', '')
                        # t = re.sub('(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d*|3D)(\.|\)|\]|\s|)(.+|)', '', name, flags=re.I)
                        if not cleantitle.get(title) in cleantitle.get(name):
                            continue
                    except Exception:
                        continue
                    y = re.findall('[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', name)[-1].upper()
                    if not y == hdlr:
                        continue

                    try:
                        link = 'magnet:%s' % (re.findall('href="magnet:(.+?)"', entry, re.DOTALL)[0])
                        link = client.replaceHTMLCodes(link).split('&tr')[0]
                    except Exception:
                        continue

                    quality, _ = source_utils.get_release_quality(name, link)

                    info = []

                    try:
                        size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', entry)[-1]
                        dsize, isize = source_utils._size(size)
                    except Exception:
                        dsize, isize = 0.0, ''

                    info.insert(0, isize)

                    info = ' | '.join(info)
                    sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en',
                                    'url': link, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': name})
                except Exception:
                    continue

            return sources
        except:
            log_utils.log('ZOOGLE - Exception', 1)
            return sources

    def resolve(self, url):
        return url
