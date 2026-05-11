# -*- coding: utf-8 -*-
#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# As long as you retain this notice you can do whatever you want with
# this stuff. If we meet some day, and you think this stuff is worth it,
# you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################

# - Converted to py3/2 for dev name


import re

from six import ensure_text

from microjenscrapers import parse_qs, urljoin, urlencode, quote_plus
from microjenscrapers.modules import cleantitle, client, debrid, source_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['300mbfilms.co', '300mbfilms.ws']
        self.base_link = 'https://www.300mbfilms.ws'
        self.search_link = '/?s=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
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
        except Exception:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if debrid.status() is False:
                return sources

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s S%02dE%02d' % (
                data['tvshowtitle'],
                int(data['season']),
                int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (
                data['title'],
                data['year'])
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url)

            r = client.request(url)

            posts = re.findall('<h2 class="title">(.+?)</h2>', r, re.IGNORECASE)

            hostDict = hostprDict + hostDict

            urls = []
            for item in posts:

                try:
                    link, name = re.findall('href="(.+?)" title="(.+?)"', item, re.IGNORECASE)[0]
                    if not cleantitle.get(title) in cleantitle.get(name):
                        continue
                    name = client.replaceHTMLCodes(name)
                    try: _name = name.lower().replace('permalink to', '')
                    except: _name = name

                    quality, info = source_utils.get_release_quality(name, link)

                    try:
                        size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', name)[-1]
                        dsize, isize = source_utils._size(size)
                    except Exception:
                        dsize, isize = 0.0, ''
                    info.insert(0, isize)

                    info = ' | '.join(info)

                    links = self.links(link)
                    urls += [(i, quality, info) for i in links]
                except Exception:
                    pass

            for item in urls:
                if 'earn-money' in item[0]:
                    continue

                if any(x in item[0] for x in ['.rar', '.zip', '.iso']):
                    continue
                url = client.replaceHTMLCodes(item[0])
                #url = url.encode('utf-8')
                url = ensure_text(url)

                valid, host = source_utils.is_host_valid(url, hostDict)
                if not valid:
                    continue
                host = client.replaceHTMLCodes(host)
                #host = host.encode('utf-8')
                host = ensure_text(host)

                sources.append({'source': host, 'quality': item[1], 'language': 'en', 'url': url, 'info': item[2], 'direct': False, 'debridonly': True, 'size': dsize, 'name': _name})
            return sources
        except Exception:
            return sources

    def links(self, url):
        urls = []
        try:
            if url is None:
                return

            r = client.request(url)
            r = client.parseDOM(r, 'div', attrs={'class': 'entry'})
            r = client.parseDOM(r, 'a', ret='href')
            r1 = [i for i in r if 'money' in i][0]
            r = client.request(r1)
            r = client.parseDOM(r, 'div', attrs={'id': 'post-\d+'})[0]

            if 'enter the password' in r:
                plink = client.parseDOM(r, 'form', ret='action')[0]

                post = {'post_password': '300mbfilms', 'Submit': 'Submit'}
                send_post = client.request(plink, post=post, output='cookie')
                link = client.request(r1, cookie=send_post)
            else:
                link = client.request(r1)

            link = re.findall('<strong>Single(.+?)</tr', link, re.DOTALL)[0]
            link = client.parseDOM(link, 'a', ret='href')
            for i in link:
                if 'earn-money-onlines.info' in i:
                    trim = i.replace('protector1.php', 'protector.php')
                    r = client.request(trim)
                    filter_links = re.compile('<center> <a href="(.+?)"').findall(r)
                    for i in filter_links:
                        if any(x in i for x in ['uptobox', 'clicknupload']):
                            continue
                        urls.append(i)
                else:
                    urls.append(i)

            return urls
        except Exception:
            pass

    def resolve(self, url):
        return url
