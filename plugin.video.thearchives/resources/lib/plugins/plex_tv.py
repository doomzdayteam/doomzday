import gzip
import json
import re
import sys
import time
from html import unescape
from urllib.parse import quote, urlencode, unquote
from uuid import uuid4

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


FANART = Addon().getAddonInfo('fanart')

BASE_URL = 'https://www.plex.tv/watch-free-tv'
PLEX_TV_API = 'https://plex.tv'
APP_URL = 'https://app.plex.tv'
EPG_BASE = 'https://epg.provider.plex.tv'
PROVIDER_VERSION = '5.1'
CATALOG_URL = 'https://i.mjh.nz/Plex/.channels.json.gz'
DEFAULT_REGION = 'us'

ROOT_URL = BASE_URL
CHANNELS_URL = f'{BASE_URL}/channels'
SEARCH_URL = f'{BASE_URL}/search'
HUBS_URL = f'{BASE_URL}/hubs'
HUB_URL = f'{BASE_URL}/hub'
REGION_URL = f'{BASE_URL}/region'

PINNED_HUBS = [
    ('whatsOnNow', "What's On Now"),
]

BLOCKED_CHANNEL_ID_SUFFIXES = (
    '-63eecb32ac23d1ee072087cb',
)
BLOCKED_CHANNEL_TITLES = {
    '123go!',
}


def _load_json(response):
    try:
        return json.loads(response or '{}')
    except (json.JSONDecodeError, TypeError):
        return {}


def _load_catalog(raw):
    if isinstance(raw, str):
        return json.loads(raw)
    try:
        text = gzip.decompress(raw).decode('utf-8')
    except (OSError, EOFError):
        text = raw.decode('utf-8')
    return json.loads(text)


def _strip_html(text):
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', unescape(str(text))).strip()[:800]


def _clean_title(title):
    return re.sub(r'\[/?COLOR[^\]]*\]', '', str(title or 'Plex Live TV')).strip()


def _with_kodi_headers(url, user_agent, referer=f'{APP_URL}/'):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer, safe="")}'
    )


def _kodi_header_query(user_agent, referer=f'{APP_URL}/'):
    return urlencode({
        'User-Agent': user_agent,
        'Referer': referer,
    })


def _configure_hls_inputstream(liz, user_agent):
    liz.setProperty('inputstream', 'inputstream.ffmpegdirect')
    liz.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
    liz.setProperty('inputstream.ffmpegdirect.stream_mode', 'timeshift')
    liz.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')
    liz.setProperty('inputstream.ffmpegdirect.stream_headers', _kodi_header_query(user_agent))


def _is_blocked_channel(channel_id='', title='', part_key=''):
    title = str(title or '').strip().lower()
    channel_id = str(channel_id or '').strip().lower()
    part_key = str(part_key or '').strip().lower()
    return (
        title in BLOCKED_CHANNEL_TITLES
        or any(channel_id.endswith(suffix) for suffix in BLOCKED_CHANNEL_ID_SUFFIXES)
        or any(suffix in part_key for suffix in BLOCKED_CHANNEL_ID_SUFFIXES)
    )


def _media_part_key(item):
    media = item.get('Media', []) if isinstance(item, dict) else []
    if not isinstance(media, list):
        return ''
    for media_item in media:
        if not isinstance(media_item, dict):
            continue
        if media_item.get('drm') is True:
            continue
        protocol = str(media_item.get('protocol') or '').lower()
        parts = media_item.get('Part', [])
        if not isinstance(parts, list):
            continue
        for part in parts:
            key = part.get('key', '') if isinstance(part, dict) else ''
            if key and (key.endswith('.m3u8') or protocol == 'hls'):
                return key
    return ''


def _best_image(item):
    if not isinstance(item, dict):
        return ''
    for key in ('thumb', 'art', 'coverPoster', 'grandparentThumb', 'parentThumb'):
        url = item.get(key, '')
        if isinstance(url, str) and url and not url.lower().split('?', 1)[0].endswith('.svg'):
            return url.replace('http://', 'https://', 1)
    images = item.get('Image', [])
    if isinstance(images, list):
        preferred = ('clearLogo', 'coverArt', 'coverPoster', 'background')
        for image_type in preferred:
            for image in images:
                if not isinstance(image, dict):
                    continue
                url = image.get('url', '')
                if image.get('type') == image_type and url:
                    return url.replace('http://', 'https://', 1)
    return ''


def _channels_from_catalog(catalog, region_code=DEFAULT_REGION):
    channels = []
    wanted_region = str(region_code or '').lower()
    source_channels = catalog.get('channels', {}) if isinstance(catalog, dict) else {}
    for channel_id, channel in source_channels.items():
        if not isinstance(channel, dict):
            continue
        regions = [str(region).lower() for region in channel.get('regions', [])]
        if wanted_region and wanted_region not in regions:
            continue
        title = str(channel.get('name') or '').strip()
        channel_id = str(channel_id or '').strip()
        if not title or not channel_id:
            continue
        if _is_blocked_channel(channel_id, title):
            continue
        logo = channel.get('logo', '') or ''
        channels.append({
            'id': channel_id,
            'title': title,
            'number': '',
            'summary': _strip_html(channel.get('description', '')),
            'thumb': logo,
            'art': logo,
            'part_key': '',
            'genre_keys': [],
            'programs': channel.get('programs', []) or [],
        })
    return sorted(channels, key=_channel_sort_key)


def _regions(catalog):
    regions = catalog.get('regions', {}) if isinstance(catalog, dict) else {}
    items = []
    for code, region in regions.items():
        if not isinstance(region, dict):
            continue
        name = region.get('name') or code.upper()
        logo = region.get('logo', '') or ''
        items.append((str(code).lower(), str(name), logo))
    return sorted(items, key=lambda item: item[1].lower())


def _region_headers(catalog, region_code):
    regions = catalog.get('regions', {}) if isinstance(catalog, dict) else {}
    region = regions.get(str(region_code or '').lower(), {})
    headers = region.get('headers', {}) if isinstance(region, dict) else {}
    return headers if isinstance(headers, dict) else {}


def _merge_channel_part_keys(channels, lineup_payload):
    lineup_channels = _channels_from_lineup(lineup_payload)
    part_keys = {
        channel.get('id'): channel.get('part_key', '')
        for channel in lineup_channels
        if channel.get('id') and channel.get('part_key')
    }
    for channel in channels:
        channel['part_key'] = part_keys.get(channel.get('id'), channel.get('part_key', ''))
    return channels


def _channels_from_lineup(payload):
    channels = []
    container = payload.get('MediaContainer', {}) if isinstance(payload, dict) else {}
    for channel in container.get('Channel', []) or []:
        if not isinstance(channel, dict) or channel.get('hidden') is True:
            continue
        part_key = _media_part_key(channel)
        title = str(channel.get('title') or '').strip()
        channel_id = str(channel.get('id') or '').strip()
        if not title or not channel_id or not part_key:
            continue
        if _is_blocked_channel(channel_id, title, part_key):
            continue
        channels.append({
            'id': channel_id,
            'title': title,
            'number': str(channel.get('vcn') or channel.get('channelNumber') or '').strip(),
            'summary': _strip_html(channel.get('summary', '')),
            'thumb': _best_image(channel),
            'art': channel.get('art', '') or _best_image(channel),
            'part_key': part_key,
            'genre_keys': channel.get('genreRatingKeys', []) or [],
        })
    return sorted(channels, key=_channel_sort_key)


def _channel_sort_key(channel):
    number = channel.get('number', '')
    try:
        numeric = int(number)
    except (TypeError, ValueError):
        numeric = 999999
    return numeric, channel.get('title', '').lower()


def _stream_url(part_key, token, client_id, user_agent):
    if not part_key:
        return ''
    path = part_key if part_key.startswith('/') else f'/{part_key}'
    params = {
        'X-Plex-Token': token,
        'X-Plex-Client-Identifier': client_id,
        'X-Plex-Product': 'Plex Web',
        'X-Plex-Platform': 'Chrome',
        'X-Plex-Version': '4.159.0',
        'X-Plex-Device-Name': 'Plex Web',
        'X-Plex-Advertising-DoNotTrack': '0',
    }
    return _with_kodi_headers(f'{EPG_BASE}{path}?{urlencode(params)}', user_agent)


def _channel_item(channel, token, client_id, user_agent):
    number = channel.get('number', '')
    prefix = f'[COLOR grey]{number}[/COLOR] ' if number else ''
    thumb = channel.get('thumb', '')
    title = channel.get('title', 'Plex Live TV')
    now = _current_program(channel)
    if now:
        title = f'{title} - {now}'
    return {
        'type': 'item',
        'title': f'[COLOR cyan]Play[/COLOR] {prefix}{title}',
        'link': _stream_url(channel.get('part_key', ''), token, client_id, user_agent),
        'thumbnail': thumb,
        'icon': thumb,
        'poster': channel.get('art', thumb),
        'landscape': channel.get('art', thumb),
        'fanart': channel.get('art', thumb) or FANART,
        'summary': channel.get('summary', ''),
        'is_playable': 'true',
    }


def _items_from_hub(payload, token, client_id, user_agent):
    items = []
    container = payload.get('MediaContainer', {}) if isinstance(payload, dict) else {}
    for metadata in container.get('Metadata', []) or []:
        if not isinstance(metadata, dict):
            continue
        part_key = _media_part_key(metadata)
        title = str(metadata.get('title') or metadata.get('grandparentTitle') or '').strip()
        if not part_key or not title:
            continue
        if _is_blocked_channel(title=title, part_key=part_key):
            continue
        thumb = _best_image(metadata)
        summary = _strip_html(metadata.get('summary') or metadata.get('tagline') or '')
        items.append({
            'type': 'item',
            'title': f'[COLOR cyan]Play[/COLOR] {title}',
            'link': _stream_url(part_key, token, client_id, user_agent),
            'thumbnail': thumb,
            'icon': thumb,
            'poster': thumb,
            'landscape': metadata.get('art', '') or thumb,
            'fanart': metadata.get('art', '') or thumb or FANART,
            'summary': summary,
            'is_playable': 'true',
        })
    return items


def _filter_channels(channels, query):
    terms = [term for term in re.split(r'\s+', str(query or '').lower()) if term]
    if not terms:
        return []
    matches = []
    for channel in channels:
        haystack = ' '.join([
            channel.get('number', ''),
            channel.get('title', ''),
            channel.get('summary', ''),
            ' '.join(channel.get('genre_keys', [])),
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


class PlexTV(Plugin):
    name = 'plex_tv'
    priority = 1047

    def __init__(self):
        self.session = DI.session
        self.base_url = BASE_URL
        self.client_id = str(uuid4())
        self.token = ''
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        )
        if self.session:
            self.session.headers = self._plex_headers()
        self._catalog = None

    def _plex_headers(self):
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
            'X-Plex-Product': 'Plex Web',
            'X-Plex-Client-Identifier': self.client_id,
            'X-Plex-Platform': 'Chrome',
            'X-Plex-Version': '4.159.0',
            'X-Plex-Device': 'Chrome',
            'X-Plex-Device-Name': 'Plex Web',
        }
        if self.token:
            headers['X-Plex-Token'] = self.token
        return headers

    def _ensure_token(self):
        if self.token:
            return self.token
        resp = self.session.post(f'{PLEX_TV_API}/api/v2/users/anonymous', headers=self._plex_headers())
        data = resp.json()
        self.token = data.get('authToken', '')
        return self.token

    def _provider_headers(self, extra_headers=None):
        self._ensure_token()
        headers = self._plex_headers()
        headers['X-Plex-Provider-Version'] = PROVIDER_VERSION
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _get_json(self, url, extra_headers=None):
        resp = self.session.get(url, headers=self._provider_headers(extra_headers))
        try:
            return resp.json()
        except ValueError:
            return _load_json(resp.text)

    def _fetch_catalog(self):
        if self._catalog:
            return self._catalog
        resp = self.session.get(CATALOG_URL, headers=self._plex_headers())
        self._catalog = _load_catalog(resp.content)
        return self._catalog

    def _channels_payload(self, region_code=DEFAULT_REGION, catalog=None):
        catalog = catalog or self._fetch_catalog()
        return self._get_json(
            f'{EPG_BASE}/lineups/plex/channels',
            extra_headers=_region_headers(catalog, region_code),
        )

    def _catalog_channels(self, region_code=DEFAULT_REGION):
        catalog = self._fetch_catalog()
        channels = _channels_from_catalog(catalog, region_code)
        _merge_channel_part_keys(channels, self._channels_payload(region_code, catalog))
        return [channel for channel in channels if channel.get('part_key')]

    def _hub_payload(self, hub_key):
        return self._get_json(f'{EPG_BASE}/hubs/sections/home/{hub_key}')

    def _region_path(self, region_code, tail=''):
        base = f'{REGION_URL}/{quote(region_code, safe="")}'
        return f'{base}/{tail.lstrip("/")}' if tail else base

    def _parse_region_route(self, url):
        if not url.startswith(REGION_URL + '/'):
            return '', ''
        route = url.replace(REGION_URL + '/', '', 1)
        region_code, _, tail = route.partition('/')
        return unquote(region_code).lower(), tail

    def get_list(self, url):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        if url == ROOT_URL:
            return json.dumps({'kind': 'root', 'catalog': self._fetch_catalog()})

        region_code, tail = self._parse_region_route(url)
        if region_code:
            if not tail:
                return json.dumps({'kind': 'region', 'region': region_code})
            if tail == 'search':
                query = self.from_keyboard(header=f'Search Plex Live TV ({region_code.upper()})')
                if not query:
                    sys.exit()
                return json.dumps({
                    'kind': 'search',
                    'region': region_code,
                    'query': query,
                    'channels': self._catalog_channels(region_code),
                })
            if tail == 'channels':
                return json.dumps({
                    'kind': 'channels',
                    'region': region_code,
                    'channels': self._catalog_channels(region_code),
                })
            return None

        if url == SEARCH_URL:
            query = self.from_keyboard()
            if not query:
                sys.exit()
            return json.dumps({
                'kind': 'search',
                'query': query,
                'channels': self._catalog_channels(),
            })

        if url == CHANNELS_URL:
            return json.dumps({
                'kind': 'channels',
                'channels': self._catalog_channels(),
            })

        if url == HUBS_URL:
            return json.dumps({'kind': 'hubs', 'hubs': PINNED_HUBS})

        if url.startswith(HUB_URL + '/'):
            hub_key = unquote(url.replace(HUB_URL + '/', '', 1).split('/')[0])
            return json.dumps({
                'kind': 'hub',
                'hub': hub_key,
                'payload': self._hub_payload(hub_key),
            })

        return None

    def parse_list(self, url, response):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        data = _load_json(response)
        kind = data.get('kind', '')

        if kind == 'root':
            items = []
            for code, name, logo in _regions(data.get('catalog', {})):
                items.append({
                    'type': 'dir',
                    'title': f'[COLOR cyan]{name}[/COLOR]',
                    'link': self._region_path(code),
                    'thumbnail': logo or 'resources/media/live_tv.png',
                    'summary': f'Browse Plex live TV channels for {name}.',
                })
            items.append({
                'type': 'dir',
                'title': '[COLOR orange]Plex Live TV Hubs[/COLOR]',
                'link': HUBS_URL,
                'thumbnail': 'resources/media/live_tv.png',
                'summary': 'Browse Plex rows like What is On Now.',
            })
            return items

        if kind == 'region':
            region_code = data.get('region', DEFAULT_REGION)
            label = str(region_code).upper()
            return [
                {
                    'type': 'dir',
                    'title': f'[COLOR deepskyblue]Search Plex Live TV ({label})[/COLOR]',
                    'link': self._region_path(region_code, 'search'),
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': f'Search Plex live TV channels for {label}.',
                },
                {
                    'type': 'dir',
                    'title': f'[COLOR orange]All Channels ({label})[/COLOR]',
                    'link': self._region_path(region_code, 'channels'),
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': f'Browse the Plex live TV channel lineup for {label}.',
                },
            ]

        if kind == 'hubs':
            return [
                {
                    'type': 'dir',
                    'title': title,
                    'link': f'{HUB_URL}/{quote(key, safe="")}',
                    'thumbnail': 'resources/media/live_tv.png',
                }
                for key, title in data.get('hubs', [])
            ]

        if kind == 'hub':
            items = _items_from_hub(data.get('payload', {}), self._ensure_token(), self.client_id, self.user_agent)
            return items or [{
                'type': 'dir',
                'title': '[COLOR grey]No playable hub items found[/COLOR]',
                'link': ROOT_URL,
            }]

        channels = data.get('channels', [])
        if kind == 'search':
            channels = _filter_channels(channels, data.get('query', ''))

        items = [
            _channel_item(channel, self._ensure_token(), self.client_id, self.user_agent)
            for channel in channels
        ]
        return items or [{
            'type': 'dir',
            'title': '[COLOR grey]No Plex channels found[/COLOR]',
            'link': ROOT_URL,
        }]

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

        if not isinstance(link, str) or EPG_BASE not in link:
            return None

        title = _clean_title(data.get('title', 'Plex Live TV'))
        thumbnail = data.get('thumbnail', '')
        liz = xbmcgui.ListItem(title, path=link)
        liz.setProperty('IsPlayable', 'true')
        if thumbnail:
            liz.setArt({
                'thumb': thumbnail,
                'icon': thumbnail,
                'poster': thumbnail,
                'fanart': data.get('fanart', '') or FANART,
            })
        set_video_info(liz, {'title': title, 'plot': data.get('summary', '')})
        liz.setMimeType('application/vnd.apple.mpegurl')
        _configure_hls_inputstream(liz, self.user_agent)
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(link, liz)
        return True

    def from_keyboard(self, default_text='', header='Search Plex Live TV'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
