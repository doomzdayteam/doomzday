# -*- coding: UTF-8 -*-
# - Converted to py3/2 for dev name


import re, base64

import six

from microjenscrapers import cfScraper
from microjenscrapers import parse_qs, urljoin, urlparse, urlencode, quote_plus
from microjenscrapers.modules import client, cleantitle, source_utils, log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['www2.putlockers.gs', 'putlockerfree.net', 'www8.putlockers.fm', 'putlocker.unblckd.pw']
        self.base_link = 'https://www2.putlockers.gs/'
        self.search_link = 'search-movies/%s.html'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year, 'aliases': aliases}
            url = urlencode(url)
            return url
        except:
            log_utils.log('plockers0 Exception', 1)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('plockers1 Exception', 1)
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
            log_utils.log('plockers2 Exception', 1)
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None: return sources

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = cleantitle.get_query(title)
            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']
            query = '%s season %d' % (title, int(data['season'])) if 'tvshowtitle' in data else title
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            query = quote_plus(query)

            url = urljoin(self.base_link, self.search_link % query)

            ua = {'User-Agent': client.agent()}
            r = cfScraper.get(url, headers=ua).content
            r = six.ensure_text(r, errors='replace')
            _posts = client.parseDOM(r, 'div', attrs={'class': 'item'})
            posts = []
            for p in _posts:
                try:
                    post = (client.parseDOM(p, 'a', ret='href')[1],
                              client.parseDOM(p, 'a')[1],
                              re.findall(r'Release:\s*?(\d{4})</', p, re.I|re.S)[1])
                    posts.append(post)
                except:
                    pass
            posts = [(i[0], client.parseDOM(i[1], 'i')[0], i[2]) for i in posts if i]

            if 'tvshowtitle' in data:
                sep = 'season %d' % int(data['season'])
                sepi = 'season-%1d/episode-%1d.html' % (int(data['season']), int(data['episode']))
                post = [i[0] for i in posts if sep in i[1].lower()][0]
                data = cfScraper.get(post, headers=ua).content
                data = six.ensure_text(data, errors='replace')
                link = client.parseDOM(data, 'a', ret='href')
                link = [i for i in link if sepi in i][0]
            else:
                link = [i[0] for i in posts if cleantitle.get_title(title) in cleantitle.get_title(i[1]) and hdlr == i[2]][0]

            r = cfScraper.get(link, headers=ua).content
            r = six.ensure_text(r, errors='replace')
            try:
                v = re.findall('document.write\(Base64.decode\("(.+?)"\)', r)[0]
                v = v.encode('utf-8')
                b64 = base64.b64decode(v)
                b64 = six.ensure_text(b64, errors='ignore')
                url = client.parseDOM(b64, 'iframe', ret='src')[0]
                try:
                    host = re.findall('([\w]+[.][\w]+)$', urlparse(url.strip().lower()).netloc)[0]
                    host = client.replaceHTMLCodes(host)
                    host = six.ensure_str(host)
                    valid, hoster = source_utils.is_host_valid(host, hostDict)
                    if valid:
                        sources.append({
                            'source': hoster,
                            'quality': 'SD',
                            'language': 'en',
                            'url': url.replace('\/', '/'),
                            'direct': False,
                            'debridonly': False
                        })
                except:
                    log_utils.log('plockers4 Exception', 1)
                    pass
            except:
                log_utils.log('plockers3 Exception', 1)
                pass
            r = client.parseDOM(r, 'div', {'class': 'server_line'})
            r = [(client.parseDOM(i, 'a', ret='href')[0],
                  client.parseDOM(i, 'p', attrs={'class': 'server_servername'})[0]) for i in r]
            if r:
                for i in r:
                    try:
                        host = re.sub('Server|Link\s*\d+', '', i[1]).lower()
                        url = i[0].replace('\/', '/')
                        host = client.replaceHTMLCodes(host)
                        host = six.ensure_str(host)
                        if 'other' in host: continue
                        valid, hoster = source_utils.is_host_valid(host, hostDict)
                        if valid:
                            sources.append({
                                'source': hoster,
                                'quality': 'SD',
                                'language': 'en',
                                'url': url,
                                'direct': False,
                                'debridonly': False
                            })
                    except:
                        log_utils.log('plockers5 Exception', 1)
                        pass
            return sources
        except:
            log_utils.log('plockers Exception', 1)
            return

    def resolve(self, url):
        if 'putlocker' in url:
            try:
                r = client.request(url)
                r = six.ensure_text(r, errors='replace')
                try:
                    v = re.findall('document.write\(Base64.decode\("(.+?)"\)', r)[0]
                    v = v.encode('utf-8')
                    b64 = base64.b64decode(v)
                    b64 = six.ensure_text(b64, errors='ignore')
                    url = client.parseDOM(b64, 'iframe', ret='src')[0]
                    url = url.replace('///', '//')
                except:
                    u = client.parseDOM(r, 'div', attrs={'class': 'player'})
                    url = client.parseDOM(u, 'a', ret='href')[0]
            except:
                log_utils.log('plockersR Exception', 1)

            return url
        else:
            return url
