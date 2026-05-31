import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote, unquote
from uuid import uuid4

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


FANART = Addon().getAddonInfo('fanart')

BASE_URL = 'https://play.xumo.com'
MARKETING_URL = 'https://www.xumo.com'
API_BASE = 'https://valencia-app-mds.xumo.com/v2'
CHANNEL_LIST_ID = '10006'
CHANNEL_LIST_GEO_ID = '2f08a9b3'
CHANNEL_LIST_URL = (
    f'{API_BASE}/proxy/channels/list/{CHANNEL_LIST_ID}.json'
    f'?sort=hybrid&geoId={CHANNEL_LIST_GEO_ID}'
)
BROADCAST_QS = (
    '?f=providers&f=cuePoints&f=connectorId&f=genres&f=title&f=episodeTitle'
    '&f=runtime&f=ratings&f=keywords&f=season&f=episode'
)


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
    return re.sub(r'\[/?COLOR[^\]]*\]', '', str(title or 'Xumo Play')).strip()


def _with_kodi_headers(url, user_agent, referer=BASE_URL):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer + "/", safe="")}'
    )


def _channel_id(item):
    guid = item.get('guid', {}) if isinstance(item, dict) else {}
    value = guid.get('value') if isinstance(guid, dict) else ''
    return str(value or item.get('id') or '').strip()


def _channel_group(item):
    genres = item.get('genre', []) if isinstance(item, dict) else []
    if isinstance(genres, list) and genres:
        value = genres[0].get('value', '') if isinstance(genres[0], dict) else ''
        if value:
            return str(value).strip()
    return 'Channels'


def _is_live(item):
    props = item.get('properties', {}) if isinstance(item, dict) else {}
    value = props.get('is_live') if isinstance(props, dict) else ''
    return str(value).lower() == 'true'


def _channel_sort_key(channel):
    try:
        number = int(channel.get('number'))
    except (TypeError, ValueError):
        number = 999999
    return number, str(channel.get('name', '')).lower()


def _logo_url(channel_id, size=168):
    return f'https://image.xumo.com/v1/channels/channel/{channel_id}/{size}x{size}.png'


def _channels_from_catalog(catalog):
    items = catalog.get('channel', {}).get('item', []) if isinstance(catalog, dict) else []
    channels = []
    for item in items:
        if not isinstance(item, dict) or not _is_live(item):
            continue
        channel_id = _channel_id(item)
        name = str(item.get('title') or '').strip()
        if not channel_id or not name:
            continue
        channels.append({
            'id': channel_id,
            'name': name,
            'number': item.get('number', ''),
            'description': _strip_html(item.get('description', '')),
            'group': _channel_group(item),
            'logo': _logo_url(channel_id),
            'slug': item.get('slug', ''),
        })
    return sorted(channels, key=_channel_sort_key)


def _groups_from_catalog(catalog):
    counts = {}
    for channel in _channels_from_catalog(catalog):
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
            str(channel.get('number', '')),
            channel.get('name', ''),
            channel.get('group', ''),
            channel.get('description', ''),
        ]).lower()
        if all(term in haystack for term in terms):
            matches.append(channel)
    return matches


def _replace_stream_placeholders(url, user_agent):
    if not isinstance(url, str) or not url:
        return ''
    device_id = str(uuid4())
    now = datetime.now(timezone.utc)
    replacements = {
        'PLATFORM': 'web',
        'IFA_TYPE': 'tifa',
        'IFA': device_id,
        'AMZN_APP_ID': '',
        'LAT': '',
        'LON': '',
        'OS': 'Windows',
        'OS_VERSION': '10',
        'IS_LAT': '0',
        'CCPA_Value': '1YNY',
        'IAB_content_category': '',
        'content_language': 'en',
        'content_rating': '',
        'device_make': 'Chrome',
        'device_model': 'Web',
        'publica_site_id': '',
        'APP_VERSION': '2.23.3',
        'app_bundle': 'web.xumo.com',
        'app_store_url': BASE_URL,
        'APP_NAME': 'XumoPlay',
        'UA': user_agent,
        'CACHEBUSTER': str(int(now.timestamp())),
    }
    for key, value in replacements.items():
        url = url.replace(f'[{key}]', quote(str(value), safe=''))
    return re.sub(r'\[[A-Za-z0-9_]+\]', '', url)


def _build_stream_url(url, user_agent):
    url = _replace_stream_placeholders(url, user_agent)
    return _with_kodi_headers(url, user_agent) if url else ''


class XumoPlay(Plugin):
    name = 'xumo_play'
    priority = 1047

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

        self.live_url = f'{self.base_url}/live'
        self.live_cat_url = f'{self.live_url}/category'
        self.channel_url = f'{self.base_url}/channel'
        self.search_url = f'{self.base_url}/search'
        self._catalog = None

    def _api_get(self, url):
        resp = self.session.get(url, headers=self.headers)
        try:
            return resp.json()
        except ValueError:
            return _load_json(resp.text)

    def _fetch_catalog(self):
        if self._catalog:
            return self._catalog
        self._catalog = self._api_get(CHANNEL_LIST_URL)
        return self._catalog

    def get_list(self, url):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        if url == self.search_url:
            query = self.from_keyboard()
            if not query:
                sys.exit()
            return json.dumps({
                'kind': 'search',
                'query': query,
                'catalog': self._fetch_catalog(),
            })

        if url == self.base_url or url == self.live_url or url.startswith(self.live_cat_url + '/'):
            return json.dumps({
                'kind': 'catalog',
                'catalog': self._fetch_catalog(),
            })

        if url.startswith(self.channel_url + '/'):
            channel_id = unquote(url.replace(self.channel_url + '/', '').split('/')[0])
            return json.dumps({
                'kind': 'channel',
                'channelId': channel_id,
                'catalog': self._fetch_catalog(),
            })

        return None

    def parse_list(self, url, response):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        data = _load_json(response)
        catalog = data.get('catalog', data)
        itemlist = []

        if url == self.base_url:
            return [
                {
                    'type': 'dir',
                    'title': '[COLOR deepskyblue]Search Xumo Play[/COLOR]',
                    'link': self.search_url,
                    'thumbnail': 'resources/media/live_tv.png',
                },
                {
                    'type': 'dir',
                    'title': '[COLOR orange]-- Live TV --[/COLOR]',
                    'link': self.live_url,
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': 'Browse free live channels from Xumo Play.',
                },
            ]

        if url == self.live_url:
            for group, count in _groups_from_catalog(catalog):
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR orange]{group}[/COLOR] ({count})',
                    'link': f'{self.live_cat_url}/{quote(group, safe="")}',
                    'thumbnail': 'resources/media/live_tv.png',
                })
            return itemlist or self._empty('No live channels available', self.base_url)

        channels = _channels_from_catalog(catalog)
        if url == self.search_url:
            channels = _filter_channels(channels, data.get('query', ''))
        elif url.startswith(self.live_cat_url + '/'):
            group = unquote(url.replace(self.live_cat_url + '/', '').split('/')[0])
            channels = [channel for channel in channels if channel.get('group') == group]
        elif url.startswith(self.channel_url + '/'):
            channel_id = unquote(url.replace(self.channel_url + '/', '').split('/')[0])
            channels = [channel for channel in channels if channel.get('id') == channel_id]
        else:
            return None

        for channel in channels:
            self._add_channel_item(itemlist, channel)
        return itemlist or self._empty('No channels found', self.live_url)

    def _empty(self, message, link):
        return [{
            'type': 'dir',
            'title': f'[COLOR grey]{message}[/COLOR]',
            'link': link,
        }]

    def _add_channel_item(self, itemlist, channel):
        number = str(channel.get('number') or '').strip()
        name = channel.get('name', 'Xumo Play')
        label = f'{number} - {name}' if number else name
        itemlist.append({
            'type': 'item',
            'title': f'[COLOR red]>[/COLOR] {label}',
            'link': f"{self.channel_url}/{quote(channel.get('id', ''), safe='')}",
            'thumbnail': channel.get('logo', '') or 'resources/media/live_tv.png',
            'summary': channel.get('description', '') or channel.get('group', ''),
            'is_playable': 'true',
        })

    def _resolve_channel(self, channel_id):
        hour = datetime.now(timezone.utc).hour
        broadcast = self._api_get(f'{API_BASE}/channels/channel/{channel_id}/broadcast.json?hour={hour}')
        assets = broadcast.get('assets', []) if isinstance(broadcast, dict) else []
        asset_id = ''
        for asset in assets:
            if isinstance(asset, dict) and asset.get('id'):
                asset_id = str(asset.get('id'))
                break
        if not asset_id:
            return {}

        asset = self._api_get(f'{API_BASE}/assets/asset/{asset_id}.json{BROADCAST_QS}')
        providers = asset.get('providers', []) if isinstance(asset, dict) else []
        for provider in providers:
            for source in provider.get('sources', []):
                uri = source.get('uri', '') if isinstance(source, dict) else ''
                if uri and ('.m3u8' in uri or 'mpegURL' in source.get('produces', '')):
                    return {
                        'title': asset.get('title') or provider.get('title') or 'Xumo Play',
                        'summary': _strip_html(asset.get('description', '')),
                        'link': _build_stream_url(uri, self.user_agent),
                    }
        return {}

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

        if link.startswith(self.channel_url + '/'):
            channel_id = unquote(link.replace(self.channel_url + '/', '').split('/')[0])
            try:
                resolved = self._resolve_channel(channel_id)
                if not resolved.get('link'):
                    xbmcgui.Dialog().notification(
                        'Xumo Play', 'Stream not available',
                        xbmcgui.NOTIFICATION_WARNING, 3000,
                    )
                    return True
                link = resolved.get('link', '')
                data.setdefault('title', resolved.get('title', 'Xumo Play'))
                data.setdefault('summary', resolved.get('summary', ''))
            except Exception:
                xbmcgui.Dialog().notification(
                    'Xumo Play', 'Failed to resolve stream',
                    xbmcgui.NOTIFICATION_WARNING, 3000,
                )
                return True

        if '.m3u8' not in link and 'xumo' not in link.lower():
            return None

        title = _clean_title(data.get('title', 'Xumo Play'))
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

    def from_keyboard(self, default_text='', header='Search Xumo Play'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
