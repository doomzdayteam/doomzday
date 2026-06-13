import sys
import os
import time
import base64
import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote, unquote, urlencode, urlparse, parse_qs
from typing import List, Optional, Dict
from uuid import uuid4
import xbmc
import xbmcgui
from xbmcaddon import Addon
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info
from ..DI import DI
from ..vod_cache import VOD_CACHE, vod_cache_key

FANART = Addon().getAddonInfo('fanart')


BASE_URL         = 'https://tubitv.com'
OZ_BASE          = f'{BASE_URL}/oz'
OZ_VIDEOS        = f'{OZ_BASE}/videos'
TENSOR_API       = 'https://tensor-cdn.production-public.tubi.io/api/v1'
ACCOUNT_API      = 'https://account.production-public.tubi.io'
CONTENT_API      = 'https://content-cdn.production-public.tubi.io/api/v3/content'
IMAGE_BASE       = 'https://images.adrise.tv'
DRM_RESOURCE_MARKERS = ('widevine', 'playready', 'fairplay')
PLAYBACK_RESOURCES = (
    'hlsv6',
    'hlsv3',
    'hlsv6_widevine_nonclearlead',
    'hlsv6_playready_psshv0',
    'hlsv6_fairplay',
)


VOD_CATEGORIES = [
    ('most_popular',        'Most Popular'),
    ('recently_added',      'Recently Added'),
    ('tubi_originals',      'Tubi Originals'),
    ('action',              'Action'),
    ('adult_animation',     'Adult Animation'),
    ('anime',               'Anime'),
    ('classics',            'Classic TV & Movies'),
    ('comedy',              'Comedy'),
    ('crime_tv',            'Crime TV'),
    ('documentary',         'Documentaries'),
    ('docuseries',          'Docuseries'),
    ('drama',               'Drama'),
    ('family_movies',       'Family Movies'),
    ('family_series',       'Family Shows'),
    ('horror',              'Horror'),
    ('indie_films',         'Indie Movies'),
    ('kid_classics',        'Kid Friendly Classics'),
    ('lgbt',                'LGBTQ+ Storytelling'),
    ('lifestyle_tv',        'Lifestyle'),
    ('music',               'Music'),
    ('mystery',             'Mystery'),
    ('reality_tv',          'Reality TV'),
    ('romance',             'Romance'),
    ('sci_fi_and_fantasy',  'Sci-Fi & Fantasy'),
    ('sports_movies_and_tv','Sports Stories'),
    ('thrillers',           'Thrillers'),
    ('true_crime',          'True Crime'),
    ('westerns',            'Westerns'),
    ('black_cinema',        'Black Cinema'),
    ('creators',            'Creatorverse'),
]


def _duration_str(seconds):
    if not seconds:
        return ''
    try:
        total = int(seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'
    except (ValueError, TypeError):
        return ''


def _absolute_url(url, base=IMAGE_BASE):
    if not isinstance(url, str) or not url:
        return ''
    if url.startswith('//'):
        return f'https:{url}'
    if url.startswith('http'):
        return url
    return f'{base}{url}'


def _best_image(item, fallback=''):
    images = item.get('images', {})
    if isinstance(images, dict):
        for key in ('poster', 'thumbnail', 'landscape', 'background', 'hero'):
            urls = images.get(key, [])
            if isinstance(urls, list):
                for url in urls:
                    if isinstance(url, str) and url:
                        return _absolute_url(url, '')
            elif isinstance(urls, str) and urls:
                return _absolute_url(urls, '')

    for key in ('posterarts', 'thumbnails', 'hero_images', 'backgrounds'):
        imgs = item.get(key, [])
        if isinstance(imgs, list):
            for img in imgs:
                if isinstance(img, str) and img:
                    return _absolute_url(img)
        elif isinstance(imgs, str) and imgs:
            return _absolute_url(imgs)
    for key in ('poster', 'thumbnail', 'image', 'poster_url', 'thumbnail_url', 'img'):
        url = item.get(key, '')
        if isinstance(url, str) and url:
            return _absolute_url(url)
    return fallback


def _strip_html(text):
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', unescape(str(text)))[:500]


def _with_kodi_headers(url, user_agent, referer):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer, safe="")}'
    )


def _kodi_header_query(user_agent, referer=BASE_URL):
    return (
        f'User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer, safe="")}'
    )


def _configure_hls_inputstream(liz, user_agent):
    try:
        has_addon = getattr(xbmc, 'getCondVisibility', lambda _cond: True)
        if not has_addon('System.HasAddon(inputstream.adaptive)'):
            return False
        liz.setProperty('inputstream', 'inputstream.adaptive')
        liz.setProperty('inputstream.adaptive.stream_headers', _kodi_header_query(user_agent))
        return True
    except Exception:
        return False


def _clean_title(title):
    return re.sub(r'\[/?COLOR[^\]]*\]', '', str(title or 'Tubi TV')).strip()


def _content_id_from_url(url):
    m = re.search(r'/(?:video|movies|tv-shows|live)/([^/?#|]+)', str(url or ''))
    return m.group(1) if m else ''


def _stream_url_from_item(item):
    if not isinstance(item, dict):
        return ''

    direct_url = item.get('url', '')
    if isinstance(direct_url, str) and '.m3u8' in direct_url:
        return _absolute_url(direct_url, '')

    resources = item.get('video_resources', [])
    if not isinstance(resources, list):
        return ''

    fallback = ''
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        resource_type = str(resource.get('type', '')).lower()
        is_drm_labelled = any(marker in resource_type for marker in DRM_RESOURCE_MARKERS)
        manifest = resource.get('manifest', {})
        if not isinstance(manifest, dict):
            continue
        manifest_url = _absolute_url(manifest.get('url', ''), '')
        if not manifest_url:
            continue
        if 'hls' in resource_type:
            if is_drm_labelled:
                continue
            return manifest_url
        if not fallback and not is_drm_labelled:
            fallback = manifest_url
    return fallback


def _has_drm_resources(item):
    if not isinstance(item, dict):
        return False

    resources = item.get('video_resources', [])
    if not isinstance(resources, list):
        return False

    for resource in resources:
        if not isinstance(resource, dict):
            continue
        resource_type = str(resource.get('type', '')).lower()
        if any(marker in resource_type for marker in DRM_RESOURCE_MARKERS):
            return True
    return False


def _is_drm_only_item(item):
    return _has_drm_resources(item) and not _stream_url_from_item(item)


def _has_playable_stream(item):
    if not isinstance(item, dict):
        return False
    if _stream_url_from_item(item):
        return True
    for key in ('children', 'episodes', 'items', 'videos'):
        children = item.get(key, [])
        if isinstance(children, dict):
            children = list(children.values())
        if not isinstance(children, list):
            continue
        for child in children:
            if _has_playable_stream(child):
                return True
    return False


def _series_has_only_drm_children(item):
    if not isinstance(item, dict):
        return False
    children = item.get('children', item.get('episodes', []))
    if not children:
        return False
    return not _has_playable_stream(item) and any(_has_drm_resources(child) for child in _collect_contents(item))


def _extract_next_data(html):
    
    m = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>\s*(\{.+?\})\s*</script>',
        html, re.DOTALL,
    )
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, TypeError):
            pass
    
    m = re.search(r'window\.__data\s*=', html)
    if m:
        raw_data = _extract_balanced_object(html, m.end())
        raw_data = _normalise_js_json(raw_data)
        try:
            return json.loads(raw_data)
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _extract_balanced_object(text, start):
    
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        char = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return ''


def _normalise_js_json(text):
    
    if not text:
        return ''
    return re.sub(r'(?<=[:\[,])\s*undefined(?=\s*[,}\]])', 'null', text)


def _page_data(data):
    return data.get('props', {}).get('pageProps', {}) or data


def _json_response(response):
    try:
        return json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return {}


def _category_parts(url):
    parsed = urlparse(url)
    slug = unquote(parsed.path.rstrip('/').split('/')[-1])
    mode = parse_qs(parsed.query).get('content_mode', [''])[0]
    return slug, mode


def _find_content(data, content_id=''):
    contents = _collect_contents(_page_data(data))
    if content_id:
        for item in contents:
            item_id = str(item.get('id', item.get('video_id', item.get('content_id', ''))))
            if item_id == content_id:
                return item
    for item in contents:
        if _stream_url_from_item(item):
            return item
    return contents[0] if contents else {}


def _live_groups(data):
    containers = _page_data(data).get('containers', [])
    if isinstance(containers, list):
        groups = []
        seen = set()
        for group in containers:
            if not isinstance(group, dict):
                continue
            contents = [str(item) for item in group.get('contents', []) if item]
            slug = group.get('container_slug') or group.get('id') or group.get('container_id') or ''
            if not contents or not slug or slug in seen:
                continue
            seen.add(slug)
            groups.append({
                'name': group.get('name') or group.get('title') or slug.replace('_', ' ').title(),
                'slug': slug,
                'contents': contents,
            })
        if groups:
            return groups

    epg = _page_data(data).get('epg', {})
    groups_by_mode = epg.get('contentIdsByContainer', {})
    if not isinstance(groups_by_mode, dict):
        return []

    groups = []
    seen = set()
    for group_list in groups_by_mode.values():
        if not isinstance(group_list, list):
            continue
        for group in group_list:
            if not isinstance(group, dict):
                continue
            contents = [str(item) for item in group.get('contents', []) if item]
            slug = group.get('container_slug', '')
            if not contents or not slug or slug in seen:
                continue
            seen.add(slug)
            groups.append({
                'name': group.get('name', slug.replace('_', ' ').title()),
                'slug': slug,
                'contents': contents,
            })
    return groups


def _collect_contents(data, depth=0):
    
    items = []
    if not isinstance(data, (dict, list)) or depth > 5:
        return items

    if isinstance(data, list):
        for entry in data:
            items.extend(_collect_contents(entry, depth + 1))
        return items

    video_by_id = data.get('video', {}).get('byId', {})
    if isinstance(video_by_id, dict):
        items.extend(_collect_contents(list(video_by_id.values()), depth + 1))

    by_id = data.get('byId', {})
    if isinstance(by_id, dict):
        items.extend(_collect_contents(list(by_id.values()), depth + 1))

    
    item_id = data.get('id', data.get('video_id', data.get('content_id', '')))
    title = data.get('title', data.get('name', ''))
    if item_id and title and data.get('type') in (
        'v', 's', 'l', 'movie', 'series', 'episode', 'channel', 'linear', None,
    ):
        items.append(data)

    
    for key in ('contents', 'children', 'items', 'videos', 'episodes',
                'rows', 'containers', 'cursor_list', 'list'):
        sub = data.get(key)
        if isinstance(sub, (list, dict)):
            items.extend(_collect_contents(sub, depth + 1))

    
    if not items:
        for key, val in data.items():
            if isinstance(val, dict) and ('title' in val or 'children' in val):
                items.extend(_collect_contents(val, depth + 1))

    return items


class TubiTV(Plugin):
    

    name = "tubi_tv"
    priority = 1050

    def __init__(self):
        self.session = DI.session
        self.base_url = BASE_URL
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        )
        self.session.headers = {
            'User-Agent': self.user_agent,
            'Referer': BASE_URL,
            'Accept': 'application/json, text/html',
        }

        
        self.category_url   = f'{self.base_url}/category'
        self.movies_url     = f'{self.base_url}/movies'
        self.tv_url         = f'{self.base_url}/tv-shows'
        self.live_url       = f'{self.base_url}/live'
        self.live_cat_url   = f'{self.live_url}/category'
        self.series_url     = f'{self.base_url}/series'
        self.video_url      = f'{self.base_url}/video'
        self.search_url     = f'{self.base_url}/search'
        self.vod_search_url = f'{self.base_url}/vod/search'

        self._device_id = str(uuid4())
        self._anon_token = ''
        self._anon_token_expires = 0
        self._drm_only_cache = {}

   
    def _cached_vod_page(self, key, url, headers, kind='catalog'):
        return VOD_CACHE.get_or_set_response(
            self.name,
            vod_cache_key(key, url),
            kind,
            lambda: self.session.get(url, headers=headers).text,
        )

    def _api_headers(self, token=''):
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
            'Origin': BASE_URL,
            'Referer': f'{BASE_URL}/',
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers

    def _post_json(self, url, payload, headers=None):
        body = json.dumps(payload, separators=(',', ':'))
        resp = self.session.post(
            url,
            data=body,
            headers=headers or self._api_headers(),
        )
        return json.loads(resp.text)

    def _get_anon_token(self):
        now = time.time()
        if self._anon_token and self._anon_token_expires > now:
            return self._anon_token

        verifier = os.urandom(16).hex()
        challenge = base64.b64encode(
            hashlib.sha256(verifier.encode('utf-8')).digest()
        ).decode('ascii')
        signing_key = self._post_json(
            f'{ACCOUNT_API}/device/anonymous/signing_key',
            {
                'challenge': challenge,
                'version': '1.0.0',
                'platform': 'web',
                'device_id': self._device_id,
            },
            headers={
                **self._api_headers(),
                'Content-Type': 'application/json',
            },
        )

        payload = {
            'verifier': verifier,
            'id': signing_key['id'],
            'platform': 'web',
            'device_id': self._device_id,
        }
        body = json.dumps(payload, separators=(',', ':'))
        tubi_date = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
        canonical = (
            'POST\n/device/anonymous/token\n\n'
            'content-type:application/json\n\n'
            'content-type\n'
            f'{body_hash}'
        )
        string_to_sign = (
            f'TUBI-HMAC-SHA256\n{tubi_date}\n'
            f'{hashlib.sha256(canonical.encode("utf-8")).hexdigest()}'
        )
        key = b'TUBI' + base64.b64decode(signing_key['key'])
        k_date = hmac.new(
            key, tubi_date.split('T')[0].encode('utf-8'), hashlib.sha256
        ).digest()
        k_req = hmac.new(k_date, b'tubi_request', hashlib.sha256).digest()
        signature = hmac.new(k_req, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        query = urlencode({
            'X-Tubi-Algorithm': 'TUBI-HMAC-SHA256',
            'X-Tubi-Date': tubi_date,
            'X-Tubi-Expires': '30',
            'X-Tubi-SignedHeaders': 'content-type',
            'X-Tubi-Signature': signature,
        })
        token_data = self._post_json(
            f'{ACCOUNT_API}/device/anonymous/token?{query}',
            payload,
            headers={
                **self._api_headers(),
                'Content-Type': 'application/json',
            },
        )

        self._anon_token = token_data.get('access_token', '')
        self._anon_token_expires = now + max(int(token_data.get('expires_in', 3600)) - 60, 60)
        return self._anon_token

    def _cached_api_response(self, key, path, params=None, kind='catalog'):
        params = params or {}

        def fetch():
            token = self._get_anon_token()
            resp = self.session.get(
                f'{TENSOR_API}{path}',
                headers=self._api_headers(token),
                params=params,
            )
            return resp.text

        return VOD_CACHE.get_or_set_response(
            self.name,
            vod_cache_key('api', key, path, params),
            kind,
            fetch,
        )

    def _content_detail(self, content_id):
        token = self._get_anon_token()
        params = [('content_id', content_id)]
        for resource in PLAYBACK_RESOURCES:
            params.append(('video_resources', resource))
        resp = self.session.get(
            CONTENT_API,
            headers={
                **self._api_headers(token),
                'Accept-Version': '~5.0.0',
                'x-capability': '{"content_types":["se"]}',
            },
            params=params,
        )
        return json.loads(resp.text)

    def _vod_menu_cache_kind(self, url):
        if url in (self.search_url, self.vod_search_url):
            return 'search'
        if url in (self.movies_url, self.tv_url):
            return 'catalog'
        if url.startswith(self.category_url + '/') or url.startswith(self.series_url + '/'):
            return 'catalog'
        return ''

    def _container_dirs(self, data, content_mode=''):
        itemlist = []
        containers = data.get('containers', [])
        if not isinstance(containers, list):
            return itemlist
        for container in containers:
            if not isinstance(container, dict):
                continue
            container_id = container.get('id') or container.get('container_slug') or container.get('container_id')
            title = container.get('title') or container.get('name')
            if not container_id or not title:
                continue
            query = f'?content_mode={quote(content_mode)}' if content_mode else ''
            itemlist.append({
                'type': 'dir',
                'title': f'[COLOR cyan]>[/COLOR] {title}',
                'link': f'{self.category_url}/{quote(str(container_id))}{query}',
                'thumbnail': _best_image(container),
                'summary': _strip_html(container.get('description', '')),
            })
        return itemlist

    def _is_drm_only_menu_item(self, item, item_type, content_id):
        if item_type in ('l', 'linear', 'channel'):
            return False
        if _is_drm_only_item(item):
            return True
        if item.get('video_resources'):
            return False
        if not content_id:
            return False
        if content_id not in self._drm_only_cache:
            try:
                detail = self._content_detail(content_id)
                self._drm_only_cache[content_id] = (
                    _is_drm_only_item(detail) or
                    (item_type in ('s', 'series') and _series_has_only_drm_children(detail))
                )
            except Exception:
                self._drm_only_cache[content_id] = False
        return self._drm_only_cache[content_id]


    def get_list(self, url):
        headers = {
            'User-Agent': self.user_agent,
            'Referer': f'{BASE_URL}/',
            'Accept': 'text/html,application/json',
        }

        
        if url in (self.search_url, self.vod_search_url):
            query = self.from_keyboard()
            if not query:
                sys.exit()
            search_page = f'{BASE_URL}/search/{quote(query)}'
            html = self._cached_vod_page(vod_cache_key('search', query), search_page, headers, kind='search')
            return json.dumps({'_query': query, '_html': html})

        
        if url.startswith(self.video_url + '/'):
            video_id = url.replace(self.video_url + '/', '').split('/')[0]
            try:
                return json.dumps(self._content_detail(video_id))
            except Exception:
                resp = self.session.get(f'{BASE_URL}/video/{video_id}', headers=headers)
                return resp.text

        if url.startswith(self.live_cat_url + '/'):
            return self._cached_api_response(
                'live_epg',
                '/epg',
                {'is_kids_mode': 'false', 'platform': 'web'},
            )

        if url.startswith(self.live_url + '/'):
            channel_id = url.replace(self.live_url + '/', '').split('/')[0]
            resp = self.session.get(f'{BASE_URL}/live/{channel_id}', headers=headers)
            return resp.text

        
        if url.startswith(self.series_url + '/'):
            series_id = url.replace(self.series_url + '/', '').split('/')[0]
            try:
                return VOD_CACHE.get_or_set_response(
                    self.name,
                    vod_cache_key('content', 'series', series_id),
                    'catalog',
                    lambda: json.dumps(self._content_detail(series_id)),
                )
            except Exception:
                page_url = f'{BASE_URL}/tv-shows/{series_id}'
                return self._cached_vod_page(vod_cache_key('series', series_id), page_url, headers)

        
        if url.startswith(self.category_url + '/'):
            cat_slug, content_mode = _category_parts(url)
            params = {'is_kids_mode': 'false'}
            if content_mode:
                params['content_mode'] = content_mode
            return self._cached_api_response(f'container:{cat_slug}:{content_mode}', f'/containers/{cat_slug}', params)

        
        if url == self.movies_url:
            return self._cached_api_response(
                'browse:movie',
                '/browse_list',
                {'is_kids_mode': 'false', 'content_mode': 'movie'},
            )

        
        if url == self.tv_url:
            return self._cached_api_response(
                'browse:tv',
                '/browse_list',
                {'is_kids_mode': 'false', 'content_mode': 'tv'},
            )

        
        if url == self.live_url:
            return self._cached_api_response(
                'live_epg',
                '/epg',
                {'is_kids_mode': 'false', 'platform': 'web'},
            )

        return None

   

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:

        if not url.startswith(self.base_url):
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

    def _parse_list_uncached(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:

        if not url.startswith(self.base_url):
            return None

        itemlist = []

        
        if url == self.base_url:
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Tubi[/COLOR]',
                'link': self.search_url,
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── Movies ──[/COLOR]',
                'link': self.movies_url,
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── TV Shows ──[/COLOR]',
                'link': self.tv_url,
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── Live TV ──[/COLOR]',
                'link': self.live_url,
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── Browse by Category ──[/COLOR]',
                'link': self.base_url,
            })
            for slug, label in VOD_CATEGORIES:
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR cyan]▶[/COLOR] {label}',
                    'link': f'{self.category_url}/{slug}',
                })
            return itemlist

        
        if url in (self.search_url, self.vod_search_url):
            try:
                envelope = json.loads(response)
                query = envelope.get('_query', '').lower()
                html = envelope.get('_html', '')
            except (json.JSONDecodeError, TypeError):
                return itemlist

            next_data = _extract_next_data(html)
            props = _page_data(next_data)
            contents = _collect_contents(props)

            for item in contents:
                self._add_content_item(itemlist, item, query_filter=query, include_live=(url == self.search_url))

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No results found[/COLOR]',
                    'link': self.base_url,
                })
            return itemlist

        
        if url == self.live_url:
            next_data = _json_response(response) or _extract_next_data(response)
            for group in _live_groups(next_data):
                itemlist.append({
                    'type': 'dir',
                    'title': f"[COLOR orange]{group['name']}[/COLOR] ({len(group['contents'])})",
                    'link': f"{self.live_cat_url}/{quote(group['slug'])}",
                })

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No live channels available[/COLOR]',
                    'link': self.base_url,
                })
            return itemlist

        if url.startswith(self.live_cat_url + '/'):
            slug = unquote(url.replace(self.live_cat_url + '/', '').split('/')[0])
            next_data = _json_response(response) or _extract_next_data(response)
            groups = [group for group in _live_groups(next_data) if group['slug'] == slug]
            contents = next_data.get('contents', {}) if isinstance(next_data, dict) else {}
            for channel_id in (groups[0]['contents'] if groups else []):
                try:
                    channel = contents.get(str(channel_id), {}) if isinstance(contents, dict) else {}
                    if channel:
                        channel = dict(channel)
                        channel.setdefault('type', 'linear')
                    self._add_content_item(itemlist, channel)
                except Exception:
                    continue

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No live channels available[/COLOR]',
                    'link': self.live_url,
                })
            return itemlist

        if (url == self.movies_url or url == self.tv_url or
                url.startswith(self.category_url + '/')):
            api_data = _json_response(response)
            if url == self.movies_url and api_data:
                itemlist.extend(self._container_dirs(api_data, 'movie'))
                return itemlist
            if url == self.tv_url and api_data:
                itemlist.extend(self._container_dirs(api_data, 'tv'))
                return itemlist

            next_data = api_data or _extract_next_data(response)
            props = _page_data(next_data)
            contents = _collect_contents(props)

            for item in contents:
                self._add_content_item(itemlist, item)

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No content available[/COLOR]',
                    'link': self.base_url,
                })
            return itemlist

       
        if url.startswith(self.series_url + '/'):
            next_data = _json_response(response) or _extract_next_data(response)
            props = _page_data(next_data)

            
            series_data = props.get('contentData', props.get('video', props))
            series_name = series_data.get('title', 'Unknown Series')
            series_thumb = _best_image(series_data)
            series_summary = _strip_html(series_data.get('description', ''))

            
            children = series_data.get('children', series_data.get('episodes', []))
            if not children:
                children = _collect_contents(props)

            if not children:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No episodes available[/COLOR]',
                    'link': self.base_url,
                })
                return itemlist

            season_nodes = []
            direct_children = []
            for child in children:
                if isinstance(child, dict) and isinstance(child.get('children'), list):
                    season_nodes.append(child)
                else:
                    direct_children.append(child)

            if season_nodes:
                for idx, season in enumerate(season_nodes, 1):
                    eps = [ep for ep in season.get('children', []) if isinstance(ep, dict)]
                    if not eps:
                        continue
                    season_items = []
                    for ep in eps:
                        self._add_episode_item(season_items, ep, series_thumb)
                    if not season_items:
                        continue
                    season_title = season.get('title') or f'Season {idx}'
                    itemlist.append({
                        'type': 'dir',
                        'title': (
                            f'[COLOR orange]â”€â”€ {season_title} '
                            f'({len(eps)} episode{"s" if len(eps) != 1 else ""}) â”€â”€[/COLOR]'
                        ),
                        'link': self.base_url,
                        'thumbnail': series_thumb,
                        'summary': series_summary,
                    })
                    itemlist.extend(season_items)
                if itemlist:
                    return itemlist

            
            seasons = {}
            ungrouped = []
            for ep in direct_children:
                if not isinstance(ep, dict):
                    continue
                sn = ep.get('season_number', ep.get('seasonNumber', 0))
                try:
                    sn = int(sn)
                except (ValueError, TypeError):
                    sn = 0
                if sn > 0:
                    seasons.setdefault(sn, []).append(ep)
                else:
                    ungrouped.append(ep)

            if seasons:
                for sn in sorted(seasons.keys()):
                    eps = seasons[sn]
                    season_items = []
                    for ep in eps:
                        self._add_episode_item(season_items, ep, series_thumb)
                    if not season_items:
                        continue
                    itemlist.append({
                        'type': 'dir',
                        'title': (
                            f'[COLOR orange]── Season {sn} '
                            f'({len(eps)} episode{"s" if len(eps) != 1 else ""}) ──[/COLOR]'
                        ),
                        'link': self.base_url,
                        'thumbnail': series_thumb,
                        'summary': series_summary,
                    })
                    itemlist.extend(season_items)
            else:
                for ep in (ungrouped or children):
                    self._add_episode_item(itemlist, ep, series_thumb)

            return itemlist

        
        if url.startswith(self.video_url + '/'):
            content_id = _content_id_from_url(url)
            data = _json_response(response) or _extract_next_data(response)
            item = _find_content(data, content_id)
            stream_url = _stream_url_from_item(item)

            if stream_url:
                title = item.get('title', 'Tubi TV')
                thumb = _best_image(item)
                summary = _strip_html(item.get('description', ''))
                play_url = _with_kodi_headers(stream_url, self.user_agent, BASE_URL)
                itemlist.append({
                    'type': 'item',
                    'title': f'[COLOR red]▶[/COLOR] {title}',
                    'link': play_url,
                    'thumbnail': thumb,
                    'summary': summary,
                    'is_playable': 'true',
                })

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]Content not available[/COLOR]',
                    'link': self.base_url,
                })
            return itemlist

        return itemlist

   

    def _add_content_item(self, itemlist, item, query_filter=None, include_live=True):
        if not isinstance(item, dict):
            return

        content_id = str(item.get('id', item.get('video_id', item.get('content_id', ''))))
        title = item.get('title', item.get('name', ''))
        if not content_id or not title:
            return

        if query_filter:
            searchable = f"{title} {item.get('description', '')} {item.get('tags', '')}".lower()
            if query_filter not in searchable:
                return

        thumb = _best_image(item)
        summary = _strip_html(item.get('description', ''))
        item_type = str(item.get('type', item.get('detailed_type', ''))).lower()
        if not include_live and item_type in ('l', 'linear', 'channel'):
            return
        if self._is_drm_only_menu_item(item, item_type, content_id):
            return
        year = item.get('year', item.get('release_year', ''))
        rating = item.get('rating', item.get('content_rating', ''))
        dur_secs = item.get('duration', 0)
        duration = _duration_str(dur_secs)

        info_parts = []
        if year:
            info_parts.append(str(year))
        if rating:
            info_parts.append(str(rating))
        if duration:
            info_parts.append(duration)
        info_line = ' | '.join(info_parts)

        if item_type in ('s', 'series'):
            
            display = f'[COLOR deepskyblue]📺[/COLOR] {title}'
            if info_line:
                display += f' [COLOR grey]({info_line})[/COLOR]'
            itemlist.append({
                'type': 'dir',
                'title': display,
                'link': f'{self.series_url}/{content_id}',
                'thumbnail': thumb,
                'summary': summary,
            })
        else:
            
            display = f'[COLOR red]▶[/COLOR] {title}'
            if info_line:
                display += f' [COLOR grey]({info_line})[/COLOR]'
            if item_type in ('l', 'linear', 'channel'):
                stream_url = _stream_url_from_item(item)
                link = (
                    _with_kodi_headers(stream_url, self.user_agent, BASE_URL)
                    if stream_url else f'{self.live_url}/{content_id}'
                )
                playback_type = 'live'
            else:
                link = f'{self.video_url}/{content_id}'
                playback_type = 'vod'

            itemlist.append({
                'type': 'item',
                'title': display,
                'link': link,
                'thumbnail': thumb,
                'summary': summary,
                'playback_type': playback_type,
                'is_playable': 'true',
            })

    def _add_episode_item(self, itemlist, ep, series_thumb=''):
        if not isinstance(ep, dict):
            return
        if _is_drm_only_item(ep):
            return

        ep_id = str(ep.get('id', ep.get('video_id', ep.get('content_id', ''))))
        ep_name = ep.get('title', 'Untitled')
        ep_num = ep.get('episode_number', ep.get('episodeNumber', ep.get('number', '')))
        ep_season = ep.get('season_number', ep.get('seasonNumber', ''))
        ep_summary = _strip_html(ep.get('description', ''))
        ep_duration = _duration_str(ep.get('duration', 0))
        ep_rating = ep.get('rating', ep.get('content_rating', ''))
        ep_thumb = _best_image(ep) or series_thumb

        info_parts = []
        if ep_rating:
            info_parts.append(str(ep_rating))
        if ep_duration:
            info_parts.append(ep_duration)
        info_line = ' | '.join(info_parts)

        ep_prefix = ''
        if ep_season and ep_num:
            ep_prefix = f'S{ep_season}E{ep_num} '
        elif ep_num:
            ep_prefix = f'E{ep_num} '

        display = f'[COLOR limegreen]▶[/COLOR] {ep_prefix}{ep_name}'
        if info_line:
            display += f' [COLOR grey]({info_line})[/COLOR]'

        if ep_id:
            link = f'{self.video_url}/{ep_id}'
        else:
            return

        itemlist.append({
            'type': 'item',
            'title': display,
            'link': link,
            'thumbnail': ep_thumb,
            'summary': ep_summary,
            'playback_type': 'vod',
            'is_playable': 'true',
        })

  

    def play_video(self, item: str) -> Optional[bool]:
        data = {}
        link = item
        try:
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            data = json.loads(item)
            link = data.get('link', '')
        except (json.JSONDecodeError, TypeError, AttributeError):
            data = {}
            link = item.decode('utf-8') if isinstance(item, bytes) else item

        if not isinstance(link, str):
            return None

        
        is_tubi = any(domain in link for domain in (
            'tubitv.com', 'tubi.io', 'tubi.video', 'adrise.tv',
        ))
        if not is_tubi:
            return None

        playback_type = str(data.get('playback_type', '')).lower()
       
        detail_prefixes = (
            self.video_url + '/',
            self.movies_url + '/',
            self.tv_url + '/',
            self.live_url + '/',
        )
        if any(link.startswith(prefix) for prefix in detail_prefixes):
            if link.startswith(self.live_url + '/'):
                playback_type = 'live'
            elif not playback_type:
                playback_type = 'vod'
            content_id = _content_id_from_url(link)
            try:
                vdata = self._content_detail(content_id)
                stream_url = _stream_url_from_item(vdata)
                if not stream_url and _is_drm_only_item(vdata):
                    xbmcgui.Dialog().notification(
                        'Tubi TV', 'Protected Tubi title skipped',
                        xbmcgui.NOTIFICATION_WARNING, 4000,
                    )
                    return True
                if not stream_url:
                    page_url = link.split('|')[0]
                    resp = self.session.get(page_url, headers={
                        'User-Agent': self.user_agent,
                        'Referer': f'{BASE_URL}/',
                    })
                    page_data = _extract_next_data(resp.text)
                    vdata = _find_content(page_data, content_id)
                    stream_url = _stream_url_from_item(vdata)
                if stream_url:
                    link = _with_kodi_headers(stream_url, self.user_agent, BASE_URL)
                    if not data.get('title'):
                        data['title'] = vdata.get('title', 'Tubi TV')
                    if not data.get('thumbnail'):
                        data['thumbnail'] = _best_image(vdata)
                    if not data.get('summary'):
                        data['summary'] = _strip_html(vdata.get('description', ''))
                elif _is_drm_only_item(vdata):
                    xbmcgui.Dialog().notification(
                        'Tubi TV', 'Protected Tubi title skipped',
                        xbmcgui.NOTIFICATION_WARNING, 4000,
                    )
                    return True
                else:
                    xbmcgui.Dialog().notification(
                        'Tubi TV', 'Stream not available',
                        xbmcgui.NOTIFICATION_WARNING, 3000,
                    )
                    return True
            except Exception:
                xbmcgui.Dialog().notification(
                    'Tubi TV', 'Failed to resolve stream',
                    xbmcgui.NOTIFICATION_WARNING, 3000,
                )
                return True

        title = _clean_title(data.get('title', 'Tubi TV'))
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
        if 'tubi.video' in link and playback_type == 'live':
            _configure_hls_inputstream(liz, self.user_agent)
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass

        xbmc.Player().play(link, liz)
        return True

    def from_keyboard(self, default_text='', header='Search Tubi TV'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
