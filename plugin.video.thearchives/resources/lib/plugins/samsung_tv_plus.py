import gzip
import json
import re
import sys
import time
from html import unescape
from urllib.parse import quote, unquote

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


FANART = Addon().getAddonInfo('fanart')

BASE_URL = 'https://www.samsungtvplus.com'
CATALOG_URL = 'https://i.mjh.nz/SamsungTVPlus/.channels.json.gz'
PLAYBACK_URL = 'https://jmp2.uk/{slug}'
DEFAULT_SLUG = 'stvp-{id}'


def _load_catalog(raw):
    if isinstance(raw, str):
        return json.loads(raw)
    try:
        text = gzip.decompress(raw).decode('utf-8')
    except (OSError, EOFError):
        text = raw.decode('utf-8')
    return json.loads(text)


def _load_json(response):
    try:
        return json.loads(response or '{}')
    except (json.JSONDecodeError, TypeError):
        return {}


def _strip_html(text):
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', unescape(str(text))).strip()[:800]


def _clean_title(title):
    return re.sub(r'\[/?COLOR[^\]]*\]', '', str(title or 'Samsung TV Plus')).strip()


def _with_kodi_headers(url, user_agent, referer=BASE_URL):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer + "/", safe="")}'
    )


def _stream_url(channel_id, user_agent, slug_template=DEFAULT_SLUG):
    slug = slug_template.format(id=channel_id)
    return _with_kodi_headers(PLAYBACK_URL.format(slug=slug), user_agent)


def _regions(catalog):
    regions = catalog.get('regions', {}) if isinstance(catalog, dict) else {}
    items = []
    for code, region in regions.items():
        name = region.get('name') or code.upper()
        items.append((str(code).lower(), str(name)))
    return sorted(items, key=lambda item: item[1].lower())


def _channel_sort_key(channel):
    chno = channel.get('chno')
    try:
        number = int(chno)
    except (TypeError, ValueError):
        number = 999999
    return number, str(channel.get('name', '')).lower()


def _channels_for_region(catalog, region_code):
    regions = catalog.get('regions', {}) if isinstance(catalog, dict) else {}
    region = regions.get(str(region_code).lower(), {})
    channels = []
    for channel_id, channel in region.get('channels', {}).items():
        if not isinstance(channel, dict):
            continue
        if channel.get('license_url'):
            continue
        name = str(channel.get('name', '')).strip()
        if not channel_id or not name:
            continue
        item = dict(channel)
        item['id'] = str(channel_id)
        item['name'] = name
        item['group'] = str(channel.get('group') or 'Channels').strip() or 'Channels'
        item['description'] = _strip_html(channel.get('description', ''))
        channels.append(item)
    return sorted(channels, key=_channel_sort_key)


def _groups_for_region(catalog, region_code):
    counts = {}
    for channel in _channels_for_region(catalog, region_code):
        group = channel.get('group') or 'Channels'
        counts[group] = counts.get(group, 0) + 1
    return sorted(counts.items(), key=lambda item: item[0].lower())


def _filter_channels(channels, query):
    terms = [term for term in re.split(r'\s+', str(query or '').lower()) if term]
    if not terms:
        return []
    matches = []
    for channel in channels:
        haystack = ' '.join([
            str(channel.get('chno', '')),
            channel.get('name', ''),
            channel.get('group', ''),
            channel.get('description', ''),
        ]).lower()
        if all(term in haystack for term in terms):
            matches.append(channel)
    return matches


def _current_program(channel):
    now = int(time.time())
    programs = channel.get('programs', [])
    if not isinstance(programs, list):
        return ''
    current = ''
    for index, program in enumerate(programs):
        if not isinstance(program, list) or len(program) < 2:
            continue
        try:
            start = int(program[0])
        except (TypeError, ValueError):
            continue
        title = str(program[1] or '').strip()
        next_start = None
        if index + 1 < len(programs) and isinstance(programs[index + 1], list):
            try:
                next_start = int(programs[index + 1][0])
            except (TypeError, ValueError, IndexError):
                next_start = None
        if start <= now and (next_start is None or now < next_start):
            return title
        if not current:
            current = title
    return current


class SamsungTVPlus(Plugin):
    name = 'samsung_tv_plus'
    priority = 1049

    def __init__(self):
        self.session = DI.session
        self.base_url = BASE_URL
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        )
        self.headers = {
            'User-Agent': self.user_agent,
            'Referer': f'{BASE_URL}/',
            'Accept': 'application/json, text/plain, */*',
        }
        if self.session:
            self.session.headers = self.headers

        self.region_url = f'{self.base_url}/region'
        self.live_url = f'{self.base_url}/live'
        self.live_cat_url = f'{self.live_url}/category'
        self.search_url = f'{self.base_url}/search'
        self._catalog = None

    def _fetch_catalog(self):
        if self._catalog:
            return self._catalog
        resp = self.session.get(CATALOG_URL, headers=self.headers)
        self._catalog = _load_catalog(resp.content)
        return self._catalog

    def _region_path(self, region_code, tail=''):
        base = f'{self.region_url}/{quote(region_code, safe="")}'
        return f'{base}/{tail.lstrip("/")}' if tail else base

    def _parse_region_route(self, url):
        if not url.startswith(self.region_url + '/'):
            return '', ''
        route = url.replace(self.region_url + '/', '', 1)
        region_code, _, tail = route.partition('/')
        return unquote(region_code).lower(), tail

    def get_list(self, url):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        catalog = self._fetch_catalog()
        if url == self.search_url or url.endswith('/search'):
            query = self.from_keyboard()
            if not query:
                sys.exit()
            return json.dumps({'kind': 'search', 'query': query, 'catalog': catalog})

        return json.dumps({'kind': 'catalog', 'catalog': catalog})

    def parse_list(self, url, response):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        data = _load_json(response)
        catalog = data.get('catalog', data)
        slug_template = catalog.get('slug') or DEFAULT_SLUG
        itemlist = []

        if url == self.base_url:
            for code, name in _regions(catalog):
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR cyan]{name}[/COLOR]',
                    'link': self._region_path(code),
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': 'Samsung TV Plus live channels for this region.',
                })
            return itemlist

        region_code, tail = self._parse_region_route(url)
        if not region_code:
            return None

        if not tail:
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Samsung TV Plus[/COLOR]',
                'link': self._region_path(region_code, 'search'),
                'thumbnail': 'resources/media/live_tv.png',
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR cyan]> All Live Channels[/COLOR]',
                'link': self._region_path(region_code, 'live'),
                'thumbnail': 'resources/media/live_tv.png',
            })
            for group, count in _groups_for_region(catalog, region_code):
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR orange]{group}[/COLOR] ({count})',
                    'link': self._region_path(region_code, f'live/category/{quote(group, safe="")}'),
                    'thumbnail': 'resources/media/live_tv.png',
                })
            return itemlist

        channels = _channels_for_region(catalog, region_code)
        if tail == 'search':
            channels = _filter_channels(channels, data.get('query', ''))
        elif tail.startswith('live/category/'):
            group = unquote(tail.replace('live/category/', '', 1))
            channels = [channel for channel in channels if channel.get('group') == group]
        elif tail != 'live':
            return None

        for channel in channels:
            self._add_channel_item(itemlist, channel, slug_template)

        if not itemlist:
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR grey]No channels found[/COLOR]',
                'link': self._region_path(region_code),
            })
        return itemlist

    def _add_channel_item(self, itemlist, channel, slug_template):
        number = str(channel.get('chno') or '').strip()
        name = channel.get('name', 'Samsung TV Plus')
        now = _current_program(channel)
        label = f'{number} - {name}' if number else name
        if now:
            label = f'{label} - {now}'
        itemlist.append({
            'type': 'item',
            'title': f'[COLOR red]>[/COLOR] {label}',
            'link': _stream_url(channel.get('id', ''), self.user_agent, slug_template),
            'thumbnail': channel.get('logo', '') or 'resources/media/live_tv.png',
            'summary': channel.get('description', '') or channel.get('group', ''),
            'is_playable': 'true',
        })

    def play_video(self, item):
        data = {}
        link = item
        try:
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            data = json.loads(item)
            link = data.get('link', '')
        except (json.JSONDecodeError, TypeError, AttributeError):
            link = item.decode('utf-8') if isinstance(item, bytes) else item

        if not isinstance(link, str):
            return None

        if 'jmp2.uk/' not in link and '.m3u8' not in link and 'samsung' not in link.lower():
            return None

        title = _clean_title(data.get('title', 'Samsung TV Plus'))
        thumbnail = data.get('thumbnail', '')
        liz = xbmcgui.ListItem(title, path=link)
        liz.setProperty('IsPlayable', 'true')
        if thumbnail:
            liz.setArt({
                'thumb': thumbnail,
                'icon': thumbnail,
                'poster': thumbnail,
                'fanart': FANART,
            })
        set_video_info(liz, {'title': title, 'plot': data.get('summary', '')})
        liz.setMimeType('application/vnd.apple.mpegurl')
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass

        xbmc.Player().play(link, liz)
        return True

    def from_keyboard(self, default_text='', header='Search Samsung TV Plus'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
