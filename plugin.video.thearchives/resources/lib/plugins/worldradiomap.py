import sys
import json
import re
from html import unescape
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
        return bool(re.match(r'https?://worldradiomap\.com/.+/play/.+(?:\.htm)?/?$', str(url or '')))

    def _is_city_url(self, url: str) -> bool:
        if '/play/' in url:
            return False
        return bool(re.match(r'https?://worldradiomap\.com/.+/.+(?:\.htm)?/?$', str(url or '')))

    def _is_region_url(self, url: str) -> bool:
        url = str(url or '').rstrip('/')
        if url in (self.base_url, self.list_url.rstrip('/'), self.search_url.rstrip('/')):
            return False
        return bool(re.match(r'https?://worldradiomap\.com/[a-z\-]+/?$', url))

    def _message_item(self, title: str, summary: str = '') -> Dict[str, str]:
        return {
            'type': 'dir',
            'title': title,
            'link': self.base_url,
            'summary': summary
        }

   
    def get_list(self, url):
        if url == self.search_url:
            query = self.from_keyboard()
            if not query:
                sys.exit()
            response = self.session.get(self.list_url, headers=self.headers)
            return json.dumps({
                'kind': 'search',
                'query': query,
                'html': response.text
            })

        if url.startswith(self.base_url) and (
            url.rstrip('/') == self.base_url
            or url.rstrip('/') == self.list_url.rstrip('/')
            or self._is_city_url(url)
            or self._is_region_url(url)
        ):
            response = self.session.get(url, headers=self.headers)
            return response.text

        return

   
    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not url.startswith(self.base_url) and url != self.search_url:
            return

        soup = BeautifulSoup(response, 'html.parser')
        itemlist = []

        
        if url == self.search_url:
            query = ''
            html = response
            try:
                data = json.loads(response)
                if data.get('kind') == 'search':
                    query = data.get('query', '')
                    html = data.get('html', '')
                    soup = BeautifulSoup(html, 'html.parser')
            except (TypeError, json.JSONDecodeError):
                query = getattr(self, '_search_query', '')
            if query:
                itemlist.extend(self._filter_cities(soup, query))
            return itemlist or [self._message_item('[COLOR grey]No matching cities found[/COLOR]')]

        
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
            return itemlist or [self._message_item('[COLOR grey]No cities found[/COLOR]')]

        
        if self._is_city_url(url):
            itemlist.extend(self._parse_city_stations(soup, url, response))
            return itemlist or [self._message_item('[COLOR grey]No playable stations found[/COLOR]', url)]

        
        if self._is_region_url(url):
            itemlist.extend(self._parse_region(soup))
            return itemlist or [self._message_item('[COLOR grey]No cities found[/COLOR]')]

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
            stream_url = self._resolve_stream(response.text, link)
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
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(stream_url, liz)
        return True

    def _resolve_stream(self, html: str, page_url=None) -> Optional[str]:
        
        soup = BeautifulSoup(html, 'html.parser')

        
        audio = soup.find('audio')
        if audio:
            source = audio.find('source')
            if source and source.get('src'):
                return self._resolve_stream_candidate(urljoin(page_url or self.base_url, source['src']))
            if audio.get('src'):
                return self._resolve_stream_candidate(urljoin(page_url or self.base_url, audio['src']))

        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(ext in href for ext in ('.mp3', '.aac', '.ogg', '.m3u', '.pls', '.m3u8')):
                stream_url = href if href.startswith('http') else urljoin(page_url or self.base_url, href)
                return self._resolve_stream_candidate(stream_url)

        
        stream_match = re.search(
            r'(https?://[^\s\'"<>]+\.(?:mp3|aac|ogg|m3u8|pls|m3u)(?:\?[^\s\'"<>]*)?)',
            html
        )
        if stream_match:
            return self._resolve_stream_candidate(stream_match.group(1))

        return None

    def _resolve_stream_candidate(self, stream_url: str) -> str:
        lower_url = (stream_url or '').lower().split('?', 1)[0]
        if lower_url.endswith(('.m3u', '.pls')):
            return self._resolve_playlist_stream(stream_url) or stream_url
        return stream_url

    def _resolve_playlist_stream(self, playlist_url: str) -> Optional[str]:
        try:
            response = self.session.get(playlist_url, headers=self.headers)
        except Exception:
            return None

        for line in response.text.splitlines():
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('['):
                continue
            if line.lower().startswith('file') and '=' in line:
                line = line.split('=', 1)[1].strip()
            if line.startswith('http'):
                return line
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
            lower_thumbnail = (thumbnail or '').lower()
            if any(skip in lower_thumbnail for skip in ('icon.gif', 'outer.png')) or lower_thumbnail.endswith('.svg'):
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

    def _parse_city_stations(self, soup, page_url=None, html_text='') -> list:
        items = []
        seen_items = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/play/' not in href:
                continue

            link = urljoin(page_url or self.base_url, href)
            if not self._is_play_url(link):
                continue

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

            item_key = (freq, title, link)
            if item_key in seen_items:
                continue
            seen_items.add(item_key)

            lower_thumbnail = (thumbnail or '').lower()
            if any(skip in lower_thumbnail for skip in ('icon.gif', 'outer.png')) or lower_thumbnail.endswith('.svg'):
                thumbnail = ''

            items.append({
                'type': 'item',
                'title': title,
                'link': link,
                'thumbnail': thumbnail,
                'is_playable': 'true'
            })
        if not items and html_text:
            items = self._parse_city_stations_regex(html_text, page_url)
        try:
            xbmc.log(f'[WorldRadioMap] Parsed {len(items)} stations from {page_url}', xbmc.LOGINFO)
        except Exception:
            pass
        return items

    def _strip_html(self, value: str) -> str:
        value = re.sub(r'<[^>]+>', ' ', value or '')
        value = unescape(value).replace('\xa0', ' ')
        return re.sub(r'\s+', ' ', value).strip()

    def _parse_city_stations_regex(self, html_text: str, page_url=None) -> list:
        items = []
        seen_items = set()
        for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', html_text or '', re.I | re.S):
            if '/play/' not in row:
                continue
            anchor = re.search(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', row, re.I | re.S)
            if not anchor:
                continue
            href, anchor_html = anchor.groups()
            if '/play/' not in href:
                continue
            link = urljoin(page_url or self.base_url, href)
            if not self._is_play_url(link):
                continue

            freq = ''
            freq_match = re.search(r'<td\b[^>]*class=["\']?freq["\']?[^>]*>(.*?)</td>', row, re.I | re.S)
            if freq_match:
                freq = self._strip_html(freq_match.group(1))

            title = self._strip_html(anchor_html) or 'Unknown Station'
            if freq:
                title = f'{freq} - {title}'

            item_key = (freq, title, link)
            if item_key in seen_items:
                continue
            seen_items.add(item_key)

            thumbnail = ''
            for img_src in re.findall(r'<img\b[^>]*src=["\']([^"\']+)["\']', anchor_html, re.I):
                lower_src = img_src.lower()
                if any(skip in lower_src for skip in ('icon.gif', 'outer.png', 'nologo.svg')):
                    continue
                if lower_src.endswith('.svg'):
                    continue
                thumbnail = urljoin(page_url or self.base_url, img_src)
                break

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

    def _normalize_search_text(self, value: str) -> str:
        value = re.sub(r'[^a-z0-9]+', ' ', str(value or '').lower())
        return re.sub(r'\s+', ' ', value).strip()

    def _filter_cities(self, soup, query: str) -> list:
        results = []
        seen_links = set()
        query_text = self._normalize_search_text(query)
        query_terms = query_text.split()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if not href.endswith('.htm'):
                continue
            full_url = urljoin(self.base_url, href)
            if not self._is_city_url(full_url):
                continue
            title = a.text.strip()
            search_text = self._normalize_search_text(f'{title} {full_url}')
            if title and (
                query_text in search_text
                or all(term in search_text for term in query_terms)
            ) and full_url not in seen_links:
                seen_links.add(full_url)
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
