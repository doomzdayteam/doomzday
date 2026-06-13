import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote, unquote, urlencode
from uuid import uuid4

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from ..vod_cache import VOD_CACHE, vod_cache_key
from resources.lib.infotagger.helpers import set_video_info


FANART = Addon().getAddonInfo('fanart')

BASE_URL = 'https://play.xumo.com'
MARKETING_URL = 'https://www.xumo.com'
API_BASE = 'https://valencia-app-mds.xumo.com/v2'
BEACON_URL = 'https://demo-beacons.xumo.com/content/v2/impression.json'
XUMO_API_HOST = 'valencia-app-mds.xumo.com'
XUMO_API_KEY = 'BJ8e86EyuW8GUsXJ'
APP_VERSION = '2.25.1'
WIDEVINE_LICENSE_BASE = 'https://widevine-dash.ezdrm.com/proxy?pX=5FE38E&CustomData='
CHANNEL_LIST_ID = '10006'
CHANNEL_LIST_GEO_ID = '2f08a9b3'
CHANNEL_LIST_URL = (
    f'{API_BASE}/proxy/channels/list/{CHANNEL_LIST_ID}.json'
    f'?sort=hybrid&geoId={CHANNEL_LIST_GEO_ID}'
)
MOVIES_PATH = '/free-movies'
SHOWS_PATH = '/tv-shows'
BROADCAST_QS = (
    '?f=providers&f=cuePoints&f=connectorId&f=genres&f=title&f=episodeTitle'
    '&f=runtime&f=ratings&f=keywords&f=season&f=episode'
    '&f=descriptions&f=originalReleaseYear'
)


def _load_json(response):
    try:
        return json.loads(response or '{}')
    except (json.JSONDecodeError, TypeError):
        return {}


def _extract_next_page(html):
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>\s*(\{.+?\})\s*</script>',
        html or '',
        re.DOTALL,
    )
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
    except (json.JSONDecodeError, TypeError):
        return {}
    return data.get('props', {}).get('pageProps', {}).get('page', {}) or {}


def _strip_html(text):
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', unescape(str(text))).strip()[:800]


def _overview_from_item(item):
    if not isinstance(item, dict):
        return ''
    summary = _strip_html(item.get('description', ''))
    if summary:
        return summary
    descriptions = item.get('descriptions', {})
    if isinstance(descriptions, dict):
        for key in ('large', 'medium', 'small', 'tiny'):
            summary = _strip_html(descriptions.get(key, ''))
            if summary:
                return summary
    return ''


def _clean_title(title):
    return re.sub(r'\[/?COLOR[^\]]*\]', '', str(title or 'Xumo Play')).strip()


def _with_kodi_headers(url, user_agent, referer=BASE_URL):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer + "/", safe="")}'
    )


def _kodi_header_query(user_agent, referer=f'{BASE_URL}/'):
    return (
        f'User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer, safe="")}'
        f'&Origin={quote(BASE_URL, safe="")}'
    )


def _widevine_license_key(license_url, user_agent):
    headers = f'Content-Type=application/octet-stream&{_kodi_header_query(user_agent)}'
    return f'{license_url}|{headers}|R{{SSM}}|'


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


def _duration_str(seconds):
    if not seconds:
        return ''
    try:
        total = int(seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'
    except (TypeError, ValueError):
        return ''


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


def _search_terms(query):
    return [term for term in re.split(r'\s+', str(query or '').lower()) if term]


def _card_image(card):
    image = card.get('image', '') if isinstance(card, dict) else ''
    image_ext = card.get('imageExt', '') if isinstance(card, dict) else ''
    card_id = str(card.get('id') or '') if isinstance(card, dict) else ''
    if image.startswith('https://image.xumo.com/v1/assets/asset/') and card_id:
        ext = image_ext.lstrip('.') or 'webp'
        return f'https://image.xumo.com/v1/assets/asset/{quote(card_id, safe="")}/600x900.{ext}'
    if image and image_ext and not image.endswith(image_ext):
        return f'{image}{image_ext}'
    return image


def _card_route(card):
    route_type = card.get('type') or 'free-movies'
    slug = card.get('slug') or re.sub(r'[^a-z0-9]+', '-', str(card.get('title', '')).lower()).strip('-')
    card_id = card.get('id', '')
    return f'{BASE_URL}/{route_type}/{quote(slug, safe="")}/{quote(card_id, safe="")}'


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
        self.vod_search_url = f'{self.base_url}/vod/search'
        self.movies_url = f'{self.base_url}{MOVIES_PATH}'
        self.shows_url = f'{self.base_url}{SHOWS_PATH}'
        self.all_movies_url = f'{self.base_url}/vod/movies'
        self.all_shows_url = f'{self.base_url}/vod/shows'
        self.vod_cat_url = f'{self.base_url}/vod/category'
        self.asset_url = f'{self.base_url}/asset'
        self._catalog = None
        self._device_id = None
        self._drm_token = None
        self._session_id = None
        self._page_view_id = None
        self._xumo_session_started = False
        self._asset_metadata = {}

    def _api_get(self, url):
        resp = self.session.get(url, headers=self.headers)
        try:
            return resp.json()
        except ValueError:
            return _load_json(resp.text)

    def _api_post(self, url, body=None, headers=None):
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)
        resp = self.session.post(url, headers=request_headers, json=body or {})
        try:
            return resp.json()
        except ValueError:
            return _load_json(resp.text)

    def _xumo_device_id(self):
        if self._device_id:
            return self._device_id
        data = self._api_post(
            f'{API_BASE}/devices/device/id.json',
            headers={'Authorization': f'XumoValenciaId id={XUMO_API_KEY}'},
        )
        self._device_id = data.get('id', '')
        return self._device_id

    def _session_ids(self):
        if not self._session_id:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            self._session_id = f'{now_ms}{uuid4().hex[:10]}'
            self._page_view_id = f'{self._session_id}{uuid4().hex[:10]}'
        return self._session_id, self._page_view_id

    def _send_beacon(self, event_type, device_id, **payload):
        session_id, page_view_id = self._session_ids()
        data = {
            'eventType': event_type,
            'clientVersion': APP_VERSION,
            'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
            'deviceId': device_id,
            'sessionId': session_id,
            'pageViewId': page_view_id,
        }
        for key, value in payload.items():
            if value is not None:
                data[key] = value
        self.session.get(f'{BEACON_URL}?{urlencode(data)}', headers=self.headers)

    def _start_xumo_session(self, asset_id=''):
        if self._xumo_session_started:
            return
        device_id = self._xumo_device_id()
        if not device_id:
            return
        try:
            self._send_beacon('appStart', 'undefined')
            self._send_beacon(
                'appReport',
                device_id,
                viewedItems='mobile=false',
                assetId=asset_id or 'undefined',
            )
        except Exception:
            pass
        self._xumo_session_started = True

    def _xumo_drm_token(self, asset_id=''):
        if self._drm_token:
            return self._drm_token
        device_id = self._xumo_device_id()
        if not device_id:
            return ''
        self._start_xumo_session(asset_id)
        url = f'{API_BASE}/security/drm/token.json?deviceId={quote(device_id, safe="")}'
        for delay_ms in (0, 1000, 1500, 2500):
            if delay_ms:
                self._sleep_ms(delay_ms)
            try:
                data = self._api_get(url)
            except Exception:
                data = {}
            self._drm_token = data.get('token', '')
            if self._drm_token:
                break
        return self._drm_token

    def _widevine_license_url(self, provider_id, asset_id):
        device_id = self._xumo_device_id()
        token = self._xumo_drm_token(asset_id)
        if not device_id or not token:
            return ''
        custom_data = {
            'host': XUMO_API_HOST,
            'deviceId': device_id,
            'clientVersion': APP_VERSION,
            'providerId': provider_id,
            'assetId': asset_id,
            'token': token,
        }
        return f'{WIDEVINE_LICENSE_BASE}{quote(json.dumps(custom_data, separators=(",", ":")), safe="")}'

    def _sleep_ms(self, milliseconds):
        try:
            xbmc.sleep(milliseconds)
        except AttributeError:
            import time
            time.sleep(milliseconds / 1000.0)

    def _fetch_catalog(self):
        if self._catalog:
            return self._catalog
        self._catalog = self._api_get(CHANNEL_LIST_URL)
        return self._catalog

    def _fetch_page(self, path_or_url):
        url = path_or_url if path_or_url.startswith('http') else f'{self.base_url}{path_or_url}'
        def fetch():
            resp = self.session.get(url, headers=self.headers)
            return resp.text

        response = VOD_CACHE.get_or_set_response(
            self.name,
            vod_cache_key('page', url),
            'catalog',
            fetch,
        )
        return _extract_next_page(response or '')

    def _fetch_asset_metadata(self, asset_id):
        asset_id = str(asset_id or '').strip()
        if not asset_id:
            return {}
        if asset_id not in self._asset_metadata:
            try:
                url = f'{API_BASE}/assets/asset/{quote(asset_id, safe="")}.json{BROADCAST_QS}'
                response = VOD_CACHE.get_or_set_response(
                    self.name,
                    vod_cache_key('asset', asset_id),
                    'catalog',
                    lambda: self.session.get(url, headers=self.headers).text,
                )
                self._asset_metadata[asset_id] = _load_json(response or '{}')
            except Exception:
                self._asset_metadata[asset_id] = {}
        return self._asset_metadata[asset_id]

    def _vod_menu_cache_kind(self, url):
        if url in (self.search_url, self.vod_search_url):
            return 'search'
        if url in (self.movies_url, self.shows_url, self.all_movies_url, self.all_shows_url):
            return 'catalog'
        if url.startswith(self.vod_cat_url + '/') or url.startswith(self.shows_url + '/'):
            return 'catalog'
        return ''

    def _asset_overview(self, asset_id):
        return _overview_from_item(self._fetch_asset_metadata(asset_id))

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
                'movies': self._fetch_page(MOVIES_PATH),
                'shows': self._fetch_page(SHOWS_PATH),
            })

        if url == self.vod_search_url:
            query = self.from_keyboard(header='Search Xumo Play VOD')
            if not query:
                sys.exit()
            return json.dumps({
                'kind': 'vod_search',
                'query': query,
                'movies': self._fetch_page(MOVIES_PATH),
                'shows': self._fetch_page(SHOWS_PATH),
            })

        if url in (self.movies_url, self.all_movies_url):
            return json.dumps({
                'kind': 'vod_page' if url == self.movies_url else 'vod_all',
                'route': 'free-movies',
                'page': self._fetch_page(MOVIES_PATH),
            })

        if url in (self.shows_url, self.all_shows_url):
            return json.dumps({
                'kind': 'vod_page' if url == self.shows_url else 'vod_all',
                'route': 'tv-shows',
                'page': self._fetch_page(SHOWS_PATH),
            })

        if url.startswith(self.vod_cat_url + '/'):
            tail = url.replace(self.vod_cat_url + '/', '').split('/')
            route = unquote(tail[0]) if tail else 'free-movies'
            cat_id = unquote(tail[1]) if len(tail) > 1 else ''
            page_path = SHOWS_PATH if route == 'tv-shows' else MOVIES_PATH
            return json.dumps({
                'kind': 'vod_category',
                'route': route,
                'categoryId': cat_id,
                'page': self._fetch_page(page_path),
            })

        if url.startswith(self.shows_url + '/'):
            return json.dumps({
                'kind': 'show_detail',
                'page': self._fetch_page(url),
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

        cache_kind = self._vod_menu_cache_kind(url)
        if cache_kind:
            return VOD_CACHE.get_or_set_menu(
                self.name,
                vod_cache_key('menu', url, response),
                cache_kind,
                lambda: self._parse_list_uncached(url, response),
            )
        return self._parse_list_uncached(url, response)

    def _parse_list_uncached(self, url, response):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        data = _load_json(response)
        catalog = data.get('catalog', data)
        itemlist = []

        if url == self.base_url:
            return [
                {
                    'type': 'item',
                    'title': '[COLOR khaki]Requires Widevine for VOD[/COLOR]',
                    'link': (
                        'message/Xumo Play on demand movies and episodes may use Widevine DRM. '
                        'Use the InputStream Helper link below to install or configure Widevine.'
                    ),
                    'summary': 'Some Xumo Play VOD streams require Widevine DRM support.',
                },
                {
                    'type': 'item',
                    'title': '[COLOR lawngreen]Click to Install Widevine / InputStream Helper[/COLOR]',
                    'link': 'inputstream_helper',
                    'summary': 'Install or configure InputStream Adaptive and Widevine for Xumo VOD playback.',
                },
                {
                    'type': 'dir',
                    'title': '[COLOR deepskyblue]Search Xumo Play[/COLOR]',
                    'link': self.search_url,
                    'thumbnail': 'resources/media/live_tv.png',
                },
                {
                    'type': 'dir',
                    'title': '[COLOR orange]-- Movies --[/COLOR]',
                    'link': self.movies_url,
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': 'Browse free on demand movies from Xumo Play.',
                },
                {
                    'type': 'dir',
                    'title': '[COLOR orange]-- TV Shows --[/COLOR]',
                    'link': self.shows_url,
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': 'Browse free on demand TV shows from Xumo Play.',
                },
                {
                    'type': 'dir',
                    'title': '[COLOR orange]-- Live TV --[/COLOR]',
                    'link': self.live_url,
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': 'Browse free live channels from Xumo Play.',
                },
            ]

        if url in (self.movies_url, self.shows_url):
            route = data.get('route', 'free-movies')
            page = data.get('page', {})
            all_url = self.all_shows_url if route == 'tv-shows' else self.all_movies_url
            all_label = 'All On Demand TV Shows' if route == 'tv-shows' else 'All On Demand Movies'
            itemlist.append({
                'type': 'dir',
                'title': f'[COLOR deepskyblue]>[/COLOR] {all_label}',
                'link': all_url,
                'thumbnail': 'resources/media/live_tv.png',
            })
            self._add_vod_category_items(itemlist, page, route)
            return itemlist or self._empty('No on demand categories available', self.base_url)

        if url in (self.all_movies_url, self.all_shows_url):
            route = data.get('route', 'free-movies')
            for card in self._iter_cards(data.get('page', {}), route=route):
                self._add_vod_card_item(itemlist, card)
            return itemlist or self._empty('No on demand titles available', self.base_url)

        if url.startswith(self.vod_cat_url + '/'):
            route = data.get('route', 'free-movies')
            for card in self._iter_cards(
                    data.get('page', {}),
                    route=route,
                    category_id=data.get('categoryId', '')):
                self._add_vod_card_item(itemlist, card)
            return itemlist or self._empty('No titles found', self.base_url)

        if url.startswith(self.shows_url + '/'):
            self._add_show_detail_items(itemlist, data.get('page', {}))
            return itemlist or self._empty('No episodes found', self.shows_url)

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
        if url in (self.search_url, self.vod_search_url):
            query = data.get('query', '')
            for card in self._iter_cards(data.get('movies', {}), route='free-movies', query=query):
                self._add_vod_card_item(itemlist, card)
            for card in self._iter_cards(data.get('shows', {}), route='tv-shows', query=query):
                self._add_vod_card_item(itemlist, card)
            if url == self.search_url:
                for channel in _filter_channels(channels, query):
                    self._add_channel_item(itemlist, channel)
            return itemlist or self._empty('No results found', self.base_url)
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

    def _rails_from_page(self, page):
        rails = page.get('rails', []) if isinstance(page, dict) else []
        return rails if isinstance(rails, list) else []

    def _iter_cards(self, page, route=None, category_id=None, query=None):
        seen = set()
        terms = _search_terms(query)
        for rail in self._rails_from_page(page):
            if not isinstance(rail, dict):
                continue
            category = rail.get('category', {}) if isinstance(rail.get('category', {}), dict) else {}
            cat_id = str(category.get('deepLink') or category.get('id') or '')
            if category_id and category_id != cat_id:
                continue
            for card in rail.get('cards', []):
                if not isinstance(card, dict):
                    continue
                card_id = str(card.get('id') or '')
                title = card.get('title', '')
                if not card_id or not title:
                    continue
                if route and card.get('type') != route:
                    continue
                haystack = ' '.join([
                    str(title),
                    str(card.get('description', '')),
                    str(card.get('contentType', '')),
                    str(category.get('name', '')),
                ]).lower()
                if terms and not all(term in haystack for term in terms):
                    continue
                key = f"{card.get('type', '')}:{card_id}"
                if key in seen:
                    continue
                seen.add(key)
                yield card

    def _add_vod_card_item(self, itemlist, card):
        title = card.get('title', 'Xumo Play')
        content_type = str(card.get('contentType') or '').upper()
        thumb = _card_image(card)
        card_id = card.get('id', '')
        summary = _overview_from_item(card) or self._asset_overview(card_id)
        duration = _duration_str(card.get('runtime'))

        if content_type == 'SERIES' or card.get('type') == 'tv-shows':
            display = f'[COLOR deepskyblue]>[/COLOR] {title}'
            itemlist.append({
                'type': 'dir',
                'title': display,
                'link': _card_route(card),
                'thumbnail': thumb,
                'summary': summary,
            })
            return

        display = f'[COLOR red]>[/COLOR] {title}'
        if duration:
            display += f' [COLOR grey]({duration})[/COLOR]'
        itemlist.append({
            'type': 'item',
            'title': display,
            'link': f"{self.asset_url}/{quote(card_id, safe='')}",
            'thumbnail': thumb,
            'summary': summary,
            'is_playable': 'true',
        })

    def _add_vod_category_items(self, itemlist, page, route):
        for rail in self._rails_from_page(page):
            category = rail.get('category', {}) if isinstance(rail, dict) else {}
            cards = rail.get('cards', []) if isinstance(rail, dict) else []
            if not isinstance(category, dict) or not cards:
                continue
            cat_id = str(category.get('deepLink') or category.get('id') or '')
            name = category.get('name', '')
            if not cat_id or not name:
                continue
            itemlist.append({
                'type': 'dir',
                'title': f'[COLOR limegreen]>[/COLOR] {name} [COLOR grey]({len(cards)})[/COLOR]',
                'link': f'{self.vod_cat_url}/{quote(route, safe="")}/{quote(cat_id, safe="")}',
                'thumbnail': _card_image(cards[0]) if cards else 'resources/media/live_tv.png',
            })

    def _add_show_detail_items(self, itemlist, page):
        entity = page.get('entity', {}) if isinstance(page, dict) else {}
        seasons = entity.get('seasons', []) if isinstance(entity, dict) else []
        series_thumb = _card_image(entity) if isinstance(entity, dict) else ''
        series_summary = _overview_from_item(entity)
        if not isinstance(seasons, list):
            return

        for season in seasons:
            if not isinstance(season, dict):
                continue
            category = season.get('category', {}) if isinstance(season.get('category', {}), dict) else {}
            season_meta = season.get('season', {}) if isinstance(season.get('season', {}), dict) else {}
            season_name = category.get('name') or f"Season {season_meta.get('number', '')}".strip()
            cards = season.get('cards', [])
            if not isinstance(cards, list) or not cards:
                continue
            itemlist.append({
                'type': 'dir',
                'title': f'[COLOR orange]-- {season_name} ({len(cards)} episodes) --[/COLOR]',
                'link': self.shows_url,
                'thumbnail': series_thumb,
                'summary': series_summary,
            })
            for card in cards:
                ep_title = card.get('title', 'Episode')
                season_num = card.get('season') or season_meta.get('number', '')
                ep_num = card.get('episode', '')
                prefix = f'S{season_num}E{ep_num} ' if season_num and ep_num else ''
                duration = _duration_str(card.get('duration') or card.get('runtime'))
                display = f'[COLOR limegreen]>[/COLOR] {prefix}{ep_title}'
                if duration:
                    display += f' [COLOR grey]({duration})[/COLOR]'
                itemlist.append({
                    'type': 'item',
                    'title': display,
                    'link': f"{self.asset_url}/{quote(card.get('id', ''), safe='')}",
                    'thumbnail': _card_image(card) or series_thumb,
                    'summary': _overview_from_item(card) or series_summary,
                    'is_playable': 'true',
                })

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
                        'summary': _overview_from_item(asset),
                        'link': _build_stream_url(uri, self.user_agent),
                    }
        return {}

    def _resolve_asset(self, asset_id):
        asset = self._api_get(f'{API_BASE}/assets/asset/{asset_id}.json{BROADCAST_QS}')
        providers = asset.get('providers', []) if isinstance(asset, dict) else []
        fallback = ''
        saw_drm = False
        for provider in providers:
            provider_id = provider.get('id', '')
            for source in provider.get('sources', []):
                if not isinstance(source, dict):
                    continue
                uri = source.get('uri', '')
                produces = source.get('produces', '')
                if not uri:
                    continue
                if source.get('drm'):
                    saw_drm = True
                    drm = source.get('drm') if isinstance(source.get('drm'), dict) else {}
                    if (
                            drm.get('widevine')
                            and ('.mpd' in uri or 'dash' in produces.lower())):
                        license_url = self._widevine_license_url(provider_id, asset_id)
                        if license_url:
                            return {
                                'title': asset.get('title') or provider.get('title') or 'Xumo Play',
                                'summary': _overview_from_item(asset),
                                'link': uri,
                                'type': 'widevine',
                                'license_key': _widevine_license_key(license_url, self.user_agent),
                            }
                    continue
                if '.m3u8' in uri or 'mpegURL' in produces:
                    return {
                        'title': asset.get('title') or provider.get('title') or 'Xumo Play',
                        'summary': _overview_from_item(asset),
                        'link': _build_stream_url(uri, self.user_agent),
                    }
                if not fallback and ('.mpd' in uri or 'dash' in produces.lower()):
                    fallback = uri
        if fallback:
            return {
                'title': asset.get('title') or 'Xumo Play',
                'summary': _overview_from_item(asset),
                'link': _with_kodi_headers(fallback, self.user_agent),
            }
        if saw_drm:
            return {
                'title': asset.get('title') or 'Xumo Play',
                'summary': _overview_from_item(asset),
                'drm': True,
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
                if resolved.get('type'):
                    data['playback_type'] = resolved.get('type')
                if resolved.get('license_key'):
                    data['license_key'] = resolved.get('license_key')
            except Exception:
                xbmcgui.Dialog().notification(
                    'Xumo Play', 'Failed to resolve stream',
                    xbmcgui.NOTIFICATION_WARNING, 3000,
                )
                return True

        if link.startswith(self.asset_url + '/'):
            asset_id = unquote(link.replace(self.asset_url + '/', '').split('/')[0])
            try:
                resolved = self._resolve_asset(asset_id)
                if not resolved.get('link'):
                    message = (
                        'DRM stream not playable'
                        if resolved.get('drm') else
                        'Stream not available'
                    )
                    xbmcgui.Dialog().notification(
                        'Xumo Play', message,
                        xbmcgui.NOTIFICATION_WARNING, 3000,
                    )
                    return True
                link = resolved.get('link', '')
                data.setdefault('title', resolved.get('title', 'Xumo Play'))
                data.setdefault('summary', resolved.get('summary', ''))
                if resolved.get('type'):
                    data['playback_type'] = resolved.get('type')
                if resolved.get('license_key'):
                    data['license_key'] = resolved.get('license_key')
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
        if data.get('playback_type') == 'widevine':
            if not self._ensure_widevine_inputstream():
                xbmcgui.Dialog().notification(
                    'Xumo Play',
                    'inputstream.adaptive/Widevine is not available',
                    xbmcgui.NOTIFICATION_WARNING,
                    3000,
                )
                return True
            self._configure_widevine_item(liz, data.get('license_key', ''))
        else:
            liz.setMimeType('application/vnd.apple.mpegurl')
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass

        xbmc.Player().play(link, liz)
        return True

    def _ensure_widevine_inputstream(self):
        try:
            import inputstreamhelper
            helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
            return helper.check_inputstream()
        except Exception:
            return True

    def _configure_widevine_item(self, liz, license_key):
        liz.setMimeType('application/dash+xml')
        liz.setProperty('inputstream', 'inputstream.adaptive')
        liz.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        liz.setProperty('inputstream.adaptive.stream_headers', _kodi_header_query(self.user_agent))
        liz.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        liz.setProperty('inputstream.adaptive.license_key', license_key)

    def from_keyboard(self, default_text='', header='Search Xumo Play'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
