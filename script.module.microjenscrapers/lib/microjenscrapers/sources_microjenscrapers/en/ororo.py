# -*- coding: utf-8 -*-

'''
    dev name Add-on

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

# - Converted to py3/2 for dev name


import re,base64

import simplejson as json

from microjenscrapers import urljoin
from microjenscrapers.modules import cache
from microjenscrapers.modules import control
from microjenscrapers.modules import client
from microjenscrapers.modules import log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['ororo.tv']
        self.base_link = 'https://ororo.tv'
        self.moviesearch_link = '/api/v2/movies'
        self.tvsearch_link = '/api/v2/shows'
        self.movie_link = '/api/v2/movies/%s'
        self.show_link = '/api/v2/shows/%s'
        self.episode_link = '/api/v2/episodes/%s'

        self.user = control.setting('ororo.user')
        self.password = control.setting('ororo.pass')
        self.headers = {
        'Authorization': 'Basic %s' % base64.b64encode('%s:%s' % (self.user, self.password)),
        'User-Agent': 'dev name for Kodi'
        }


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            if (self.user == '' or self.password == ''): raise Exception()

            url = cache.get(self.ororo_moviecache, 60, self.user)
            url = [i[0] for i in url if imdb == i[1]][0]
            url= self.movie_link % url

            return url
        except Exception as e:
            log_utils.log('Ororo: '+str(e))
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            if (self.user == '' or self.password == ''): raise Exception()

            url = cache.get(self.ororo_tvcache, 120, self.user)
            url = [i[0] for i in url if imdb == i[1]][0]
            url= self.show_link % url

            return url
        except Exception as e:
            log_utils.log('Ororo: '+str(e))
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if (self.user == '' or self.password == ''): raise Exception()

            if url == None: return

            url = urljoin(self.base_link, url)

            r = client.request(url, headers=self.headers)
            r = json.loads(r)['episodes']
            r = [(str(i['id']), str(i['season']), str(i['number']), str(i['airdate'])) for i in r]

            url = [i for i in r if season == '%01d' % int(i[1]) and episode == '%01d' % int(i[2])]
            url += [i for i in r if premiered == i[3]]

            url= self.episode_link % url[0][0]

            return url
        except Exception as e:
            log_utils.log('Ororo: '+str(e))
            return


    def ororo_moviecache(self, user):
        try:
            url = urljoin(self.base_link, self.moviesearch_link)

            r = client.request(url, headers=self.headers)
            r = json.loads(r)['movies']
            r = [(str(i['id']), str(i['imdb_id'])) for i in r]
            r = [(i[0], 'tt' + re.sub('[^0-9]', '', i[1])) for i in r]
            return r
        except Exception as e:
            log_utils.log('Ororo: '+str(e))
            return


    def ororo_tvcache(self, user):
        try:
            url = urljoin(self.base_link, self.tvsearch_link)

            r = client.request(url, headers=self.headers)
            r = json.loads(r)['shows']
            r = [(str(i['id']), str(i['imdb_id'])) for i in r]
            r = [(i[0], 'tt' + re.sub('[^0-9]', '', i[1])) for i in r]
            return r
        except Exception as e:
            log_utils.log('Ororo: '+str(e))
            return


    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []

            if url == None: return sources

            if (self.user == '' or self.password == ''): raise Exception()

            url = urljoin(self.base_link, url)
            url = client.request(url, headers=self.headers)
            url = json.loads(url)['url']

            sources.append({'source': 'direct', 'quality': 'HD', 'language': 'en', 'url': url, 'direct': True, 'debridonly': False})

            return sources
        except Exception as e:
            log_utils.log('Ororo: '+str(e))
            return sources


    def resolve(self, url):
        return url


