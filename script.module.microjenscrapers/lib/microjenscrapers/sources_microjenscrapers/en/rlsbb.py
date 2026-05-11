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

from six import ensure_text, ensure_str

from microjenscrapers import cfScraper
from microjenscrapers import parse_qs, urljoin, urlparse, urlencode, quote_plus
from microjenscrapers.modules import cleantitle, client, debrid, log_utils, source_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['rlsbb.com', 'rlsbb.ru', 'rlsbb.to', 'proxybb.com']
        self.base_link = 'http://rlsbb.to/'
        self.old_base_link = 'http://old3.rlsbb.to/'
        self.search_base_link = 'http://search.rlsbb.ru/'
        self.search_cookie = 'serach_mode=rlsbb'
        self.search_link = 'lib/search526049.php?phrase=%s&pindex=1&content=true'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('RLSBB - Exception', 1)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            log_utils.log('RLSBB - Exception', 1)
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
            log_utils.log('RLSBB - Exception', 1)
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:

            if url is None:
                return sources

            if debrid.status() is False:
                return sources

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            year = data['year']
            _year = re.findall('(\d{4})', data['premiered'])[0] if 'tvshowtitle' in data else year
            title = cleantitle.get_query(title)
            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year
            #premDate = ''

            query = '%s S%02dE%02d' % (title, int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (title, year)
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
            query = query.replace(" ", "-")

            _base_link = self.base_link if int(_year) >= 2021 else self.old_base_link

            #url = self.search_link % quote_plus(query)
            #url = urljoin(_base_link, url)

            url = _base_link + query
            #log_utils.log('rlsbb_url: ' + str(url))

            r = cfScraper.get(url).content

            if r is None and 'tvshowtitle' in data:
                season = re.search('S(.*?)E', hdlr)
                season = season.group(1)
                query = title
                query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
                query = query + "-S" + season
                query = query.replace("&", "and")
                query = query.replace("  ", " ")
                query = query.replace(" ", "-")
                url = _base_link + query
                r = cfScraper.get(url).content

            r = ensure_text(r, errors='replace')

            for loopCount in list(range(0, 2)):
                if loopCount == 1 or (r is None and 'tvshowtitle' in data):

                    #premDate = re.sub('[ \.]', '-', data['premiered'])
                    query = re.sub(r'[\\\\:;*?"<>|/\-\']', '', title)
                    query = query.replace(
                        "&", " and ").replace(
                        "  ", " ").replace(
                        " ", "-")  # throw in extra spaces around & just in case
                    #query = query + "-" + premDate

                    url = _base_link + query
                    url = url.replace('The-Late-Show-with-Stephen-Colbert', 'Stephen-Colbert')

                    r = cfScraper.get(url).content
                    r = ensure_text(r, errors='replace')

                posts = client.parseDOM(r, "div", attrs={"class": "content"})
                items = []
                for post in posts:
                    try:
                        u = client.parseDOM(post, 'a', ret='href')
                        for i in u:
                            try:
                                name = str(i)
                                if hdlr in name.upper():
                                    items.append(name)
                                #elif len(premDate) > 0 and premDate in name.replace(".", "-"):
                                    #items.append(name)
                            except:
                                pass
                    except:
                        pass

                if len(items) > 0:
                    break

            seen_urls = set()

            for item in items:
                try:
                    url = str(item)
                    url = client.replaceHTMLCodes(url)
                    url = ensure_str(url, errors='ignore')

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    host = url.replace("\\", "")
                    host2 = host.strip('"')
                    host = re.findall('([\w]+[.][\w]+)$', urlparse(host2.strip().lower()).netloc)[0]

                    if host not in hostDict:
                        continue
                    if any(x in host2 for x in ['.rar', '.zip', '.iso', '.part']):
                        continue

                    quality, info = source_utils.get_release_quality(host2)

                    info = ' | '.join(info)

                    sources.append({'source': host, 'quality': quality, 'language': 'en',
                                    'url': host2, 'info': info, 'direct': False, 'debridonly': True})
                except:
                    log_utils.log('RLSBB - Exception', 1)
                    pass
            check = [i for i in sources if not i['quality'] == 'CAM']
            if check:
                sources = check
            return sources
        except:
            log_utils.log('RLSBB - Exception', 1)
            return sources

    def resolve(self, url):
        return url
