# -*- coding: UTF-8 -*-
#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# @dev name wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################

# - Converted to py3/2 for dev name



import re
from datetime import datetime

import requests

import xbmc
from bs4 import BeautifulSoup, NavigableString
from microjenscrapers import urlencode
from microjenscrapers.modules import cleantitle, jsunpack, log_utils
from microjenscrapers.modules.client import randomagent


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['primewire.gr']
        self.base_link = 'https://www.primewire.gr'

        # Use the **mobile** version of the website, a bit less traffic needed from them.
        self.BASE_URL = 'http://m.primewire.gr'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            lowerTitle = title.lower()
            possibleTitles = set(
                (lowerTitle, cleantitle.getsearch(lowerTitle))
                + tuple((alias['title'].lower() for alias in aliases) if aliases else ())
            )
            return self._getSearchData(lowerTitle, possibleTitles, year, self._createSession(), isMovie=True)
        except:
            log_utils.log('PrimewireGR - Exception', 1)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            lowerTitle = tvshowtitle.lower()
            possibleTitles = set(
                (lowerTitle, cleantitle.getsearch(lowerTitle))
                + tuple((alias['title'].lower() for alias in aliases) if aliases else ())
            )
            return self._getSearchData(lowerTitle, possibleTitles, year, self._createSession(), isMovie=False)
        except:
            log_utils.log('PrimewireGR - Exception', 1)
            return

    def episode(self, data, imdb, tvdb, title, premiered, season, episode):
        try:
            seasonsPageURL = data['pageURL']

            # An extra step needed before sources() can be called. Get the episode page.
            # This code will crash if they change the website structure in the future.

            session = self._createSession(data['UA'], data['cookies'], data['referer'])
            xbmc.sleep(1000)
            r = self._sessionGET(seasonsPageURL, session)
            if r.ok:
                soup = BeautifulSoup(r.content, 'html.parser')
                mainDIV = soup.find('div', {'class': 'tv_container'})
                firstEpisodeDIV = mainDIV.find('div', {'class': 'show_season', 'data-id': season})
                # Filter the episode HTML entries to find the one that represents the episode we're after.
                episodeDIV = next((element for element in firstEpisodeDIV.next_siblings if not isinstance(
                    element, NavigableString) and next(element.a.strings, '').strip('E ') == episode), None)
                if episodeDIV:
                    return {
                        'pageURL': self.BASE_URL + episodeDIV.a['href'],
                        'UA': session.headers['User-Agent'],
                        'referer': seasonsPageURL,
                        'cookies': session.cookies.get_dict()
                    }
            return None
        except:
            log_utils.log('PrimewireGR - Exception', 1)
            return

    def sources(self, data, hostDict, hostprDict):
        try:
            session = self._createSession(data['UA'], data['cookies'], data['referer'])
            pageURL = data['pageURL']

            xbmc.sleep(1000)
            r = self._sessionGET(pageURL, session)
            if not r.ok:
                return

            sources = []

            soup = BeautifulSoup(r.content, 'html.parser')
            mainDIV = soup.find('div', class_='actual_tab')
            for hostBlock in mainDIV.findAll('tbody'):

                # All valid host links always have an 'onclick' attribute.
                if 'onclick' in hostBlock.a.attrs:
                    onClick = hostBlock.a['onclick']
                    if 'Promo' in onClick:
                        continue  # Ignore ad links.

                    hostName = re.search('''['"](.*?)['"]''', onClick).group(1)
                    qualityClass = hostBlock.span['class']
                    quality = 'SD' if ('cam' not in qualityClass and 'ts' not in qualityClass) else 'CAM'

                    # Send data for the resolve() function below to use later, when the user plays an item.
                    unresolvedData = {
                        'pageURL': self.BASE_URL + hostBlock.a['href'],  # Not yet usable, see resolve().
                        'UA': data['UA'],
                        'cookies': session.cookies.get_dict(),
                        'referer': pageURL
                    }
                    sources.append(
                        {
                            'source': hostName,
                            'quality': quality,
                            'language': 'en',
                            'url': unresolvedData,
                            'direct': False,
                            'debridonly': False
                        }
                    )
            return sources
        except:
            log_utils.log('PrimewireGR - Exception', 1)
            return sources

    def resolve(self, data):
        try:
            hostURL = None
            DELAY_PER_REQUEST = 1000  # In milliseconds.

            startTime = datetime.now()
            session = self._createSession(data['UA'], data['cookies'], data['referer'])
            r = self._sessionGET(data['pageURL'], session, allowRedirects=False)
            if r.ok:
                if 'Location' in r.headers:
                    hostURL = r.headers['Location']  # For most hosts they redirect.
                else:
                    # On rare cases they JS-pack the host link in the page source.
                    try:
                        hostURL = re.search(r'''go\(\\['"](.*?)\\['"]\);''', jsunpack.unpack(r.text)).group(1)
                    except Exception:
                        pass  # Or sometimes their page is just broken.

            # Do a little delay, if necessary, between resolve() calls.
            elapsed = int((datetime.now() - startTime).total_seconds() * 1000)
            if elapsed < DELAY_PER_REQUEST:
                xbmc.sleep(max(DELAY_PER_REQUEST - elapsed, 100))

            return hostURL
        except:
            log_utils.log('PrimewireGR - Exception', 1)
            return

    def _getSearchData(self, query, possibleTitles, year, session, isMovie):
        try:
            searchURL = self.BASE_URL + ('/?' if isMovie else '/?tv=&') + urlencode({'search_keywords': query})
            r = self._sessionGET(searchURL, session)
            if not r.ok:
                return None

            bestGuessesURLs = []

            soup = BeautifulSoup(r.content, 'html.parser')
            mainDIV = soup.find('div', role='main')
            for resultDIV in mainDIV.findAll('div', {'class': 'index_item'}, recursive=False):
                # Search result titles in Primewire.gr are usually "[Name of Movie/TVShow] (yyyy)".
                # Example: 'Star Wars Legends: Legacy of the Force (2015)'
                match = re.search(r'(.*?)(?:\s\((\d{4})\))?$', resultDIV.a['title'].lower().strip())
                resultTitle, resultYear = match.groups()
                if resultTitle in possibleTitles:
                    if resultYear == year:  # 'resultYear' = '(yyyy)', with parenthesis.
                        bestGuessesURLs.insert(0, resultDIV.a['href'])  # Use year to make better guesses.
                    else:
                        bestGuessesURLs.append(resultDIV.a['href'])

            if bestGuessesURLs:
                return {
                    'pageURL': self.BASE_URL + bestGuessesURLs[0],
                    'UA': session.headers['User-Agent'],
                    'referer': searchURL,
                    'cookies': session.cookies.get_dict(),
                }
            else:
                return None
        except:
            log_utils.log('PrimewireGR - Exception', 1)
            return

    def _sessionGET(self, url, session, allowRedirects=True):
        try:
            return session.get(url, allow_redirects=allowRedirects, timeout=8)
        except Exception:
            return type('FailedResponse', (object,), {'ok': False})

    def _createSession(self, userAgent=None, cookies=None, referer=None):
        # Try to spoof a header from a web browser.
        session = requests.Session()
        session.headers.update(
            {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'User-Agent': userAgent if userAgent else randomagent(),
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': referer if referer else self.BASE_URL + '/',
                'Upgrade-Insecure-Requests': '1',
                'DNT': '1'
            }
        )
        if cookies:
            session.cookies.update(cookies)
        return session

