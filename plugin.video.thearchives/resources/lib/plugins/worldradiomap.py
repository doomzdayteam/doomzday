import sys
import json
import re
from urllib.parse import quote, urljoin
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


class WorldRadioMap(Plugin):
    name = "worldradiomap"
    priority = 1100

    def __init__(self):
        self.session = DI.session
        self.base_url = 'https://worldradiomap.com'
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.headers = {
            "User-Agent": self.user_agent,
            "Referer": self.base_url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.session.headers.update(self.headers)
        self.list_url = f'{self.base_url}/list/'
        self.search_url = f'{self.base_url}/search'

   
    def _is_play_url(self, url: str) -> bool:
        return 'worldradiomap.com' in url and '/play/' in url and url.endswith('.htm')

    def _is_city_url(self, url: str) -> bool:
        if '/play/' in url:
            return False
        return bool(re.match(r'https?://worldradiomap\.com/.+/.+\.htm$', url))

    def _is_region_url(self, url: str) -> bool:
        if url.rstrip('/') == self.base_url:
            return False
        return bool(re.match(r'https?://worldradiomap\.com/[a-z\-]+/?$', url))

   
    def get_list(self, url):
        if url != self.search_url:
            return
        query = self.from_keyboard()
        if not query:
            sys.exit()
        response = self.session.get(self.list_url, headers=self.headers)
        self._search_query = query
        return response.text

   
    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not url.startswith(self.base_url) and url != self.search_url:
            return

        soup = BeautifulSoup(response, 'html.parser')
        itemlist = []

        
        if url == self.search_url:
            query = getattr(self, '_search_query', '')
            if query:
                itemlist.extend(self._filter_cities(soup, query))
            return itemlist

        
        if url.rstrip('/') == self.base_url:
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Cities[/COLOR]',
                'link': self.search_url
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Browse All Cities[/COLOR]',
                'link': self.list_url
            })
            itemlist.extend(self._parse_featured(soup))
            return itemlist

        
        if url.rstrip('/') == self.list_url.rstrip('/'):
            itemlist.extend(self._parse_city_list(soup))
            return itemlist

        
        if self._is_city_url(url):
            itemlist.extend(self._parse_city_stations(soup))
            return itemlist

        
        if self._is_region_url(url):
            itemlist.extend(self._parse_region(soup))
            return itemlist

        return itemlist

    def play_video(self, item) -> Optional[bool]:
        
        try:
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            data = json.loads(item)
            link = data.get('link', '')
        except (json.JSONDecodeError, TypeError, AttributeError):
            
            if isinstance(item, str) and self._is_play_url(item):
                link = item
                data = {'title': 'Radio', 'link': link}
            else:
                return

        if not self._is_play_url(link):
            return

        
        try:
            response = self.session.get(link, headers=self.headers)
            stream_url = self._resolve_stream(response.text)
        except Exception as e:
            xbmc.log(f'[WorldRadioMap] Error fetching play page: {e}', xbmc.LOGERROR)
            return

        if not stream_url:
            xbmc.log(f'[WorldRadioMap] No stream URL found on {link}', xbmc.LOGWARNING)
            return

        
        title = data.get('title', 'Radio')
        thumbnail = data.get('thumbnail', default_icon)
        liz = xbmcgui.ListItem(title, path=stream_url)
        set_music_info(liz, {'title': title})
        liz.setArt({
            'thumb': thumbnail,
            'icon': thumbnail,
            'fanart': FANART
        })
        liz.setProperty('IsPlayable', 'true')
        xbmc.Player().play(stream_url, liz)
        return True

    def _resolve_stream(self, html: str) -> Optional[str]:
        
        soup = BeautifulSoup(html, 'html.parser')

        
        audio = soup.find('audio')
        if audio:
            source = audio.find('source')
            if source and source.get('src'):
                return source['src']
            if audio.get('src'):
                return audio['src']

        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(ext in href for ext in ('.mp3', '.aac', '.ogg', '.m3u', '.pls', '.m3u8')):
                return href if href.startswith('http') else urljoin(self.base_url, href)

        
        stream_match = re.search(
            r'(https?://[^\s\'"<>]+\.(?:mp3|aac|ogg|m3u8|pls|m3u)(?:\?[^\s\'"<>]*)?)',
            html
        )
        if stream_match:
            return stream_match.group(1)

        return None

    
    def _parse_featured(self, soup) -> list:
        items = []
        seen_links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/play/' not in href:
                continue
            img = a.find('img')
            if not img:
                continue
            link = urljoin(self.base_url, href)
            if link in seen_links:
                continue
            seen_links.add(link)
            title = img.get('alt', '').strip()
            if not title:
                strong = a.find('strong')
                title = strong.text.strip() if strong else 'Unknown Station'
            thumbnail = urljoin(self.base_url, img['src']) if img.get('src') else ''
            if 'icon.gif' in thumbnail or 'outer.png' in thumbnail:
                thumbnail = ''
            items.append({
                'type': 'item',
                'title': title,
                'link': link,
                'thumbnail': thumbnail,
                'is_playable': 'true'
            })
        return items

    def _parse_city_list(self, soup) -> list:
        items = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if not href.endswith('.htm'):
                continue
            full_url = urljoin(self.base_url, href)
            if not self._is_city_url(full_url):
                continue
            title = a.text.strip()
            if not title:
                continue
            items.append({
                'type': 'dir',
                'title': title,
                'link': full_url
            })
        return items

    def _parse_city_stations(self, soup) -> list:
        items = []
        seen_links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/play/' not in href or not href.endswith('.htm'):
                continue

            link = urljoin(self.base_url, href)
            if link in seen_links:
                continue
            seen_links.add(link)

            img = a.find('img')
            thumbnail = ''
            title_parts = []

            if img:
                alt = img.get('alt', '').strip()
                if alt:
                    title_parts.append(alt)
                thumbnail = urljoin(self.base_url, img['src']) if img.get('src') else ''

            link_text = a.get_text(strip=True)
            if link_text and link_text not in title_parts:
                title_parts.append(link_text)

            parent_row = a.find_parent('tr')
            freq = ''
            if parent_row:
                first_td = parent_row.find('td')
                if first_td:
                    freq = first_td.get_text(strip=True)

            title = ' '.join(title_parts) if title_parts else 'Unknown Station'
            if freq:
                title = f'{freq} - {title}'

            if 'icon.gif' in (thumbnail or '') or 'outer.png' in (thumbnail or ''):
                thumbnail = ''

            items.append({
                'type': 'item',
                'title': title,
                'link': link,
                'thumbnail': thumbnail,
                'is_playable': 'true'
            })
        return items

    def _parse_region(self, soup) -> list:
        items = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if not href.endswith('.htm'):
                continue
            full_url = urljoin(self.base_url, href)
            if self._is_city_url(full_url):
                title = a.text.strip()
                if title:
                    items.append({
                        'type': 'dir',
                        'title': title,
                        'link': full_url
                    })
        return items

    def _filter_cities(self, soup, query: str) -> list:
        results = []
        query_lower = query.lower()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if not href.endswith('.htm'):
                continue
            full_url = urljoin(self.base_url, href)
            if not self._is_city_url(full_url):
                continue
            title = a.text.strip()
            if title and query_lower in title.lower():
                results.append({
                    'type': 'dir',
                    'title': title,
                    'link': full_url
                })
        return results

    def from_keyboard(self, default_text='', header='Search Cities'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
