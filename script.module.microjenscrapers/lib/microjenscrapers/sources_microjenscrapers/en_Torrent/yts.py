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

from microjenscrapers import parse_qs, urljoin, urlencode, quote
from microjenscrapers.modules import cleantitle, client, debrid, source_utils
#from microjenscrapers import cfScraper


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['yts.am']
        self.base_link = 'https://yts.mx/'
        self.search_link = 'browse-movies/%s/all/all/0/latest/0/all'

    def movie(self, imdb, title, localtitle, aliases, year):
        if debrid.status() is False:
            return

        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = cleantitle.get_query(data['title'])

            query = '%s %s' % (title, data['year'])

            #_headers = {'User-Agent': client.agent()}

            url = self.search_link % quote(query)
            url = urljoin(self.base_link, url)
            html = client.request(url)#, headers=_headers)
            try:
                results = client.parseDOM(html, 'div', attrs={'class': 'row'})[2]
            except Exception:
                return sources

            items = re.findall('class="browse-movie-bottom">(.+?)</div>\s</div>', results, re.DOTALL)
            if items is None:
                return sources

            for entry in items:
                try:
                    try:
                        link, name = re.findall('<a href="(.+?)" class="browse-movie-title">(.+?)</a>', entry, re.DOTALL)[0]
                        name = client.replaceHTMLCodes(name)
                        if not cleantitle.get(title) in cleantitle.get(name):
                            continue
                    except Exception:
                        continue
                    y = entry[-4:]
                    if not y == data['year']:
                        continue

                    response = client.request(link)#, headers=_headers)
                    try:
                        entries = client.parseDOM(response, 'div', attrs={'class': 'modal-torrent'})
                        for torrent in entries:
                            link, name = re.findall('href="magnet:(.+?)" class="magnet-download download-torrent magnet" title="(.+?)"', torrent, re.DOTALL)[0]
                            try: _name = name.lower().replace('download', '').replace('magnet', '')
                            except: _name = name
                            link = 'magnet:%s' % link
                            link = str(client.replaceHTMLCodes(link).split('&tr')[0])
                            quality, info = source_utils.get_release_quality(name, link)
                            try:
                                size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', torrent)[-1]
                                dsize, isize = source_utils._size(size)
                            except Exception:
                                dsize, isize = 0.0, ''
                            info.insert(0, isize)
                            info = ' | '.join(info)

                            sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en',
                                            'url': link, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': _name})
                    except Exception:
                        continue
                except Exception:
                    continue

            return sources
        except:
            from microjenscrapers.modules import log_utils
            log_utils.log('Ytsam - Exception', 1)
            return sources

    def resolve(self, url):
        return url
