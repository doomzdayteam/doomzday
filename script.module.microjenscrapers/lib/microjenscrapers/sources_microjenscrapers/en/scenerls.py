# -*- coding: utf-8 -*-
"""
**Created by dev name**
"""
# - Converted to py3/2 for dev name

import re

from six import ensure_text

from microjenscrapers import cfScraper
from microjenscrapers import parse_qs, urljoin, urlparse, urlencode, quote_plus
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import debrid
from microjenscrapers.modules import source_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['scene-rls.com', 'scene-rls.net']
        self.base_link = 'http://scene-rls.net'
        self.search_link = '/?s=%s&submit=Find'

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
            if url is None: return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []

            if url is None:
                return sources

            if debrid.status() is False:
                raise Exception()

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = cleantitle.get_query(title)

            hdlr = 's%02de%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s s%02de%02d' % (title, int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (title, data['year'])
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)

            try:
                url = self.search_link % quote_plus(query)
                url = urljoin(self.base_link, url)

                r = cfScraper.get(url).content
                r = ensure_text(r, errors='replace')

                posts = client.parseDOM(r, 'div', attrs={'class': 'post'})

                items = []

                for post in posts:
                    try:
                        u = client.parseDOM(post, "div", attrs={"class": "postContent"})
                        size = re.findall('((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GiB|MiB|GB|MB))', u[0])[0]
                        u = client.parseDOM(u, "h2")
                        u = client.parseDOM(u, 'a', ret='href')
                        u = [(i.strip('/').split('/')[-1], i, size) for i in u]
                        items += u
                    except:
                        pass
            except:
                pass

            for item in items:
                try:
                    name = item[0]
                    name = client.replaceHTMLCodes(name)

                    t = re.sub('(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d*|3D)(\.|\)|\]|\s|)(.+|)', '', name)

                    if not cleantitle.get(t) == cleantitle.get(title): continue

                    quality, info = source_utils.get_release_quality(name, item[1])

                    try:
                        dsize, isize = source_utils._size(item[2])
                    except:
                        dsize, isize = 0.0, ''
                    info.insert(0, isize)

                    info = ' | '.join(info)

                    url = item[1]
                    if any(x in url for x in ['.rar', '.zip', '.iso']):
                        raise Exception()
                    url = client.replaceHTMLCodes(url)
                    url = ensure_text(url)

                    host = re.findall('([\w]+[.][\w]+)$', urlparse(url.strip().lower()).netloc)[0]
                    if host not in hostDict:
                        raise Exception()
                    host = client.replaceHTMLCodes(host)
                    host = ensure_text(host)

                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'name': name})
                except:
                    pass

            return sources
        except:
            return sources

    def resolve(self, url):
        return url


