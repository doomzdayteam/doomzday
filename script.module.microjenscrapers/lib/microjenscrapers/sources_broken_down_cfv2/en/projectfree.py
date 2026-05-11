# -*- coding: UTF-8 -*-
# -Cleaned and Checked on 02-24-2019 by dev name in dev name.

import re,urllib,urlparse,traceback
from microjenscrapers.modules import cleantitle, source_utils, log_utils
from microjenscrapers import cfScraper


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['project-free-tv.ag','my-project-free.tv']
        self.base_link = 'https://projectfreetv.fun'
        self.search_link = '/episode/%s-season-%s-episode-%s/'


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            clean_title = cleantitle.geturl(tvshowtitle)
            url = clean_title
            return url
        except:
            failure = traceback.format_exc()
            log_utils.log('projectfree0 - Exception: \n' + str(failure))
            return
 
 
    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url: return
            tvshowtitle = url
            url = self.base_link + self.search_link % (tvshowtitle, int(season), int(episode))
            return url
        except:
            failure = traceback.format_exc()
            log_utils.log('projectfree1 - Exception: \n' + str(failure))
            return


    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []
            r = cfScraper.get(url).content
            try:
                data = re.compile("callvalue\('.+?','.+?','(.+?)://(.+?)/(.+?)'\)").findall(r)
                for http,host,url in data:
                    url = '%s://%s/%s' % (http,host,url)
                    valid, host = source_utils.is_host_valid(host, hostDict)
                    if valid:
                        sources.append({ 'source': host, 'quality': 'SD', 'language': 'en', 'url': url, 'direct': False, 'debridonly': False })
            except:
                failure = traceback.format_exc()
                log_utils.log('projectfree2 - Exception: \n' + str(failure))
                pass
            return sources
        except Exception:
            failure = traceback.format_exc()
            log_utils.log('projectfree3 - Exception: \n' + str(failure))
            return


    def resolve(self, url):
        return url

