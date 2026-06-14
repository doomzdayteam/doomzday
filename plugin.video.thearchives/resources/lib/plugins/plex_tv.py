import json
import re
import sys
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

ROOT_URL = BASE_URL
CHANNELS_URL = f'{BASE_URL}/channels'
SEARCH_URL = f'{BASE_URL}/search'
HUBS_URL = f'{BASE_URL}/hubs'
HUB_URL = f'{BASE_URL}/hub'

PINNED_HUBS = [
    ('whatsOnNow', "What's On Now"),
    ('tuneInNowPopularMovies', 'Tune In Now: Popular Movies'),
]


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
    return re.sub(r'\[/?COLOR[^\]]*\]', '', str(title or 'Plex Live TV')).strip()


def _with_kodi_headers(url, user_agent, referer=f'{APP_URL}/'):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer, safe="")}'
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
    return {
        'type': 'item',
        'title': f'[COLOR cyan]Play[/COLOR] {prefix}{channel.get("title", "Plex Live TV")}',
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

    def _provider_headers(self):
        self._ensure_token()
        headers = self._plex_headers()
        headers['X-Plex-Provider-Version'] = PROVIDER_VERSION
        return headers

    def _get_json(self, url):
        resp = self.session.get(url, headers=self._provider_headers())
        try:
            return resp.json()
        except ValueError:
            return _load_json(resp.text)

    def _channels_payload(self):
        return self._get_json(f'{EPG_BASE}/lineups/plex/channels')

    def _hub_payload(self, hub_key):
        return self._get_json(f'{EPG_BASE}/hubs/sections/home/{hub_key}')

    def get_list(self, url):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        if url == ROOT_URL:
            return json.dumps({'kind': 'root'})

        if url == SEARCH_URL:
            query = self.from_keyboard()
            if not query:
                sys.exit()
            return json.dumps({
                'kind': 'search',
                'query': query,
                'channels': _channels_from_lineup(self._channels_payload()),
            })

        if url == CHANNELS_URL:
            return json.dumps({
                'kind': 'channels',
                'channels': _channels_from_lineup(self._channels_payload()),
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
            return [
                {
                    'type': 'dir',
                    'title': '[COLOR deepskyblue]Search Plex Live TV[/COLOR]',
                    'link': SEARCH_URL,
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': 'Search free Plex live TV channels.',
                },
                {
                    'type': 'dir',
                    'title': '[COLOR orange]All Channels[/COLOR]',
                    'link': CHANNELS_URL,
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': 'Browse the full Plex free live TV channel lineup.',
                },
                {
                    'type': 'dir',
                    'title': '[COLOR orange]Plex Live TV Hubs[/COLOR]',
                    'link': HUBS_URL,
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': 'Browse Plex rows like What is On Now and popular live movies.',
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
