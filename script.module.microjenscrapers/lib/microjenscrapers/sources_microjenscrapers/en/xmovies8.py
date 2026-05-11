# -*- coding: UTF-8 -*-

# MicroJen Scrapers module


import re, base64

from six import ensure_text

from microjenscrapers import cfScraper
from microjenscrapers import urljoin
from microjenscrapers.modules import client
from microjenscrapers.modules import cleantitle
from microjenscrapers.modules import dom_parser
from microjenscrapers.modules import log_utils

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['xmovies8.fm']
        self.base_link = 'https://www4.xmovies8.fm/'
        self.movies_search_path = 'search-movies/%s.html'


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            clean_title = cleantitle.geturl(title).replace('-','+')
            url = urljoin(self.base_link, self.movies_search_path % clean_title)
            #r = client.request(url)
            r = cfScraper.get(url).content
            r = ensure_text(r, errors='ignore')

            r = dom_parser.parse_dom(r, 'div', {'id': 'movie-featured'})
            r = [dom_parser.parse_dom(i, 'a', req=['href']) for i in r if i]
            r = [(i[0].attrs['href'], re.search('Release:\s*(\d+)', i[0].content)) for i in r if i]
            r = [(i[0], i[1].groups()[0]) for i in r if i[0] and i[1]]
            r = [(i[0], i[1]) for i in r if i[1] == year]
            if r[0]: 
                url = r[0][0]
                #log_utils.log('xmovies_murl: ' + repr(url))
                return url
            else: return
        except:
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            clean_title = cleantitle.geturl(tvshowtitle).replace('-','+')
            url = urljoin(self.base_link, self.movies_search_path % clean_title)
            return url
        except:
            log_utils.log('xmovies_exc1', 1)
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return
            #log_utils.log('xmovies_eurl0: ' + repr(url))
            r = cfScraper.get(url).content
            r = ensure_text(r, errors='ignore')
            seasons = client.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            seasons_urls = [client.parseDOM(s, 'a', ret='href')[0] for s in seasons]
            season_url = [u for u in seasons_urls if u.endswith('-season-%d.html' % int(season))][0]

            r2 = cfScraper.get(season_url).content
            r2 = ensure_text(r2, errors='ignore')
            episodes = client.parseDOM(r2, 'div', attrs={'id': 'details', 'class': 'section-box'})[0]
            episodes = client.parseDOM(episodes, 'a', ret='href')
            url = [e for e in episodes if e.endswith('episode-%d.html' % int(episode))][0]
            #log_utils.log('xmovies_eurl: ' + repr(url))
            return url
        except:
            log_utils.log('xmovies_exc2', 1)
            return


    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            r = cfScraper.get(url).content
            r = ensure_text(r, errors='ignore')
            r = client.parseDOM(r, 'p', attrs={'class': 'server_version'})
            for i in r:
                try:
                    link = client.parseDOM(i, 'a', ret='href')[0]
                    #link = link.replace('\/','/')
                    host = client.parseDOM(i, 'img', ret='src')[0]
                    host = re.findall('logo/(\w+).', host, re.I|re.S)[0]
                    host = client.replaceHTMLCodes(host).lower()
                    if host in str(hostDict):
                        sources.append({
                            'source': host,
                            'quality': 'SD',
                            'language': 'en',
                            'url': link,
                            'direct': False,
                            'debridonly': False
                        })
                    if len(sources) >= 300: break
                except:
                    pass
            return sources
        except:
            log_utils.log('xmovies_exc0', 1)
            return


    def resolve(self, url):
        try:
            r = cfScraper.get(url).content
            r = ensure_text(r, errors='ignore')
            url = re.findall('document.write.+?"([^"]*)', r)[0]
            url = base64.b64decode(url)
            url = ensure_text(url, errors='ignore')
            #log_utils.log('xmovies_rurl0: ' + repr(url))
            try: url = client.parseDOM(url, 'iframe', ret='src')[0]
            except: url = client.parseDOM(url, 'a', ret='href')[0]
            url = url.replace('///', '//')
            #log_utils.log('xmovies_rurl: ' + repr(url))
            return url
        except:
            return
