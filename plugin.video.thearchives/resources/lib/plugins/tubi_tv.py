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

FANART = Addon().getAddonInfo('fanart')


BASE_URL         = 'https://tubitv.com'
OZ_BASE          = f'{BASE_URL}/oz'
OZ_VIDEOS        = f'{OZ_BASE}/videos'
IMAGE_BASE       = 'https://images.adrise.tv'
DRM_RESOURCE_MARKERS = ('widevine', 'playready', 'fairplay')


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
        if any(marker in resource_type for marker in DRM_RESOURCE_MARKERS):
            continue
        manifest = resource.get('manifest', {})
        if not isinstance(manifest, dict):
            continue
        manifest_url = _absolute_url(manifest.get('url', ''), '')
        if not manifest_url:
            continue
        if 'hls' in resource_type:
            return manifest_url
        if not fallback:
            fallback = manifest_url
    return fallback


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

        self._device_id = str(uuid4())

   

    def get_list(self, url):
        headers = {
            'User-Agent': self.user_agent,
            'Referer': f'{BASE_URL}/',
            'Accept': 'text/html,application/json',
        }

        
        if url == self.search_url:
            query = self.from_keyboard()
            if not query:
                sys.exit()
            search_page = f'{BASE_URL}/search/{quote(query)}'
            resp = self.session.get(search_page, headers=headers)
            return json.dumps({'_query': query, '_html': resp.text})

        
        if url.startswith(self.video_url + '/'):
            video_id = url.replace(self.video_url + '/', '').split('/')[0]
            resp = self.session.get(f'{BASE_URL}/video/{video_id}', headers=headers)
            return resp.text

        if url.startswith(self.live_cat_url + '/'):
            resp = self.session.get(f'{BASE_URL}/live', headers=headers)
            return resp.text

        if url.startswith(self.live_url + '/'):
            channel_id = url.replace(self.live_url + '/', '').split('/')[0]
            resp = self.session.get(f'{BASE_URL}/live/{channel_id}', headers=headers)
            return resp.text

        
        if url.startswith(self.series_url + '/'):
            series_id = url.replace(self.series_url + '/', '').split('/')[0]
            page_url = f'{BASE_URL}/tv-shows/{series_id}'
            resp = self.session.get(page_url, headers=headers)
            return resp.text

        
        if url.startswith(self.category_url + '/'):
            cat_slug = url.replace(self.category_url + '/', '').split('/')[0]
            page_url = f'{BASE_URL}/category/{cat_slug}'
            resp = self.session.get(page_url, headers=headers)
            return resp.text

        
        if url == self.movies_url:
            resp = self.session.get(f'{BASE_URL}/movies', headers=headers)
            return resp.text

        
        if url == self.tv_url:
            resp = self.session.get(f'{BASE_URL}/tv-shows', headers=headers)
            return resp.text

        
        if url == self.live_url:
            resp = self.session.get(f'{BASE_URL}/live', headers=headers)
            return resp.text

        return None

   

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:

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

        
        if url == self.search_url:
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
                self._add_content_item(itemlist, item, query_filter=query)

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No results found[/COLOR]',
                    'link': self.base_url,
                })
            return itemlist

        
        if url == self.live_url:
            next_data = _extract_next_data(response)
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
            next_data = _extract_next_data(response)
            groups = [group for group in _live_groups(next_data) if group['slug'] == slug]
            headers = {
                'User-Agent': self.user_agent,
                'Referer': f'{BASE_URL}/live',
                'Accept': 'text/html,application/json',
            }
            for channel_id in (groups[0]['contents'] if groups else []):
                try:
                    resp = self.session.get(f'{BASE_URL}/live/{channel_id}', headers=headers)
                    channel_data = _extract_next_data(resp.text)
                    channel = _find_content(channel_data, channel_id)
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
            next_data = _extract_next_data(response)
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
            next_data = _extract_next_data(response)
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

            
            seasons = {}
            ungrouped = []
            for ep in children:
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
                    for ep in eps:
                        self._add_episode_item(itemlist, ep, series_thumb)
            else:
                for ep in (ungrouped or children):
                    self._add_episode_item(itemlist, ep, series_thumb)

            return itemlist

        
        if url.startswith(self.video_url + '/'):
            content_id = _content_id_from_url(url)
            data = _extract_next_data(response)
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

   

    def _add_content_item(self, itemlist, item, query_filter=None):
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

            
            stream_url = _stream_url_from_item(item)
            if stream_url:
                link = _with_kodi_headers(stream_url, self.user_agent, BASE_URL)
            elif item_type in ('l', 'linear', 'channel'):
                link = f'{self.live_url}/{content_id}'
            else:
                link = f'{self.video_url}/{content_id}'

            itemlist.append({
                'type': 'item',
                'title': display,
                'link': link,
                'thumbnail': thumb,
                'summary': summary,
                'is_playable': 'true',
            })

    def _add_episode_item(self, itemlist, ep, series_thumb=''):
        if not isinstance(ep, dict):
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

        stream_url = _stream_url_from_item(ep)
        if stream_url:
            link = _with_kodi_headers(stream_url, self.user_agent, BASE_URL)
        elif ep_id:
            link = f'{self.video_url}/{ep_id}'
        else:
            return

        itemlist.append({
            'type': 'item',
            'title': display,
            'link': link,
            'thumbnail': ep_thumb,
            'summary': ep_summary,
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

       
        detail_prefixes = (
            self.video_url + '/',
            self.movies_url + '/',
            self.tv_url + '/',
            self.live_url + '/',
        )
        if any(link.startswith(prefix) for prefix in detail_prefixes):
            content_id = _content_id_from_url(link)
            try:
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
