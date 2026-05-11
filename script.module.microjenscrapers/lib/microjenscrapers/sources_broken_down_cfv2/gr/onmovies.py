# -*- coding: utf-8 -*-

'''
    Credits to dev name and dev name; our thanks go to their creators

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import urllib, urlparse, re, base64,json

from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import client
from microjenscrapers.modules import source_utils
from microjenscrapers.modules import dom_parser as dom
from microjenscrapers.modules import unjuice
from microjenscrapers.modules import directstream


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['gr']
        self.domains = ['onlinemovie.gr']
        self.base_link = 'https://onlinemovie.one'
        self.search_link = '/wp-json/dooplay/search/?keyword=%s&nonce=550898deed'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = self.__search([localtitle] + source_utils.aliases_to_array(aliases), year)
            if not url and title != localtitle: url = self.__search([title] + source_utils.aliases_to_array(
                aliases), year)
            return url
        except BaseException:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = self.__search([localtvshowtitle] + source_utils.aliases_to_array(aliases), year)
            if not url and tvshowtitle != localtvshowtitle: url = self.__search(
                [tvshowtitle] + source_utils.aliases_to_array(aliases), year)
            return url
        except BaseException:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return

            url = url[:-1] if url.endswith('/') else url
            t = url.split('/')[-1]
            url = self.base_link + '/episodes/' + t + '-%dx%d' % (int(season), int(episode))

            return url
        except BaseException:
            return

    def __search(self, titles, year):
        try:
            tit = [i.split(':')[0] for i in titles]
            query = [self.search_link % (urllib.quote_plus(cleantitle.getsearch(i))) for i in tit]
            query = [urlparse.urljoin(self.base_link, i) for i in query]
            t = [cleantitle.get(i) for i in set(titles) if i]
            for u in query:
                try:
                    r = client.request(u)
                    r = json.loads(r)
                    r = [(r[i]['url'], r[i]['title'], r[i]['extra']) for i in r if i]
                    r = [(i[0], i[1]) for i in r if i[2]['date'] == year ]
                    if len(r) == 1: return source_utils.strip_domain(r[0][0])
                    else:
                        r = [(i[0]) for i in r if cleantitle.get(i[1]) in t]
                        return source_utils.strip_domain(r[0])

                except BaseException:
                    pass

            return
        except BaseException:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []

        try:
            if not url:
                return sources

            query = urlparse.urljoin(self.base_link, url)
            r = client.request(query)

            r1 = client.parseDOM(r, 'div', attrs={'id':'playeroptions'})[0]
            links = dom.parse_dom(r1, 'li', req=['data-post', 'data-nume'])
            links = [(i.attrs['data-post'], i.attrs['data-nume'],
                      client.parseDOM(i.content, 'span', attrs={'class': 'title'})[0]) for i in links]
            links = [(i[0], i[1], i[2]) for i in links if not 'trailer' in i[1]]
            try:
                extra = client.parseDOM(r, 'div', attrs={'class': 'links_table'})[0]
                extra = dom.parse_dom(extra, 'td')
                extra = [dom.parse_dom(i.content, 'img', req='src') for i in extra if i]
                extra = [(i[0].attrs['src'], dom.parse_dom(i[0].content, 'a', req='href')) for i in extra if i]
                extra = [(re.findall('domain=(.+?)$', i[0])[0], i[1][0].attrs['href']) for i in extra if i]
            except BaseException:
                pass
            info = []
            ptype = 'tv' if '/tvshows/' in query else 'movie'
            for item in links:

                plink = 'https://onlinemovie.gr/wp-admin/admin-ajax.php'
                pdata = {'action': 'doo_player_ajax',
                         'post': item[0],
                         'nume': item[1],
                         'type': ptype}
                pdata = urllib.urlencode(pdata)
                link = client.request(plink, post=pdata)
                link = client.parseDOM(link, 'iframe', ret='src')[0]
                lang = 'gr'
                quality, info = source_utils.get_release_quality(item[2], item[2])
                info.append('SUB')
                info = ' | '.join(info)
                if 'jwplayer' in link:
                    sub = re.findall('&sub=(.+?)&id', link)[0]
                    sub = urllib.unquote(sub)
                    sub = urlparse.urljoin(self.base_link, sub) if sub.startswith('/sub/') else sub
                    url = re.findall('source=(.+?)&sub', link)[0]
                    url = urllib.unquote(url)
                    url = urlparse.urljoin(self.base_link, url) if url.startswith('/') else url

                    if 'cdn' in url or 'nd' in url or url.endswith('.mp4') or url.endswith('.m3u8'):
                        sources.append(
                            {'source': 'CDN', 'quality': quality, 'language': lang, 'url': url, 'info': info,
                             'direct': True, 'debridonly': False, 'sub': sub})

                elif 'api.myhls' in link:
                    quality2, info = source_utils.get_release_quality(item[2], None)
                    info.append('SUB')
                    info = ' | '.join(info)
                    data = client.request(link, referer=self.base_link)
                    if not unjuice.test(data): raise Exception()
                    r = unjuice.run(data)
                    urls = re.findall('''file['"]:['"]([^'"]+).+?label":['"]([^'"]+)''', r, re.DOTALL)
                    sub = [i[0] for i in urls if 'srt' in i[0]][0]
                    sub = urlparse.urljoin(self.base_link, sub) if sub.startswith('/sub/') else sub

                    urls = [(i[0], i[1]) for i in urls if not '.srt' in i[0]]
                    for i in urls:
                        host = 'GVIDEO'
                        quality, url = i[1].lower(), i[0]

                        url = '%s|User-Agent=%s&Referer=%s' % (url, urllib.quote(client.agent()), link)
                        sources.append(
                            {'source': host, 'quality': quality, 'language': lang, 'url': url, 'info': info,
                             'direct': True, 'debridonly': False, 'sub': sub})

                elif 'myhls.stream' in link:
                    vid = link.split('/')[-1]
                    plink = 'https://myhls.stream/api/source/%s' % vid
                    data = client.request(plink, post='r=', referer=link, XHR=True)
                    data = json.loads(data)

                    urls = data['data']

                    sub = data['captions'][0]['path']
                    sub = 'https://myhls.stream/asset' + sub if sub.startswith('/') else sub

                    for i in urls:
                        url = i['file'] if not i['file'].startswith('/') else 'https://myhls.stream/%s' % i['file']
                        quality = i['label']
                        host = 'CDN-HLS'

                        sources.append(
                            {'source': host, 'quality': quality, 'language': lang, 'url': url, 'info': info,
                             'direct': True, 'debridonly': False, 'sub': sub})

                elif 'drive' in link:
                    quality, info = source_utils.get_release_quality(item[1], None)
                    info.append('SUB')
                    info = ' | '.join(info)
                    try:
                        links = directstream.google(item[0])
                        for x in links:
                            sources.append(
                                {'source': 'GVIDEO', 'quality': x['quality'], 'language': lang, 'url': x['url'],
                                 'info': info, 'direct': True, 'debridonly': False, 'sub': sub})
                    except BaseException:
                        pass

                    try:
                        r = client.request(item[0])
                        links = re.findall('''\{file:\s*['"]([^'"]+)''', r, re.DOTALL)
                        for x in links:
                            sources.append(
                                {'source': 'GVIDEO', 'quality': quality, 'language': lang, 'url': x,
                                 'info': info, 'direct': True, 'debridonly': False, 'sub': sub})

                    except BaseException:
                        pass


                else:
                    continue

            for item in extra:
                url = item[1]
                if 'movsnely' in url:
                    url = client.request(url, output='geturl', redirect=True)
                else:
                    url = url
                quality = 'SD'
                lang, info = 'gr', 'SUB'
                valid, host = source_utils.is_host_valid(item[0], hostDict)
                if not valid: continue

                sources.append({'source': host, 'quality': quality, 'language': lang, 'url': url, 'info': info,
                                'direct': False, 'debridonly': False, 'sub': sub})

            return sources
        except BaseException:
            return sources

    def resolve(self, url):
        if 'onlinemovie' in url:
            url = client.request(url, output='geturl', redirect=True)
        return url
