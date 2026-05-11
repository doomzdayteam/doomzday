# -*- coding: utf-8 -*-

'''
    AddonTemplateScrapers Project
'''

import re

from microjenscrapers import parse_qs, urljoin, urlencode, quote_plus, unquote_plus
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import log_utils
from microjenscrapers.modules import source_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['nyaa.si']
        self.base_link = 'https://nyaa.si'
        self.search_link = '/?f=0&c=0_0&q=%s'


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('nyaa0 - Exception', 1)
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('nyaa1 - Exception', 1)
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url: return
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            log_utils.log('nyaa2 - Exception', 1)
            return


    def sources(self, url, hostDict, hostprDict):
        sources = []
        if not url: return sources
        try:
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = cleantitle.get_query(title)
            aliases = data['aliases']

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']
            hdlr2 = 'S%d - %d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s %s' % (title, hdlr)
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)

            query2 = '%s %s' % (title, hdlr2)
            query2 = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query2)

            urls = []
            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url)
            urls.append(url)
            url2 = self.search_link % quote_plus(query2)
            url2 = urljoin(self.base_link, url2)
            urls.append(url2)

            for url in urls:
                try:
                    r = client.request(url)
                    if 'magnet' not in r:
                        return sources
                    r = re.sub(r'\n', '', r)
                    r = re.sub(r'\t', '', r)
                    tbody = client.parseDOM(r, 'tbody')
                    rows = client.parseDOM(tbody, 'tr')

                    for row in rows:
                        links = zip(re.findall('href="(magnet:.+?)"', row, re.DOTALL),
                                    re.findall('((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', row, re.DOTALL),
                                    [re.findall('<td class="text-center">([0-9]+)</td>', row, re.DOTALL)])

                        for link in links:
                            url = unquote_plus(link[0]).replace('&amp;', '&').replace(' ', '.').split('&tr')[0]
                            name = url.split('&dn=')[1]

                            quality, info = source_utils.get_release_quality(name, url)
                            try:
                                size = link[1]
                                dsize, isize = source_utils._size(size)
                            except:
                                dsize, isize = 0.0, ''
                                pass
                            info.insert(0, isize)
                            info = ' | '.join(info)

                            sources.append({'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url,
                                            'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': name})
                except:
                    log_utils.log('nyaa3 - Exception', 1)
                    return sources
            return sources
        except:
            log_utils.log('nyaa4 - Exception', 1)
            return sources


    def resolve(self, url):
        return url
