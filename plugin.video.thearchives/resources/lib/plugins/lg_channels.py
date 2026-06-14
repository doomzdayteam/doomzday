import json
import re
import sys
from html import unescape
from urllib.parse import quote, unquote, urljoin
from uuid import uuid4

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


FANART = Addon().getAddonInfo('fanart')

BASE_URL = 'https://lgchannels.com'
API_BASE = 'https://api.lgchannels.com/api/v1.0'
LINEUP_API_BASE = 'https://api.lgchannels.com/lineupapi/v1.0'
DEFAULT_COUNTRY = 'US'
LANGUAGE = 'en'
LG_COUNTRIES = [
    ('us', 'United States', 'US'),
    ('au', 'Australia', 'AU'),
]
LG_COUNTRY_BY_SLUG = {slug: {'label': label, 'country': country}
                      for slug, label, country in LG_COUNTRIES}
LG_COUNTRY_SOURCES = {
    'au': 'https://tv-experience.lg.com.au/lg-channels',
    'gb': 'https://www.lg.com/uk/lg-experience/helpful-hints/lg-smart-tv-channels/',
}


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


def _strip_html(text):
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', unescape(str(text))).strip()[:800]


def _absolute_url(url):
    if not isinstance(url, str) or not url:
        return ''
    if url.startswith('//'):
        return f'https:{url}'
    if url.startswith('http'):
        return url
    return url


def _with_kodi_headers(url, user_agent, referer=BASE_URL):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer, safe="")}'
    )


def _country_code(slug):
    info = LG_COUNTRY_BY_SLUG.get(slug or '')
    return info.get('country') if info else DEFAULT_COUNTRY


def _country_label(slug):
    info = LG_COUNTRY_BY_SLUG.get(slug or '')
    return info.get('label') if info else 'LG Channels'


def _route_url(url):
    return str(url or '').split('?', 1)[0]


def _replace_ssai_placeholders(url, user_agent, country=DEFAULT_COUNTRY):
    if not isinstance(url, str) or not url:
        return ''

    device_id = str(uuid4())
    values = {
        'DEVICE_ID': device_id,
        'IFA': device_id,
        'IFA_TYPE': 'rida',
        'LMT': '0',
        'DNS': '0',
        'UA': user_agent,
        'IP': '',
        'GDPR': '0',
        'GDPR_CONSENT': '',
        'COUNTRY': country,
        'US_PRIVACY': '1---',
        'APP_STOREURL': BASE_URL,
        'APP_BUNDLE': 'lgchannels.web',
        'APP_NAME': 'LG Channels',
        'APP_VERSION': '1.0.0',
        'DEVICE_TYPE': 'WEB',
        'DEVICE_MAKE': 'LG',
        'DEVICE_MODEL': 'WEB',
        'TARGETAD_ALLOWED': '1',
        'FCK': device_id,
        'VIEWSIZE': '1920x1080',
        'NONCE': str(uuid4()),
        'PCS': '',
    }

    for key, value in values.items():
        url = url.replace(f'[{key}]', quote(str(value), safe=''))
    return re.sub(r'\[[A-Z0-9_]+\]', '', url)


def _channel_key(number, name):
    return f'{str(number or "").strip()}::{str(name or "").strip().lower()}'


def _merge_lineup_and_logos(lineup, genres):
    logo_map = {}
    for genre in (genres or {}).get('genres', []):
        for channel in genre.get('channels', []):
            key = _channel_key(channel.get('channelNumber'), channel.get('channelName'))
            logo_map[key] = _absolute_url(channel.get('channelLogoUrl', ''))

    categories = []
    for category in (lineup or {}).get('channelList', []):
        channels = []
        for channel in category.get('channelInfo', []):
            number = str(channel.get('channelNumber', '')).strip()
            name = str(channel.get('channelName', '')).strip()
            channel_id = str(channel.get('channelId', '')).strip()
            key = _channel_key(number, name)
            if not channel_id or not name:
                continue
            if key not in logo_map:
                continue
            channels.append({
                'id': channel_id,
                'number': number,
                'name': name,
                'provider': str(channel.get('providerId', '')).strip(),
                'category': category.get('categoryName', ''),
                'logo': logo_map.get(key, ''),
            })
        if channels:
            categories.append({
                'name': category.get('categoryName', 'Channels'),
                'code': category.get('categoryCode', ''),
                'channels': channels,
            })
    return categories


def _load_json(response):
    try:
        return json.loads(response or '{}')
    except (json.JSONDecodeError, TypeError):
        return {}


def _clean_title(title):
    return re.sub(r'\[/?COLOR[^\]]*\]', '', str(title or 'LG Channels')).strip()


def _source_channels_from_html(html, source_url):
    channels = []
    row_re = re.compile(
        r'<tr[^>]*>.*?'
        r'<td[^>]*class="[^"]*brand[^"]*"[^>]*>.*?'
        r'<img[^>]+src="(?P<logo>[^"]+)"[^>]*>.*?</td>.*?'
        r'<td[^>]*class="[^"]*channel-no[^"]*"[^>]*>(?P<number>.*?)</td>.*?'
        r'<td[^>]*class="[^"]*channel-name[^"]*"[^>]*>(?P<name>.*?)</td>.*?'
        r'<td[^>]*class="[^"]*description[^"]*"[^>]*>(?P<description>.*?)</td>.*?'
        r'</tr>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in row_re.finditer(html or ''):
        number = _strip_html(match.group('number'))
        name = _strip_html(match.group('name'))
        if not name:
            continue
        channels.append({
            'id': f'source:{number}:{name}',
            'number': number,
            'name': name,
            'description': _strip_html(match.group('description')),
            'logo': urljoin(source_url, unescape(match.group('logo')).strip()),
            'source': source_url,
        })
    return channels


class LGChannels(Plugin):
    

    name = 'lg_channels'
    priority = 1048

    def __init__(self):
        self.session = DI.session
        self.base_url = BASE_URL
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        )
        self.headers = self._headers(DEFAULT_COUNTRY)

        self.country_url = f'{self.base_url}/country'
        self.live_url = f'{self.base_url}/live'
        self.live_cat_url = f'{self.live_url}/category'
        self.channel_url = f'{self.base_url}/channel'
        self.search_url = f'{self.base_url}/search'

    def _headers(self, country=DEFAULT_COUNTRY):
        return {
            'User-Agent': self.user_agent,
            'Referer': f'{BASE_URL}/',
            'Accept': 'application/json, text/plain, */*',
            'Origin': BASE_URL,
            'X-Device-Type': 'WEB',
            'X-Device-Country': country or DEFAULT_COUNTRY,
            'X-Device-Language': LANGUAGE,
        }

    def _country_context(self, url):
        clean_url = _route_url(url)
        if not clean_url.startswith(self.country_url + '/'):
            return None, clean_url

        route = clean_url.replace(self.country_url + '/', '', 1)
        slug, _, tail = route.partition('/')
        if slug not in LG_COUNTRY_BY_SLUG:
            return None, clean_url

        inner_url = f'{self.base_url}/{tail}' if tail else self.base_url
        return slug, inner_url

    def _country_link(self, country_slug, inner_url):
        if not country_slug:
            return inner_url
        if inner_url == self.base_url:
            return f'{self.country_url}/{country_slug}'
        tail = inner_url.replace(self.base_url + '/', '', 1)
        return f'{self.country_url}/{country_slug}/{tail}'

    def _api_get(self, url, params=None, referer=None, country=DEFAULT_COUNTRY):
        headers = self._headers(country)
        if referer:
            headers['Referer'] = referer
        resp = self.session.get(url, params=params or {}, headers=headers)
        try:
            return resp.json()
        except ValueError:
            return _load_json(resp.text)

    def _live_payload(self, country=DEFAULT_COUNTRY):
        lineup = self._api_get(f'{LINEUP_API_BASE}/channellist', country=country)
        genres = self._api_get(f'{API_BASE}/channellist', {'deviceType': 'Web'}, country=country)
        return {'lineup': lineup, 'genres': genres}

    def _source_channels(self, country_slug):
        source_url = LG_COUNTRY_SOURCES.get(country_slug or '')
        if not source_url:
            return []
        try:
            response = self.session.get(source_url, headers={
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml',
            })
            return _source_channels_from_html(response.text, source_url)
        except Exception:
            return []

    def _schedule_payload(self, channel_id, country=DEFAULT_COUNTRY):
        return self._api_get(
            f'{API_BASE}/schedulelist',
            {'channelId': channel_id},
            referer=f'{BASE_URL}/live',
            country=country,
        )

    def get_list(self, url):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        country_slug, route_url = self._country_context(url)
        country = _country_code(country_slug)

        if country_slug and route_url == self.base_url:
            return json.dumps({'kind': 'country_root', 'country': country_slug})

        if route_url == self.base_url:
            return json.dumps({'kind': 'countries'})

        if route_url == self.search_url:
            query = self.from_keyboard()
            if not query:
                sys.exit()
            return json.dumps({
                'kind': 'search',
                'query': query,
                'country': country_slug,
                'live': self._live_payload(country),
            })

        if route_url == self.live_url or route_url.startswith(self.live_cat_url + '/'):
            payload = self._live_payload(country)
            payload['kind'] = 'live'
            payload['country'] = country_slug
            payload['sourceUrl'] = LG_COUNTRY_SOURCES.get(country_slug or '', '')
            payload['sourceChannels'] = self._source_channels(country_slug)
            return json.dumps(payload)

        if route_url.startswith(self.channel_url + '/'):
            channel_id = unquote(route_url.replace(self.channel_url + '/', '').split('/')[0])
            return json.dumps({
                'kind': 'channel',
                'channelId': channel_id,
                'country': country_slug,
                'schedule': self._schedule_payload(channel_id, country),
            })

        return None

    def parse_list(self, url, response):
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        itemlist = []
        data = _load_json(response)
        country_slug, route_url = self._country_context(url)

        if country_slug and route_url == self.base_url:
            country_label = _country_label(country_slug)
            return [
                {
                    'type': 'dir',
                    'title': f'[COLOR orange]-- {country_label} --[/COLOR]',
                    'link': self._country_link(country_slug, self.base_url),
                    'thumbnail': 'resources/media/lg.png',
                    'summary': f'Source: {self._country_link(country_slug, self.base_url)}',
                },
                {
                    'type': 'dir',
                    'title': '[COLOR deepskyblue]Search LG Channels[/COLOR]',
                    'link': self._country_link(country_slug, self.search_url),
                    'thumbnail': 'resources/media/lg.png',
                    'summary': f'Source: {self._country_link(country_slug, self.search_url)}',
                },
                {
                    'type': 'dir',
                    'title': '[COLOR orange]-- Live TV --[/COLOR]',
                    'link': self._country_link(country_slug, self.live_url),
                    'thumbnail': 'resources/media/lg.png',
                    'summary': f'Source: {self._country_link(country_slug, self.live_url)}',
                },
            ]

        if route_url == self.base_url:
            for slug, label, country in LG_COUNTRIES:
                source = f'{self.country_url}/{slug}'
                source_summary = LG_COUNTRY_SOURCES.get(slug, source)
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR cyan]{label} ({country})[/COLOR]',
                    'link': source,
                    'thumbnail': 'resources/media/lg.png',
                    'summary': f'Source: {source_summary}',
                })
            return itemlist

        if route_url == self.search_url:
            query = str(data.get('query', '')).lower()
            live = data.get('live', {})
            country_slug = data.get('country') or country_slug
            for category in _merge_lineup_and_logos(live.get('lineup', {}), live.get('genres', {})):
                for channel in category.get('channels', []):
                    haystack = f"{channel.get('number', '')} {channel.get('name', '')} {category.get('name', '')}".lower()
                    if query in haystack:
                        self._add_channel_item(itemlist, channel, country_slug)
            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No results found[/COLOR]',
                    'link': self._country_link(country_slug, self.base_url),
                })
            return itemlist

        if route_url == self.live_url:
            country_slug = data.get('country') or country_slug
            categories = _merge_lineup_and_logos(data.get('lineup', {}), data.get('genres', {}))
            for category in categories:
                category_link = self._country_link(
                    country_slug,
                    f"{self.live_cat_url}/{quote(category['name'], safe='')}",
                )
                itemlist.append({
                    'type': 'dir',
                    'title': f"[COLOR orange]{category['name']}[/COLOR] ({len(category['channels'])})",
                    'link': category_link,
                    'thumbnail': 'resources/media/live_tv.png',
                    'summary': f'Source: {category_link}',
                })
            if not itemlist:
                for channel in data.get('sourceChannels') or []:
                    self._add_source_channel_item(itemlist, channel)
            if not itemlist and data.get('sourceUrl'):
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No channel list found on LG source page[/COLOR]',
                    'link': 'message/LG does not publish a channel table or Kodi-playable stream URLs at this country source page.',
                    'thumbnail': 'resources/media/lg.png',
                    'summary': f"Source: {data.get('sourceUrl')}",
                })
            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No live channels available[/COLOR]',
                    'link': self._country_link(country_slug, self.base_url),
                })
            return itemlist

        if route_url.startswith(self.live_cat_url + '/'):
            country_slug = data.get('country') or country_slug
            wanted = unquote(route_url.replace(self.live_cat_url + '/', '').split('/')[0])
            categories = _merge_lineup_and_logos(data.get('lineup', {}), data.get('genres', {}))
            for category in categories:
                if category.get('name') != wanted:
                    continue
                for channel in category.get('channels', []):
                    self._add_channel_item(itemlist, channel, country_slug)
                break
            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No channels found[/COLOR]',
                    'link': self._country_link(country_slug, self.live_url),
                })
            return itemlist

        if route_url.startswith(self.channel_url + '/'):
            country_slug = data.get('country') or country_slug
            channel = self._channel_from_schedule(data.get('schedule', {}))
            if channel:
                self._add_schedule_channel_item(itemlist, channel, _country_code(country_slug))
            else:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]Stream not available[/COLOR]',
                    'link': self._country_link(country_slug, self.live_url),
                })
            return itemlist

        return None

    def _add_channel_item(self, itemlist, channel, country_slug=None):
        title = channel.get('name', 'LG Channel')
        number = channel.get('number', '')
        display = f'[COLOR red]>[/COLOR] {number} - {title}' if number else f'[COLOR red]>[/COLOR] {title}'
        link = f"{self.channel_url}/{quote(channel.get('id', ''), safe='')}"
        itemlist.append({
            'type': 'item',
            'title': display,
            'link': self._country_link(country_slug, link),
            'thumbnail': channel.get('logo', '') or 'resources/media/live_tv.png',
            'summary': channel.get('category', ''),
            'is_playable': 'true',
        })

    def _add_source_channel_item(self, itemlist, channel):
        title = channel.get('name', 'LG Channel')
        number = channel.get('number', '')
        display = f'[COLOR red]>[/COLOR] {number} - {title}' if number else f'[COLOR red]>[/COLOR] {title}'
        message = (
            f'{title} is listed by LG, but LG does not publish a '
            'Kodi-playable stream URL for this channel source.'
        )
        itemlist.append({
            'type': 'dir',
            'title': display,
            'link': f'message/{message}',
            'thumbnail': channel.get('logo', '') or 'resources/media/live_tv.png',
            'summary': f"{channel.get('description', '')}\nSource: {channel.get('source', '')}".strip(),
        })

    def _add_schedule_channel_item(self, itemlist, channel, country=DEFAULT_COUNTRY):
        now = self._current_program(channel)
        title = channel.get('channelName', 'LG Channel')
        if now.get('title'):
            title = f"{title} - {now['title']}"
        itemlist.append({
            'type': 'item',
            'title': f'[COLOR red]>[/COLOR] {title}',
            'link': self._stream_from_channel(channel, country),
            'thumbnail': channel.get('channelLogoUrl', '') or now.get('image', '') or 'resources/media/live_tv.png',
            'summary': now.get('description', '') or channel.get('channelName', ''),
            'is_playable': 'true',
        })

    def _channel_from_schedule(self, schedule):
        categories = schedule.get('categories', []) if isinstance(schedule, dict) else []
        for category in categories:
            for channel in category.get('channels', []):
                if channel.get('mediaStaticUrl'):
                    return channel
        return {}

    def _current_program(self, channel):
        programs = channel.get('programs', [])
        if isinstance(programs, list) and programs:
            program = programs[0]
            image = ''
            images = program.get('images', [])
            if isinstance(images, list) and images:
                image = _absolute_url(images[0].get('imageUrl', '')) if isinstance(images[0], dict) else ''
            if not image:
                image = _absolute_url(
                    program.get('imageUrl', '')
                    or program.get('thumbnailUrl', '')
                    or program.get('previewImgUrl', '')
                )
            return {
                'title': program.get('title', '') or program.get('programTitle', ''),
                'description': _strip_html(program.get('description', '')),
                'image': image,
            }
        return {}

    def _stream_from_channel(self, channel, country=DEFAULT_COUNTRY):
        stream_url = _replace_ssai_placeholders(channel.get('mediaStaticUrl', ''), self.user_agent, country)
        return _with_kodi_headers(stream_url, self.user_agent, BASE_URL) if stream_url else ''

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

        country_slug, route_link = self._country_context(link)
        country = _country_code(country_slug)

        if route_link.startswith(self.channel_url + '/'):
            channel_id = unquote(route_link.replace(self.channel_url + '/', '').split('/')[0])
            try:
                schedule = self._schedule_payload(channel_id, country)
                channel = self._channel_from_schedule(schedule)
                stream = self._stream_from_channel(channel, country) if channel else ''
                if not stream:
                    xbmcgui.Dialog().notification(
                        'LG Channels', 'Stream not available',
                        xbmcgui.NOTIFICATION_WARNING, 3000,
                    )
                    return True
                link = stream
                now = self._current_program(channel)
                data.setdefault('title', channel.get('channelName', 'LG Channels'))
                data.setdefault('thumbnail', channel.get('channelLogoUrl', '') or now.get('image', ''))
                data.setdefault('summary', now.get('description', ''))
            except Exception:
                xbmcgui.Dialog().notification(
                    'LG Channels', 'Failed to resolve stream',
                    xbmcgui.NOTIFICATION_WARNING, 3000,
                )
                return True

        if '.m3u8' not in link and 'amagi.tv' not in link and 'lgchannels.com' not in link:
            return None

        title = _clean_title(data.get('title', 'LG Channels'))
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

    def from_keyboard(self, default_text='', header='Search LG Channels'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
