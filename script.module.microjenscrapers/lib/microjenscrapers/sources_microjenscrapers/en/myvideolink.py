# -*- coding: utf-8 -*-

'''
    MicroJen Scrapers module
'''



import re

from six import ensure_text
from six.moves import zip

from microjenscrapers import parse_qs, urljoin, urlencode, quote_plus
from microjenscrapers.modules import cleantitle, client, source_utils, log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['myvideolinks.net', 'iwantmyshow.tk', 'new.myvideolinks.net']
        self.base_link = 'https://see.home.kg'
        #self.base_link = 'http://kita.myvideolinks.net'
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

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s S%02dE%02d' % (
                title,
                int(data['season']),
                int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (
                title,
                data['year'])
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)

            #r = client.request(self.base_link)
            #search_base = client.parseDOM(r, 'form', ret='action')[0]
            #log_utils.log(search_base)
            #url = urljoin(search_base, self.search_link)
            url = urljoin(self.base_link, self.search_link)
            url = url % quote_plus(query)

            r = client.request(url)
            results = client.parseDOM(r, 'article', attrs={'id': 'post-\d+'})
            if not 'tvshowtitle' in data: results = [i for i in results if data['imdb'] in i]
            p = client.parseDOM(results, 'h2')
            z = zip(client.parseDOM(p, 'a', ret='href'), client.parseDOM(p, 'a'))

            if 'tvshowtitle' in data:
                posts = [(i[1], i[0]) for i in z]
            else:
                posts = [(i[1], i[0]) for i in z]

            host_dict = hostprDict + hostDict

            items = []

            for post in posts:
                try:
                    r = client.request(post[1])
                    r = ensure_text(r, errors='replace')
                    r = client.parseDOM(r, 'div', attrs={'class': 'entry-content cf'})[0]

                    if 'tvshowtitle' in data:
                        z = zip(re.findall(r'<p><b>(%s.+?)</b>' % title, r, re.I | re.S), re.findall(r'<ul>(.+?)</ul>', r, re.S))
                        for f in z:
                            u = re.findall(r'\'(http.+?)\'', f[1]) + re.findall(r'\"(http.+?)\"', f[1])
                            u = [i for i in u if '/embed/' not in i]
                            t = f[0]
                            try: s = re.findall(r'((?:\d+\.\d+|\d+\,\d+|\d+|\d+\,\d+\.\d+)\s*(?:GB|GiB|MB|MiB))', t)[0]
                            except: s = '0'
                            items += [(t, i, s) for i in u]

                    else:
                        t = ensure_text(post[0], errors='replace')
                        u = re.findall(r'\'(http.+?)\'', r) + re.findall('\"(http.+?)\"', r)
                        u = [i for i in u if '/embed/' not in i]
                        try: s = re.findall(r'((?:\d+\.\d+|\d+\,\d+|\d+|\d+\,\d+\.\d+)\s*(?:GB|GiB|MB|MiB))', r)[0]
                        except: s = '0'
                        items += [(t, i, s) for i in u]

                except:
                    log_utils.log('MYVIDEOLINK ERROR', 1)
                    pass

            for item in items:
                try:
                    url = ensure_text(item[1])
                    url = client.replaceHTMLCodes(url)

                    void = ('.rar', '.zip', '.iso', '.part', '.png', '.jpg', '.bmp', '.gif', 'sub', 'srt')
                    if url.endswith(void):
                        continue

                    name = ensure_text(item[0], errors='replace')
                    name = client.replaceHTMLCodes(name)

                    t = re.sub(r'(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d*|3D)(\.|\)|\]|\s|)(.+|)', '', name, re.I)
                    if not cleantitle.get(t) == cleantitle.get(title):
                        continue

                    y = re.findall(r'[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', name)[-1].upper()
                    if not y == hdlr:
                        continue

                    valid, host = source_utils.is_host_valid(url, host_dict)
                    if not valid:
                        continue
                    host = client.replaceHTMLCodes(host)

                    quality, info = source_utils.get_release_quality(name, url)

                    try:
                        size = item[2]
                        dsize, isize = source_utils._size(size)
                    except:
                        dsize, isize = 0.0, ''
                    info.insert(0, isize)

                    info = ' | '.join(info)

                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info,
                                    'direct': False, 'debridonly': False, 'size': dsize, 'name': name})
                except:
                    log_utils.log('MYVIDEOLINK ERROR', 1)
                    pass

            return sources
        except:
            log_utils.log('MYVIDEOLINK ERROR', 1)
            return sources


    def resolve(self, url):
        return url
