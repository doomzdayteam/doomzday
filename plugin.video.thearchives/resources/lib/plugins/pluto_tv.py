import sys
import json
import re
from html import unescape
from urllib.parse import quote, unquote, urlencode
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


BASE_URL         = 'https://pluto.tv'
API_URL          = 'https://api.pluto.tv'
BOOT_URL         = 'https://boot.pluto.tv/v4/start'
STITCHER_BASE    = 'https://cfd-v4-service-channel-stitcher-use1-1.prd.pluto.tv'
IMAGE_BASE       = 'https://images.pluto.tv'
CHANNELS_API     = f'{API_URL}/v2/channels'
VOD_CATEGORIES   = f'{API_URL}/v3/vod/categories'
VOD_SERIES       = f'{API_URL}/v3/vod/series'
VOD_SLUGS        = f'{API_URL}/v3/vod/slugs'


LIVE_CATEGORIES = [
    ('movies',          'Movies'),
    ('entertainment',   'Entertainment'),
    ('news',            'News + Opinion'),
    ('comedy',          'Comedy'),
    ('crime',           'Crime'),
    ('kids',            'Kids'),
    ('classic-tv',      'Classic TV'),
    ('reality',         'Reality'),
    ('competition',     'Competition'),
    ('sports',          'Sports'),
    ('latino',          'Latino'),
    ('gaming',          'Gaming + Anime'),
    ('music',           'Music + Radio'),
    ('explore',         'Explore'),
]

ENGLISH_REGIONS = [
    ('us', 'United States', 'US'),
    ('gb', 'United Kingdom', 'GB'),
    ('au', 'Australia', 'AU'),
]
REGION_BY_SLUG = {slug: {'slug': slug, 'label': label, 'country': country}
                  for slug, label, country in ENGLISH_REGIONS}


def _duration_str(ms):
    
    if not ms:
        return ''
    try:
        total = int(ms) // 1000
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'
    except (ValueError, TypeError):
        return ''


def _best_image(item, fallback=''):
    
    images = item.get('images', [])
    if isinstance(images, list):
        preferred = (
            'colorLogoPNG',
            'logo',
            'tileColor',
            'featuredImage',
            'hero',
            'thumbnail',
        )
        for image_type in preferred:
            for image in images:
                if not isinstance(image, dict):
                    continue
                url = image.get('url', '')
                if image.get('type') == image_type and url and not url.lower().split('?', 1)[0].endswith('.svg'):
                    return url.replace('http://', 'https://', 1)
        for image in images:
            if not isinstance(image, dict):
                continue
            url = image.get('url', '')
            if url and not url.lower().split('?', 1)[0].endswith('.svg'):
                return url.replace('http://', 'https://', 1)
    
    covers = item.get('covers', [])
    if covers:
       
        for cover in covers:
            url = cover.get('url', '')
            if url:
                return url
   
    poster = item.get('poster', {})
    if isinstance(poster, dict):
        url = poster.get('path', '')
        if url:
            return url
   
    for key in ('colorLogoPNG', 'logo', 'solidLogoPNG', 'thumbnail'):
        obj = item.get(key, {})
        if isinstance(obj, dict):
            url = obj.get('path', '')
            if url:
                return url
        elif isinstance(obj, str) and obj:
            return obj
   
    tile = item.get('tile', {})
    if isinstance(tile, dict):
        url = tile.get('path', '')
        if url:
            return url
   
    feat = item.get('featuredImage', {})
    if isinstance(feat, dict):
        url = feat.get('path', '')
        if url:
            return url
    return fallback


def _image_by_type(item, image_type):
    images = item.get('images', [])
    if not isinstance(images, list):
        return ''
    for image in images:
        if not isinstance(image, dict):
            continue
        url = image.get('url', '')
        if image.get('type') == image_type and url and not url.lower().split('?', 1)[0].endswith('.svg'):
            return url.replace('http://', 'https://', 1)
    return ''


def _image_by_key(item, *keys):
    for key in keys:
        obj = item.get(key, {})
        if isinstance(obj, dict):
            url = obj.get('path', '')
        elif isinstance(obj, str):
            url = obj
        else:
            url = ''
        if url and not url.lower().split('?', 1)[0].endswith('.svg'):
            return url.replace('http://', 'https://', 1)
    return ''


def _live_channel_art(item):
    logo = (
        _img_url(_image_by_type(item, 'colorLogoPNG')) or
        _img_url(_image_by_type(item, 'logo')) or
        _img_url(_image_by_type(item, 'solidLogoPNG')) or
        _img_url(_image_by_key(item, 'colorLogoPNG', 'logo', 'solidLogoPNG')) or
        _img_url(_best_image(item))
    )
    return {
        'thumbnail': logo,
        'icon': logo,
        'poster': logo,
        'landscape': logo,
        'fanart': logo,
        'banner': logo,
        'clearlogo': logo,
    }


def _img_url(path):
    
    if not path:
        return ''
    if path.startswith('http'):
        return path
    return f'{IMAGE_BASE}{path}'


def _strip_html(text):
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', str(text))[:500]


def _with_kodi_headers(url, user_agent, referer):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer, safe="")}'
    )


def _clean_title(title):
    return re.sub(r'\[/?COLOR[^\]]*\]', '', str(title or 'Pluto TV')).strip()


def _category_slug(category):
    return re.sub(r'[^a-z0-9]+', '-', str(category or '').lower()).strip('-')


def _api_params(region_slug, **params):
    region = REGION_BY_SLUG.get(region_slug or '')
    country = region.get('country') if region else ''
    if country:
        params['country'] = country
    return params


def _route_url(url):
    return str(url or '').split('?', 1)[0]


def _normalised_search_text(*parts):
    return ' '.join(str(part or '') for part in parts).lower()


class PlutoTV(Plugin):
    
    name = "pluto_tv"
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
            'Accept': 'application/json',
        }

        
        self.region_url     = f'{self.base_url}/region'
        self.live_regions_url = f'{self.base_url}/live-regions'
        self.live_url       = f'{self.base_url}/live'
        self.live_cat_url   = f'{self.base_url}/live/category'
        self.live_search_url = f'{self.base_url}/live/search'
        self.vod_url        = f'{self.base_url}/vod'
        self.vod_categories_url = f'{self.vod_url}/categories'
        self.vod_movies_url = f'{self.base_url}/vod/movies'
        self.vod_shows_url  = f'{self.base_url}/vod/shows'
        self.vod_cat_url    = f'{self.base_url}/vod/category'
        self.vod_item_url   = f'{self.base_url}/vod/item'
        self.vod_series_url = f'{self.base_url}/vod/series'
        self.search_url     = f'{self.base_url}/search'
        self.play_url       = f'{self.base_url}/play'

       
        self._token = None
        self._token_channels = None

    def _route_context(self, url):
        clean_url = _route_url(url)
        if not clean_url.startswith(self.region_url + '/'):
            return None, clean_url

        route = clean_url.replace(self.region_url + '/', '', 1)
        slug, _, tail = route.partition('/')
        if slug not in REGION_BY_SLUG:
            return None, clean_url

        inner_url = f'{self.base_url}/{tail}' if tail else self.base_url
        return slug, inner_url

    def _region_link(self, region_slug, inner_url):
        if not region_slug:
            return inner_url
        if inner_url == self.base_url:
            return f'{self.region_url}/{region_slug}'
        tail = inner_url.replace(self.base_url + '/', '', 1)
        return f'{self.region_url}/{region_slug}/{tail}'



    def _boot(self):
        
        if self._token:
            return self._token

        params = {
            'appName':            'web',
            'appVersion':         '8.0.0',
            'deviceVersion':      '125.0.0',
            'deviceModel':        'web',
            'deviceMake':         'chrome',
            'deviceType':         'web',
            'clientID':           str(uuid4()),
            'clientModelNumber':  '1.0.0',
            'serverSideAds':      'false',
            'drmCapabilities':    'widevine:L3',
        }
        headers = {
            'User-Agent': self.user_agent,
            'Origin': BASE_URL,
            'Referer': f'{BASE_URL}/',
        }
        try:
            resp = self.session.get(BOOT_URL, params=params, headers=headers)
            data = resp.json()
            self._token = data.get('sessionToken', '')
            self._token_channels = data.get('channels', [])
            return self._token
        except Exception:
            return ''

    def _auth_headers(self):
        token = self._boot()
        return {
            'Authorization': f'Bearer {token}',
            'User-Agent': self.user_agent,
            'Origin': BASE_URL,
            'Referer': f'{BASE_URL}/',
            'Accept': 'application/json',
        }

    def _build_live_stream(self, channel_id):
        
        token = self._boot()
        url = (
            f'{STITCHER_BASE}/v2/stitch/hls/channel/'
            f'{channel_id}/master.m3u8'
            f'?jwt={token}&masterJWTPassthrough=true'
        )
        return _with_kodi_headers(url, self.user_agent, BASE_URL)

    def _build_vod_stream(self, raw_url):
        
        token = self._boot()
        
        path = re.sub(r'^https?://[^/]+', '', raw_url.split('?')[0])
        if path.startswith('/stitch/'):
            path = f'/v2{path}'
        url = f'{STITCHER_BASE}{path}?jwt={token}&masterJWTPassthrough=true'
        return _with_kodi_headers(url, self.user_agent, BASE_URL)

    def _vod_categories_response(self, region_slug):
        def fetch():
            headers = self._auth_headers()
            params = _api_params(region_slug, includeItems='true', deviceType='web')
            resp = self.session.get(VOD_CATEGORIES, headers=headers, params=params)
            return resp.text

        return VOD_CACHE.get_or_set_response(
            self.name,
            vod_cache_key('vod_categories', region_slug or 'auto'),
            'catalog',
            fetch,
        )

    def _vod_categories_data(self, region_slug):
        try:
            return json.loads(self._vod_categories_response(region_slug) or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}

    def _vod_series_response(self, region_slug, series_id):
        def fetch():
            headers = self._auth_headers()
            params = _api_params(region_slug, includeItems='true', deviceType='web')
            api_url = f'{VOD_SERIES}/{series_id}/seasons'
            resp = self.session.get(api_url, headers=headers, params=params)
            return resp.text

        return VOD_CACHE.get_or_set_response(
            self.name,
            vod_cache_key('vod_series', region_slug or 'auto', series_id),
            'catalog',
            fetch,
        )

    def _vod_menu_cache_kind(self, route_url):
        if route_url == self.search_url:
            return 'search'
        if route_url in (self.vod_url, self.vod_movies_url, self.vod_shows_url):
            return 'catalog'
        if route_url == self.vod_categories_url:
            return 'catalog'
        if route_url.startswith(self.vod_cat_url + '/') or route_url.startswith(self.vod_series_url + '/'):
            return 'catalog'
        return ''

   
    def get_list(self, url):
        region_slug, route_url = self._route_context(url)

        if route_url == self.live_regions_url:
            return json.dumps({'kind': 'live_regions'})

        if route_url == self.base_url:
            return json.dumps({'kind': 'regions', 'region': region_slug})

        if route_url == self.search_url:
            query = self.from_keyboard(header='Search Pluto On Demand')
            if not query:
                sys.exit()
            return json.dumps({'_query': query, '_data': self._vod_categories_data(region_slug)})

        if route_url == self.live_search_url:
            query = self.from_keyboard(header='Search Pluto Live TV')
            if not query:
                sys.exit()
            if not region_slug:
                self._boot()
            if not region_slug and self._token_channels:
                return json.dumps({'_query': query, '_data': self._token_channels})
            headers = self._auth_headers()
            resp = self.session.get(CHANNELS_API, headers=headers, params=_api_params(region_slug))
            return json.dumps({'_query': query, '_data': resp.json()})

        if route_url == self.live_url or route_url.startswith(self.live_cat_url + '/'):
            if not region_slug:
                self._boot()
            
            if not region_slug and self._token_channels:
                return json.dumps(self._token_channels)
            
            headers = self._auth_headers()
            resp = self.session.get(CHANNELS_API, headers=headers, params=_api_params(region_slug))
            return resp.text

        
        if region_slug and route_url == self.vod_url:
            return json.dumps({'kind': 'vod_root', 'region': region_slug})

        if route_url == self.vod_url or route_url == self.vod_categories_url:
            return self._vod_categories_response(region_slug)

        if route_url in (self.vod_movies_url, self.vod_shows_url):
            return self._vod_categories_response(region_slug)

        
        if route_url.startswith(self.vod_cat_url + '/'):
            cat_id = route_url.replace(self.vod_cat_url + '/', '').split('/')[0]
            return json.dumps({'_cat_id': cat_id, '_data': self._vod_categories_data(region_slug)})

        
        if route_url.startswith(self.vod_series_url + '/'):
            series_id = route_url.replace(self.vod_series_url + '/', '').split('/')[0]
            return self._vod_series_response(region_slug, series_id)

       
        if route_url.startswith(self.vod_item_url + '/'):
            
            return None

        return None

   

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:

        if not url.startswith(self.base_url):
            return None

        region_slug, route_url = self._route_context(url)
        cache_kind = self._vod_menu_cache_kind(route_url)
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

        region_slug, route_url = self._route_context(url)
        itemlist = []

        if route_url == self.live_regions_url:
            for slug, label, country in ENGLISH_REGIONS:
                suffix = f' ({country})' if country else ''
                link = self._region_link(slug, self.live_url)
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR cyan]{label}{suffix}[/COLOR]',
                    'link': link,
                    'summary': f'Source: {link}',
                })
            return itemlist

        
        if not region_slug and route_url == self.base_url:
            for slug, label, country in ENGLISH_REGIONS:
                suffix = f' ({country})' if country else ''
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR cyan]{label}{suffix}[/COLOR]',
                    'link': f'{self.region_url}/{slug}',
                    'summary': 'Pluto TV catalog for this region. Playback still depends on Pluto availability in your location.',
                })
            return itemlist

        if region_slug and route_url == self.base_url:
            region = REGION_BY_SLUG[region_slug]
            region_label = region['label']
            itemlist.append({
                'type': 'dir',
                'title': f'[COLOR orange]-- {region_label} --[/COLOR]',
                'link': self._region_link(region_slug, self.base_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search On Demand[/COLOR]',
                'link': self._region_link(region_slug, self.search_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Live TV[/COLOR]',
                'link': self._region_link(region_slug, self.live_search_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── Live TV ──[/COLOR]',
                'link': self._region_link(region_slug, self.base_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR cyan]▶ All Live Channels[/COLOR]',
                'link': self._region_link(region_slug, self.live_url),
            })
            for cat_slug, cat_name in LIVE_CATEGORIES:
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR cyan]▶[/COLOR] {cat_name}',
                    'link': self._region_link(region_slug, f'{self.live_cat_url}/{cat_slug}'),
                })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── On Demand ──[/COLOR]',
                'link': self._region_link(region_slug, self.base_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR red]▶ All On Demand Movies[/COLOR]',
                'link': self._region_link(region_slug, self.vod_movies_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]▶ All On Demand TV Shows[/COLOR]',
                'link': self._region_link(region_slug, self.vod_shows_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR limegreen]â–¶ Browse All VOD Categories[/COLOR]',
                'link': self._region_link(region_slug, self.vod_categories_url),
            })
            return itemlist

        if region_slug and route_url == self.vod_url:
            region = REGION_BY_SLUG[region_slug]
            region_label = region['label']
            itemlist.append({
                'type': 'dir',
                'title': f'[COLOR orange]-- {region_label} On Demand --[/COLOR]',
                'link': self._region_link(region_slug, self.vod_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search On Demand[/COLOR]',
                'link': self._region_link(region_slug, self.search_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR red]>[/COLOR] All On Demand Movies',
                'link': self._region_link(region_slug, self.vod_movies_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]>[/COLOR] All On Demand TV Shows',
                'link': self._region_link(region_slug, self.vod_shows_url),
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR limegreen]>[/COLOR] Browse All VOD Categories',
                'link': self._region_link(region_slug, self.vod_categories_url),
            })
            return itemlist

        
        if route_url == self.search_url:
            try:
                envelope = json.loads(response)
                query = envelope.get('_query', '').lower()
                data = envelope.get('_data', {})
            except (json.JSONDecodeError, TypeError):
                return itemlist

            categories = data.get('categories', [])
            for cat in categories:
                for item in cat.get('items', []):
                    name = item.get('name', '')
                    if not name:
                        continue
                    
                    searchable = f"{name} {item.get('summary', '')} {item.get('genre', '')}".lower()
                    if query not in searchable:
                        continue

                    identifier = item.get('_id', '')
                    media_type = item.get('type', '')
                    thumb = _img_url(_best_image(item))
                    genre = item.get('genre', '')
                    rating = item.get('rating', '')
                    summary = _strip_html(item.get('summary', ''))
                    duration = _duration_str(item.get('duration', 0))

                    info_parts = []
                    if genre:
                        info_parts.append(genre)
                    if rating:
                        info_parts.append(rating)
                    if duration:
                        info_parts.append(duration)
                    info_line = ' | '.join(info_parts)

                    if media_type == 'series':
                        seasons = item.get('seasonsNumbers', [])
                        season_count = len(seasons) if seasons else 0
                        display = (
                            f'[COLOR deepskyblue]📺[/COLOR] {name}'
                            f' [COLOR grey]({season_count} season{"s" if season_count != 1 else ""})[/COLOR]'
                        )
                        itemlist.append({
                            'type': 'dir',
                            'title': display,
                                'link': self._region_link(region_slug, f'{self.vod_series_url}/{identifier}'),
                            'thumbnail': thumb,
                            'summary': f'{info_line}\n{summary}' if info_line else summary,
                        })
                    elif media_type == 'movie':
                        urls = item.get('stitched', {}).get('urls', [])
                        stream_raw = urls[0].get('url', '') if urls else ''
                        if not stream_raw:
                            continue
                        display = (
                            f'[COLOR red]▶[/COLOR] {name}'
                            f' [COLOR grey]({info_line})[/COLOR]' if info_line else
                            f'[COLOR red]▶[/COLOR] {name}'
                        )
                        itemlist.append({
                            'type': 'item',
                            'title': display,
                            'link': self.play_url,
                            'pluto_vod_raw': stream_raw,
                            'thumbnail': thumb,
                            'summary': summary,
                            'is_playable': 'true',
                        })

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No results found[/COLOR]',
                    'link': self._region_link(region_slug, self.base_url),
                })
            return itemlist

        if route_url == self.live_search_url:
            try:
                envelope = json.loads(response)
                query = envelope.get('_query', '').lower()
                channels = envelope.get('_data', [])
            except (json.JSONDecodeError, TypeError):
                return itemlist

            if not isinstance(channels, list):
                channels = []

            for ch in channels:
                self._add_live_channel_item(itemlist, ch, query_filter=query)

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No live channels found[/COLOR]',
                    'link': self._region_link(region_slug, self.base_url),
                })
            return itemlist

        
        if route_url == self.live_url or route_url.startswith(self.live_cat_url + '/'):
            try:
                channels = json.loads(response)
            except (json.JSONDecodeError, TypeError):
                return itemlist

            
            cat_filter = None
            if route_url.startswith(self.live_cat_url + '/'):
                cat_filter = route_url.replace(self.live_cat_url + '/', '').split('/')[0].lower()

            if not isinstance(channels, list):
                channels = channels if isinstance(channels, list) else []

            for ch in channels:
                ch_id = ch.get('_id', '')
                ch_name = ch.get('name', '')
                ch_number = ch.get('number', '')
                ch_category = ch.get('category', '').lower()
                ch_summary = _strip_html(ch.get('summary', ''))
                art = _live_channel_art(ch)

                if not ch_id or not ch_name:
                    continue

                
                if cat_filter and cat_filter not in ch_category and cat_filter not in _category_slug(ch_category):
                    continue

                stream_url = self._build_live_stream(ch_id)
                number_str = f'[COLOR grey]{ch_number}[/COLOR] ' if ch_number else ''
                display = f'[COLOR cyan]▶[/COLOR] {number_str}{ch_name}'

                itemlist.append({
                    'type': 'item',
                    'title': display,
                    'link': stream_url,
                    'thumbnail': art['thumbnail'],
                    'icon': art['icon'],
                    'poster': art['poster'],
                    'landscape': art['landscape'],
                    'fanart': art['fanart'],
                    'banner': art['banner'],
                    'clearlogo': art['clearlogo'],
                    'summary': ch_summary,
                    'is_playable': 'true',
                })

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No channels found for this category[/COLOR]',
                    'link': self._region_link(region_slug, self.base_url),
                })
            return itemlist

        if route_url in (self.vod_movies_url, self.vod_shows_url):
            try:
                data = json.loads(response)
            except (json.JSONDecodeError, TypeError):
                return itemlist

            media_type = 'movie' if route_url == self.vod_movies_url else 'series'
            for item in self._iter_vod_items(data.get('categories', []), media_type=media_type):
                self._add_vod_item(itemlist, item, region_slug)

            if not itemlist:
                label = 'movies' if media_type == 'movie' else 'TV shows'
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR grey]No on demand {label} available[/COLOR]',
                    'link': self._region_link(region_slug, self.base_url),
                })
            return itemlist

        
        if route_url == self.vod_url or route_url == self.vod_categories_url:
            try:
                data = json.loads(response)
            except (json.JSONDecodeError, TypeError):
                return itemlist

            categories = data.get('categories', [])
            for cat in categories:
                cat_id = cat.get('_id', '')
                cat_name = cat.get('name', '')
                total = cat.get('totalItemsCount', 0)
                if not cat_id or not cat_name:
                    continue

               
                items = cat.get('items', [])
                thumb = ''
                if items:
                    thumb = _img_url(_best_image(items[0]))

                display = f'[COLOR limegreen]▶[/COLOR] {cat_name} [COLOR grey]({total})[/COLOR]'
                itemlist.append({
                    'type': 'dir',
                    'title': display,
                    'link': self._region_link(region_slug, f'{self.vod_cat_url}/{cat_id}'),
                    'thumbnail': thumb,
                    'summary': f'{total} titles',
                })

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No VOD categories available[/COLOR]',
                    'link': self._region_link(region_slug, self.base_url),
                })
            return itemlist

        
        if route_url.startswith(self.vod_cat_url + '/'):
            try:
                envelope = json.loads(response)
                target_id = envelope.get('_cat_id', '')
                data = envelope.get('_data', {})
            except (json.JSONDecodeError, TypeError):
                return itemlist

            
            categories = data.get('categories', [])
            items = []
            for cat in categories:
                if cat.get('_id', '') == target_id:
                    items = cat.get('items', [])
                    break

            for item in items:
                identifier = item.get('_id', '')
                name = item.get('name', '')
                media_type = item.get('type', '')
                if not identifier or not name:
                    continue

                thumb = _img_url(_best_image(item))
                genre = item.get('genre', '')
                rating = item.get('rating', '')
                summary = _strip_html(item.get('summary', ''))
                duration = _duration_str(item.get('duration', 0))
                captions = item.get('cc', False)

                info_parts = []
                if genre:
                    info_parts.append(genre)
                if rating:
                    info_parts.append(rating)
                if duration:
                    info_parts.append(duration)
                if captions:
                    info_parts.append('CC')
                info_line = ' | '.join(info_parts)

                if media_type == 'series':
                    seasons = item.get('seasonsNumbers', [])
                    season_count = len(seasons) if seasons else 0
                    display = (
                        f'[COLOR deepskyblue]📺[/COLOR] {name}'
                        f' [COLOR grey]({season_count} season{"s" if season_count != 1 else ""})[/COLOR]'
                    )
                    itemlist.append({
                        'type': 'dir',
                        'title': display,
                        'link': self._region_link(region_slug, f'{self.vod_series_url}/{identifier}'),
                        'thumbnail': thumb,
                        'summary': f'{info_line}\n{summary}' if info_line else summary,
                    })

                elif media_type == 'movie':
                    urls = item.get('stitched', {}).get('urls', [])
                    stream_raw = urls[0].get('url', '') if urls else ''
                    if not stream_raw:
                        continue
                    display = f'[COLOR red]▶[/COLOR] {name}'
                    if info_line:
                        display += f' [COLOR grey]({info_line})[/COLOR]'
                    itemlist.append({
                        'type': 'item',
                        'title': display,
                        'link': self.play_url,
                        'pluto_vod_raw': stream_raw,
                        'thumbnail': thumb,
                        'summary': summary,
                        'is_playable': 'true',
                    })

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No items in this category[/COLOR]',
                    'link': self._region_link(region_slug, self.base_url),
                })
            return itemlist

        
        if route_url.startswith(self.vod_series_url + '/'):
            try:
                data = json.loads(response)
            except (json.JSONDecodeError, TypeError):
                return itemlist

            series_name = data.get('name', 'Unknown Series')
            series_thumb = _img_url(_best_image(data))
            series_summary = _strip_html(data.get('summary', ''))
            seasons = data.get('seasons', [])

            if not seasons:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No seasons available[/COLOR]',
                    'link': self._region_link(region_slug, self.base_url),
                })
                return itemlist

            for season in seasons:
                season_num = season.get('number', '?')
                episodes = season.get('episodes', [])

                if not episodes:
                    continue

                
                itemlist.append({
                    'type': 'dir',
                    'title': (
                        f'[COLOR orange]── Season {season_num} '
                        f'({len(episodes)} episode{"s" if len(episodes) != 1 else ""}) ──[/COLOR]'
                    ),
                    'link': self._region_link(region_slug, self.base_url),
                    'thumbnail': series_thumb,
                    'summary': series_summary,
                })

                for ep in episodes:
                    ep_name = ep.get('name', 'Untitled')
                    ep_num = ep.get('number', '')
                    ep_summary = _strip_html(ep.get('description', ''))
                    ep_duration = _duration_str(ep.get('duration', 0))
                    ep_rating = ep.get('rating', '')
                    ep_thumb = _img_url(_best_image(ep))
                    if not ep_thumb:
                        ep_thumb = series_thumb

                    urls = ep.get('stitched', {}).get('urls', [])
                    stream_raw = urls[0].get('url', '') if urls else ''
                    if not stream_raw:
                        continue


                    info_parts = []
                    if ep_rating:
                        info_parts.append(ep_rating)
                    if ep_duration:
                        info_parts.append(ep_duration)
                    info_line = ' | '.join(info_parts)

                    ep_label = f'E{ep_num}' if ep_num else ''
                    display = f'[COLOR limegreen]▶[/COLOR] {ep_label} {ep_name}'
                    if info_line:
                        display += f' [COLOR grey]({info_line})[/COLOR]'

                    itemlist.append({
                        'type': 'item',
                        'title': display,
                        'link': self.play_url,
                        'pluto_vod_raw': stream_raw,
                        'thumbnail': ep_thumb,
                        'summary': ep_summary,
                        'is_playable': 'true',
                    })

            return itemlist

        return itemlist

    def _iter_vod_items(self, categories, media_type=None, query_filter=None, category_id=None):
        seen = set()
        if not isinstance(categories, list):
            return
        query_filter = str(query_filter or '').lower()

        for cat in categories:
            if not isinstance(cat, dict):
                continue
            if category_id and cat.get('_id', '') != category_id:
                continue
            for item in cat.get('items', []):
                if not isinstance(item, dict):
                    continue
                identifier = item.get('_id', '')
                name = item.get('name', '')
                item_type = item.get('type', '')
                if not identifier or not name:
                    continue
                if media_type and item_type != media_type:
                    continue
                searchable = _normalised_search_text(
                    name,
                    item.get('summary', ''),
                    item.get('genre', ''),
                    item.get('rating', ''),
                    item_type,
                )
                if query_filter and query_filter not in searchable:
                    continue
                key = f'{item_type}:{identifier}'
                if key in seen:
                    continue
                seen.add(key)
                yield item

    def _vod_info_line(self, item):
        info_parts = []
        genre = item.get('genre', '')
        rating = item.get('rating', '')
        duration = _duration_str(item.get('duration', 0))
        captions = item.get('cc', False)
        if genre:
            info_parts.append(genre)
        if rating:
            info_parts.append(rating)
        if duration:
            info_parts.append(duration)
        if captions:
            info_parts.append('CC')
        return ' | '.join(info_parts)

    def _add_vod_item(self, itemlist, item, region_slug):
        identifier = item.get('_id', '')
        name = item.get('name', '')
        media_type = item.get('type', '')
        if not identifier or not name:
            return

        thumb = _img_url(_best_image(item))
        summary = _strip_html(item.get('summary', ''))
        info_line = self._vod_info_line(item)

        if media_type == 'series':
            seasons = item.get('seasonsNumbers', [])
            season_count = len(seasons) if seasons else 0
            season_text = f'{season_count} season{"s" if season_count != 1 else ""}'
            display = f'[COLOR deepskyblue]📺[/COLOR] {name}'
            if season_count:
                display += f' [COLOR grey]({season_text})[/COLOR]'
            itemlist.append({
                'type': 'dir',
                'title': display,
                'link': self._region_link(region_slug, f'{self.vod_series_url}/{identifier}'),
                'thumbnail': thumb,
                'summary': f'{info_line}\n{summary}' if info_line else summary,
            })
            return

        if media_type != 'movie':
            return

        urls = item.get('stitched', {}).get('urls', [])
        stream_raw = urls[0].get('url', '') if urls else ''
        if not stream_raw:
            return
        display = f'[COLOR red]▶[/COLOR] {name}'
        if info_line:
            display += f' [COLOR grey]({info_line})[/COLOR]'
        itemlist.append({
            'type': 'item',
            'title': display,
            'link': self.play_url,
            'pluto_vod_raw': stream_raw,
            'thumbnail': thumb,
            'summary': summary,
            'is_playable': 'true',
        })

    def _add_live_channel_item(self, itemlist, ch, cat_filter=None, query_filter=None):
        if not isinstance(ch, dict):
            return

        ch_id = ch.get('_id', '')
        ch_name = ch.get('name', '')
        ch_number = ch.get('number', '')
        ch_category = ch.get('category', '')
        ch_summary = _strip_html(ch.get('summary', ''))
        if not ch_id or not ch_name:
            return

        category_slug = _category_slug(ch_category)
        if cat_filter:
            cat_filter = cat_filter.lower()
            if cat_filter not in ch_category.lower() and cat_filter not in category_slug:
                return

        query_filter = str(query_filter or '').lower()
        if query_filter:
            searchable = _normalised_search_text(ch_name, ch_summary, ch_category, ch_number)
            if query_filter not in searchable:
                return

        art = _live_channel_art(ch)
        stream_url = self._build_live_stream(ch_id)
        number_str = f'[COLOR grey]{ch_number}[/COLOR] ' if ch_number else ''
        display = f'[COLOR cyan]▶[/COLOR] {number_str}{ch_name}'

        itemlist.append({
            'type': 'item',
            'title': display,
            'link': stream_url,
            'thumbnail': art['thumbnail'],
            'icon': art['icon'],
            'poster': art['poster'],
            'landscape': art['landscape'],
            'fanart': art['fanart'],
            'banner': art['banner'],
            'clearlogo': art['clearlogo'],
            'summary': ch_summary,
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

        if data.get('pluto_vod_raw'):
            link = self._build_vod_stream(data.get('pluto_vod_raw', ''))

        if STITCHER_BASE not in link and 'pluto.tv' not in link:
            return None

        title = _clean_title(data.get('title', 'Pluto TV'))
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

       
        stream_path = link.split('|', 1)[0]
        if '/channel/' in stream_path:
            
            parts = stream_path.split('/channel/')
            ch_slug = parts[1].split('/')[0] if len(parts) > 1 else 'Pluto TV'
            set_video_info(liz, {'title': title if title != 'Pluto TV' else ch_slug})
        else:
            set_video_info(liz, {'title': title, 'plot': data.get('summary', '')})

        liz.setMimeType('application/vnd.apple.mpegurl')
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass

        xbmc.Player().play(link, liz)
        return True

    def from_keyboard(self, default_text='', header='Search Pluto TV'):
       
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
