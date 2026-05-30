import sys
import json
import re
from urllib.parse import urljoin
from typing import List, Optional, Dict
import xbmc
import xbmcgui
from xbmcaddon import Addon
from bs4 import BeautifulSoup
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_music_info
from ..DI import DI

FANART = Addon().getAddonInfo('fanart')
addon_id = Addon().getAddonInfo('id')
default_icon = Addon(addon_id).getAddonInfo('icon')


class AudiophileFM(Plugin):
    name = "audiophilefm"
    priority = 1100

    def __init__(self):
        self.session = DI.session
        self.base_url = 'https://audiophile.fm'
        self.search_url = f'{self.base_url}/search'
        self.sanity_project = 'orhkaa59'
        self.sanity_dataset = 'production'
        self.sanity_api = f'https://{self.sanity_project}.apicdn.sanity.io/v2022-06-01/data/query/{self.sanity_dataset}'
        self._ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def _is_station_url(self, url: str) -> bool:
        if url.rstrip('/') == self.base_url:
            return False
        if url == self.search_url:
            return False
        if '/contact' in url or '/faq' in url or '/about' in url or '/submit' in url:
            return False
        return bool(re.match(r'https?://audiophile\.fm/[a-z0-9\-]+/?$', url))

    def _fetch_stations_from_api(self) -> Optional[list]:
      
        query = (
            '*[_type == "station" && active == true] | order(title asc) '
            '{ title, "slug": slug.current, quality, description, '
            '"primaryUrl": streams.primary.url, '
            '"primaryFormat": streams.primary.format, '
            '"secondaryUrl": streams.secondary.url, '
            '"secondaryFormat": streams.secondary.format, '
            '"logoUrl": logo.asset->url, '
            '"genres": genres[]->name }'
        )
        try:
            resp = self.session.get(
                self.sanity_api,
                params={'query': query},
                headers={'User-Agent': self._ua}
            )
            data = resp.json()
            return data.get('result', [])
        except Exception as e:
            xbmc.log(f'[AudiophileFM] Sanity API error: {e}', xbmc.LOGERROR)
            return None

    def _fetch_stream_for_slug(self, slug: str) -> Optional[str]:
        
        query = (
            f'*[_type == "station" && slug.current == "{slug}"][0]'
            '{ "primaryUrl": streams.primary.url, "secondaryUrl": streams.secondary.url }'
        )
        try:
            resp = self.session.get(
                self.sanity_api,
                params={'query': query},
                headers={'User-Agent': self._ua}
            )
            result = resp.json().get('result')
            if result and isinstance(result, dict):
                return result.get('primaryUrl') or result.get('secondaryUrl') or ''
        except Exception as e:
            xbmc.log(f'[AudiophileFM] Sanity slug lookup error: {e}', xbmc.LOGERROR)
        return None

    def get_list(self, url):
        if url == self.search_url:
            query = self.from_keyboard()
            if not query:
                sys.exit()
            self._search_query = query
            return '__audiophilefm_search__'

        if url.rstrip('/') == self.base_url:
            return '__audiophilefm_home__'

        if self._is_station_url(url):
            return '__audiophilefm_station__'

        return

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not response or not isinstance(response, str):
            return
        if not response.startswith('__audiophilefm_'):
            if url and url.startswith(self.base_url):
                return self._parse_html_fallback(url, response)
            return

        stations = self._fetch_stations_from_api()
        itemlist = []

        
        if response == '__audiophilefm_search__':
            query = getattr(self, '_search_query', '')
            if query and stations:
                itemlist.extend(self._filter_stations(stations, query))
            elif query:
                itemlist.extend(self._html_search_fallback(query))
            return itemlist

        
        if response == '__audiophilefm_home__':
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Stations[/COLOR]',
                'link': self.search_url
            })
            if stations:
                itemlist.extend(self._stations_to_items(stations))
            else:
                itemlist.extend(self._html_home_fallback())
            return itemlist

        
        if response == '__audiophilefm_station__':
            slug = url.rstrip('/').split('/')[-1]
            if stations:
                for s in stations:
                    if s.get('slug') == slug:
                        return self._stations_to_items([s])
            title = slug.replace('-', ' ').title()
            return [{'type': 'item', 'title': title, 'link': url, 'is_playable': 'true'}]

        return itemlist

    
    def play_video(self, item) -> Optional[bool]:
        try:
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            data = json.loads(item)
            link = data.get('link', '')
        except (json.JSONDecodeError, TypeError, AttributeError):
            if isinstance(item, str) and self._is_station_url(item):
                link = item
                data = {'title': 'Radio', 'link': link}
            else:
                return

        if not self._is_station_url(link):
            return

       
        stream_url = data.get('stream_url', '')

       
        if not stream_url:
            slug = link.rstrip('/').split('/')[-1]
            stream_url = self._fetch_stream_for_slug(slug)

        if not stream_url:
            xbmc.log(f'[AudiophileFM] No stream URL for {link}', xbmc.LOGWARNING)
            return

        title = data.get('title', 'Radio')
        clean_title = re.sub(r'\[/?COLOR[^\]]*\]', '', title).strip()
        thumbnail = data.get('thumbnail', default_icon)

        liz = xbmcgui.ListItem(clean_title, path=stream_url)
        set_music_info(liz, {'title': clean_title})
        liz.setArt({
            'thumb': thumbnail,
            'icon': thumbnail,
            'fanart': FANART
        })
        liz.setProperty('IsPlayable', 'true')
        xbmc.Player().play(stream_url, liz)
        return True

    def _stations_to_items(self, stations: list) -> list:
        items = []
        for s in stations:
            title = s.get('title') or ''
            slug = s.get('slug') or ''
            if not title or not slug:
                continue

            link = f'{self.base_url}/{slug}'
            logo_url = s.get('logoUrl') or ''
            thumbnail = f'{logo_url}?w=400&q=80' if logo_url else ''
            quality = s.get('quality') or ''
            genres = s.get('genres') or []
            stream_url = s.get('primaryUrl') or s.get('secondaryUrl') or ''

            
            display_title = title
            if quality == 'hires':
                display_title = f'[COLOR gold][Hi-Res][/COLOR] {title}'
            elif quality == 'cd':
                display_title = f'[COLOR lime][CD-Quality][/COLOR] {title}'

            if genres and isinstance(genres, list):
                
                valid_genres = [str(g) for g in genres if g]
                if valid_genres:
                    genre_str = ' | '.join(valid_genres[:3])
                    display_title += f'  [COLOR gray]({genre_str})[/COLOR]'

            item = {
                'type': 'item',
                'title': display_title,
                'link': link,
                'thumbnail': thumbnail,
                'is_playable': 'true'
            }
            if stream_url:
                item['stream_url'] = stream_url
            items.append(item)
        return items

    def _filter_stations(self, stations: list, query: str) -> list:
        q = query.lower()
        filtered = []
        for s in stations:
            title = (s.get('title') or '').lower()
            desc = (s.get('description') or '').lower()
            genres = s.get('genres') or []
            genre_str = ' '.join(str(g).lower() for g in genres if g)
            if q in title or q in desc or q in genre_str:
                filtered.append(s)
        return self._stations_to_items(filtered)


    def _html_home_fallback(self) -> list:
        try:
            resp = self.session.get(self.base_url, headers={'User-Agent': self._ua})
            soup = BeautifulSoup(resp.text, 'html.parser')
            return self._parse_stations_html(soup)
        except:
            return []

    def _html_search_fallback(self, query: str) -> list:
        try:
            resp = self.session.get(self.base_url, headers={'User-Agent': self._ua})
            soup = BeautifulSoup(resp.text, 'html.parser')
            all_stations = self._parse_stations_html(soup)
            q = query.lower()
            return [s for s in all_stations
                    if q in re.sub(r'\[/?COLOR[^\]]*\]', '', s['title']).lower()]
        except:
            return []

    def _parse_html_fallback(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not response:
            return
        if not url.startswith(self.base_url) and url != self.search_url:
            return

        soup = BeautifulSoup(response, 'html.parser')

        if url == self.search_url:
            query = getattr(self, '_search_query', '')
            if query:
                all_stations = self._parse_stations_html(soup)
                q = query.lower()
                return [s for s in all_stations
                        if q in re.sub(r'\[/?COLOR[^\]]*\]', '', s['title']).lower()]
            return []

        if url.rstrip('/') == self.base_url:
            itemlist = [{
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Stations[/COLOR]',
                'link': self.search_url
            }]
            itemlist.extend(self._parse_stations_html(soup))
            return itemlist

        return []

    def _parse_stations_html(self, soup) -> list:
        items = []
        seen = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(self.base_url, href)
            if not self._is_station_url(full_url) or full_url in seen:
                continue
            seen.add(full_url)

            title = ''
            h = a.find(['h3', 'h2', 'h4'])
            if h:
                title = h.get_text(strip=True)
            if not title:
                title = a.get('title', '').replace('Play ', '')
            if not title:
                title = a.get_text(strip=True)
            if not title:
                continue

            thumbnail = ''
            img = a.find('img')
            if img:
                src = img.get('src', '') or img.get('data-src', '')
                if src and 'cdn.sanity.io' in src:
                    thumbnail = re.sub(r'\?w=\d+', '?w=400', src)
                elif src and 'play-white' not in src:
                    thumbnail = urljoin(self.base_url, src)

            genres = []
            quality = ''
            for li in a.find_all('li'):
                tag_text = li.get_text(strip=True)
                if tag_text in ('Hi-Res', 'CD-Quality'):
                    quality = tag_text
                elif tag_text:
                    genres.append(tag_text)

            display_title = title
            if quality:
                color = 'gold' if quality == 'Hi-Res' else 'lime'
                display_title = f'[COLOR {color}][{quality}][/COLOR] {title}'
            if genres:
                genre_str = ' | '.join(genres[:3])
                display_title += f'  [COLOR gray]({genre_str})[/COLOR]'

            items.append({
                'type': 'item',
                'title': display_title,
                'link': full_url,
                'thumbnail': thumbnail,
                'is_playable': 'true'
            })
        return items

    def from_keyboard(self, default_text='', header='Search Stations'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
