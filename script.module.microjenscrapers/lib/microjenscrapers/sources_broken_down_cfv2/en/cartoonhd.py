# -*- coding: utf-8 -*-
# -Cleaned and Checked on 04-14-2020 by dev name.
# -Converted to py3/2 for dev name
# -As of May/21 site went login-only


import re
import simplejson as json
import base64
import time

import six

from microjenscrapers import parse_qs, urljoin, urlparse, urlencode, quote, unquote_plus
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import directstream
from microjenscrapers.modules import source_utils, log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['cartoonhd.care']
        self.base_link = 'https://cartoonhd.app'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            aliases.append({'country': 'us', 'title': title})
            url = {'imdb': imdb, 'title': title, 'year': year, 'aliases': aliases}
            url = urlencode(url)
            return url
        except:
            log_utils.log('cartoonhd - Exception', 1)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            aliases.append({'country': 'us', 'title': tvshowtitle})
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year, 'aliases': aliases}
            url = urlencode(url)
            return url
        except:
            log_utils.log('cartoonhd - Exception', 1)
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
        except:
            log_utils.log('cartoonhd - Exception', 1)
            return

    def searchShow(self, title, season, episode, aliases, headers):
        try:
            for alias in aliases:
                url = '%s/tv-show/%s/season/%01d/episode/%01d' % (self.base_link, cleantitle.geturl(title), int(season), int(episode))
                url = client.request(url, headers=headers, output='geturl', timeout='10')
                if url is not None and url != self.base_link:
                    break
            return url
        except:
            log_utils.log('cartoonhd - Exception', 1)
            return

    def searchMovie(self, title, year, aliases, headers):
        try:
            for alias in aliases:
                url = '%s/full-movie/%s' % (self.base_link, cleantitle.geturl(alias['title']))
                url = client.request(url, headers=headers, output='geturl', timeout='10')
                if url is not None and url != self.base_link:
                    break
            if url is None:
                for alias in aliases:
                    url = '%s/full-movie/%s-%s' % (self.base_link, cleantitle.geturl(alias['title']), year)
                    url = client.request(url, headers=headers, output='geturl', timeout='10')
                    if url is not None and url != self.base_link:
                        break

            return url
        except:
            log_utils.log('cartoonhd - Exception', 1)
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            imdb = data['imdb']
            aliases = eval(data['aliases'])
            headers = {}

            if 'tvshowtitle' in data:
                url = self.searchShow(title, int(data['season']), int(data['episode']), aliases, headers)
            else:
                url = self.searchMovie(title, data['year'], aliases, headers)

            r = client.request(url, headers=headers, output='extended', timeout='10')

            #if imdb not in r[0]:
                #raise Exception()

            try:
                cookie = r[4]
                headers = r[3]
            except:
                cookie = r[3]
                headers = r[2]
            result = r[0]

            try:
                r = re.findall('(https:.*?redirector.*?)[\'\"]', result)
                for i in r:
                    try:
                        sources.append(
                            {'source': 'gvideo', 'quality': directstream.googletag(i)[0]['quality'], 'language': 'en',
                             'url': i, 'direct': True, 'debridonly': False})
                    except:
                        pass
            except:
                pass

            try: auth = re.findall('__utmx=(.+)', cookie)[0].split(';')[0]
            except: auth = 'false'
            auth = 'Bearer %s' % unquote_plus(auth)
            headers['Authorization'] = auth
            headers['Referer'] = url

            u = '/ajax/vsozrflxcw.php'
            self.base_link = client.request(self.base_link, headers={'User-Agent': client.agent()}, output='geturl')
            u = urljoin(self.base_link, u)

            action = 'getEpisodeEmb' if '/episode/' in url else 'getMovieEmb'

            tim = str(int(time.time())) if six.PY2 else six.ensure_binary(str(int(time.time())))
            elid = quote(base64.encodestring(tim)).strip()

            token = re.findall("var\s+tok\s*=\s*'([^']+)", result)[0]

            idEl = re.findall('elid\s*=\s*"([^"]+)', result)[0]

            post = {'action': action, 'idEl': idEl, 'token': token, 'nopop': '', 'elid': elid}
            post = urlencode(post)
            cookie += ';%s=%s' % (idEl, elid)
            headers['Cookie'] = cookie

            r = client.request(u, post=post, headers=headers, cookie=cookie, XHR=True)
            r = str(json.loads(r))

            r = re.findall('\'(http.+?)\'', r) + re.findall('\"(http.+?)\"', r)

            for i in r:
                try:
                    if 'google' in i:
                        quality = 'SD'

                        if 'googleapis' in i:
                            try:
                                quality = source_utils.check_sd_url(i)
                            except Exception:
                                pass

                        if 'googleusercontent' in i:
                            i = directstream.googleproxy(i)
                            try:
                                quality = directstream.googletag(i)[0]['quality']
                            except Exception:
                                pass

                        sources.append({'source': 'gvideo', 'quality': quality, 'language': 'en', 'url': i,
                                        'direct': True, 'debridonly': False})

                    elif 'llnwi.net' in i or 'vidcdn.pro' in i:
                        try:
                            quality = source_utils.check_sd_url(i)
                            sources.append({'source': 'CDN', 'quality': quality, 'language': 'en', 'url': i,
                                            'direct': True, 'debridonly': False})

                        except Exception:
                            pass
                    else:
                        valid, hoster = source_utils.is_host_valid(i, hostDict)
                        if valid:
                            if 'vidnode.net' in i:
                                i = i.replace('vidnode.net', 'vidcloud9.com')
                                hoster = 'vidcloud9'
                            sources.append({'source': hoster, 'quality': '720p', 'language': 'en', 'url': i,
                                            'direct': False, 'debridonly': False})
                except Exception:
                    pass
            return sources
        except:
            log_utils.log('cartoonhd - Exception', 1)
            return sources

    def resolve(self, url):
        if 'google' in url and 'googleapis' not in url:
            return directstream.googlepass(url)
        else:
            return url
