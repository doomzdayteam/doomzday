import sys
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote, unquote, urljoin, parse_qs, urlparse
from typing import List, Optional, Dict
import xbmc
import xbmcgui
from xbmcaddon import Addon
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info
from ..DI import DI

FANART = Addon().getAddonInfo('fanart')


INVIDIOUS_INSTANCES = [
    'https://vid.puffyan.us',
    'https://inv.nadeko.net',
    'https://invidious.fdn.fr',
    'https://inv.tux.pizza',
    'https://invidious.nerdvpn.de',
]


class YouTubeSearch(Plugin):
    name = "youtubesearch"
    priority = 1050

    def __init__(self):
        self.session = DI.session
        self.base_url = 'https://www.youtube.com'
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
        self.session.headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        
        self.search_url = f'{self.base_url}/search'
        self.channel_search_url = f'{self.base_url}/search_channels'
        self.open_channel_url = f'{self.base_url}/open_channel'
        self.trending_url = f'{self.base_url}/trending'
        self.channel_url = f'{self.base_url}/channel'
        self.playlist_url = f'{self.base_url}/playlist'
        self.video_url = f'{self.base_url}/watch'

        
        self.api_base = self._resolve_instance()
        self.api_url = f'{self.api_base}/api/v1'

   

    def _resolve_instance(self) -> str:
        
        for instance in INVIDIOUS_INSTANCES:
            try:
                r = self.session.get(f'{instance}/api/v1/stats', timeout=5)
                if r.status_code == 200:
                    return instance
            except Exception:
                continue
        
        return INVIDIOUS_INSTANCES[0]

   

    @staticmethod
    def _message_item(title: str, summary: str = '') -> Dict[str, str]:
        return {
            'type': 'item',
            'title': f'[COLOR tomato]{title}[/COLOR]',
            'link': '',
            'summary': summary or title,
            'is_playable': 'false',
        }

    @staticmethod
    def _message_response(title: str, summary: str = '') -> str:
        return json.dumps({'_yt_route': 'message', 'title': title, 'summary': summary})

    def _ytdlp_search(self, query: str, limit: int = 50) -> list:
        from .youtube import load_ytdlp, ytdlp_params

        yt_dlp = load_ytdlp()
        params = ytdlp_params({
            'cachedir': False,
            'extract_flat': 'in_playlist',
            'noplaylist': True,
        })
        with yt_dlp.YoutubeDL(params) as ydl:
            info = ydl.extract_info(f'ytsearch{limit}:{query}', download=False)
        return info.get('entries', [])

    def _ytdlp_url_entries(self, url: str, limit: int = 50) -> list:
        from .youtube import load_ytdlp, ytdlp_params

        yt_dlp = load_ytdlp()
        params = ytdlp_params({
            'cachedir': False,
            'extract_flat': 'in_playlist',
            'noplaylist': False,
            'playlistend': limit,
        })
        with yt_dlp.YoutubeDL(params) as ydl:
            info = ydl.extract_info(url, download=False)
        return info.get('entries', [])

    def _fallback_items(
            self,
            query: str,
            limit: int,
            failure_title: str,
            failure_summary: str = '') -> List[Dict[str, str]]:
        try:
            entries = self._ytdlp_search(query, limit)
        except Exception as exc:
            summary = str(exc)
            if failure_summary:
                summary = f'{failure_summary}; yt-dlp fallback failed: {summary}'
            return [self._message_item(failure_title, summary)]

        items = []
        for entry in entries:
            item = self._ytdlp_entry_to_item(entry)
            if item:
                items.append(item)

        if not items:
            return [self._message_item('No YouTube results found', query)]

        return items

    def _api_get(self, path: str, params: Optional[Dict] = None):
        
        url = f'{self.api_url}{path}'
        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _best_thumbnail(thumbs: list) -> str:
       
        if not thumbs:
            return ''
        
        for quality in ('maxres', 'maxresdefault', 'sddefault', 'high', 'medium'):
            for t in thumbs:
                if t.get('quality', '') == quality:
                    url = t.get('url', '')
                    return url if url.startswith('http') else ''
        
        best = max(thumbs, key=lambda t: t.get('width', 0))
        url = best.get('url', '')
        return url if url.startswith('http') else ''

    @staticmethod
    def _format_duration(seconds: int) -> str:
        
        try:
            seconds = int(seconds or 0)
        except (TypeError, ValueError):
            seconds = 0
        if seconds <= 0:
            return 'LIVE'
        h, remainder = divmod(seconds, 3600)
        m, s = divmod(remainder, 60)
        if h:
            return f'{h}:{m:02d}:{s:02d}'
        return f'{m}:{s:02d}'

    @staticmethod
    def _format_views(count: int) -> str:
        
        try:
            count = int(count or 0)
        except (TypeError, ValueError):
            count = 0
        if count >= 1_000_000:
            return f'{count / 1_000_000:.1f}M views'
        if count >= 1_000:
            return f'{count / 1_000:.1f}K views'
        return f'{count} views'

  

    def get_list(self, url: str):
        
        if url == self.search_url:
            query = self.from_keyboard()
            if not query:
                return self._message_response('YouTube search cancelled')
            
            return json.dumps({'_yt_route': 'search', 'q': query})

        if url == self.channel_search_url:
            query = self.from_keyboard(header='Search YouTube Channels')
            if not query:
                return self._message_response('YouTube channel search cancelled')
            return json.dumps({'_yt_route': 'channel_search', 'q': query})

        if url == self.open_channel_url:
            channel = self.from_keyboard(header='Open YouTube Channel')
            if not channel:
                return self._message_response('Open channel cancelled')
            return json.dumps({
                '_yt_route': 'channel_url',
                'url': self._normalize_channel_url(channel),
            })

        if url.startswith(self.trending_url):
            query = parse_qs(urlparse(url).query)
            route = {'_yt_route': 'trending'}
            if query.get('type'):
                route['type'] = query['type'][0]
            return json.dumps(route)

        if url.startswith(self.channel_url):
            query = parse_qs(urlparse(url).query)
            if query.get('url'):
                return json.dumps({'_yt_route': 'channel_url', 'url': query['url'][0]})
            channel_id = unquote(url.split('/')[-1])
            if channel_id.startswith(('http://', 'https://')):
                return json.dumps({'_yt_route': 'channel_url', 'url': channel_id})
            return json.dumps({'_yt_route': 'channel', 'id': channel_id})

        if url.startswith(self.playlist_url):
            playlist_id = url.split('=')[-1]
            return json.dumps({'_yt_route': 'playlist', 'id': playlist_id})

        if url.startswith(self.video_url):
            
            return None

        if url != self.base_url:
            return None

        return json.dumps({'_yt_route': 'home'})

 

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not url.startswith(self.base_url):
            return None

        try:
            data = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return None

        route = data.get('_yt_route', '')

        if route == 'home':
            return self._parse_home()
        if route == 'message':
            return [self._message_item(data.get('title', 'YouTube'), data.get('summary', ''))]
        if route == 'search':
            return self._parse_search(data['q'])
        if route == 'channel_search':
            return self._parse_channel_search(data['q'])
        if route == 'channel_url':
            return self._parse_channel_url(data['url'])
        if route == 'trending':
            return self._parse_trending(data.get('type', ''))
        if route == 'channel':
            return self._parse_channel(data['id'])
        if route == 'playlist':
            return self._parse_playlist(data['id'])

        return None

   

    def _parse_home(self) -> List[Dict[str, str]]:
        
        itemlist = [
            {
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Videos[/COLOR]',
                'link': self.search_url,
            },
            {
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Channels[/COLOR]',
                'link': self.channel_search_url,
            },
            {
                'type': 'dir',
                'title': '[COLOR deepskyblue]Open Channel URL / @handle[/COLOR]',
                'link': self.open_channel_url,
            },
            {
                'type': 'dir',
                'title': '[COLOR deepskyblue]Trending[/COLOR]',
                'link': self.trending_url,
            },
        ]

        
        for category, label in [
                ('music', 'Trending Music'),
                ('gaming', 'Trending Gaming'),
                ('movies', 'Trending Movies'),
                ('news', 'Trending News')]:
            itemlist.append({
                'type': 'dir',
                'title': f'[COLOR lightyellow]{label}[/COLOR]',
                'link': f'{self.trending_url}?type={category}',
            })

      
        try:
            popular = self._api_get('/popular')
            for video in popular[:20]:
                itemlist.append(self._video_to_item(video))
        except Exception:
            itemlist.extend(self._fallback_items(
                'popular videos today',
                20,
                'YouTube popular failed'))

        return itemlist

    def _parse_search(self, query: str) -> List[Dict[str, str]]:
        
        itemlist = []
        try:
            results = self._api_get('/search', params={
                'q': query,
                'type': 'all',
                'sort_by': 'relevance',
            })
        except Exception as exc:
            return self._fallback_items(
                query,
                50,
                'YouTube search failed',
                str(exc))

        for item in results:
            item_type = item.get('type', '')

            if item_type == 'video':
                itemlist.append(self._video_to_item(item))

            elif item_type == 'channel':
                thumbs = item.get('authorThumbnails', [])
                thumbnail = self._best_thumbnail(thumbs)
                sub_count = item.get('subCount', 0)
                title = item.get('author', 'Unknown Channel')
                desc = f'{self._format_views(sub_count).replace(" views", " subscribers")}'
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR deepskyblue]{title}[/COLOR]',
                    'link': self._make_channel_link(
                        f'{self.base_url}/channel/{item["authorId"]}/videos',
                        item.get('authorId', '')),
                    'thumbnail': thumbnail,
                    'summary': desc,
                })

            elif item_type == 'playlist':
                title = item.get('title', 'Playlist')
                playlist_id = item.get('playlistId', '')
                thumbnail = item.get('playlistThumbnail', '')
                video_count = item.get('videoCount', 0)
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR lightyellow]{title}[/COLOR] ({video_count} videos)',
                    'link': f'{self.playlist_url}?list={playlist_id}',
                    'thumbnail': thumbnail,
                })

        if not itemlist:
            return [self._message_item('No YouTube results found', query)]

        return itemlist

    def _parse_channel_search(self, query: str) -> List[Dict[str, str]]:
       
        url = f'{self.base_url}/results?search_query={quote(query)}&sp=EgIQAg%253D%253D'
        try:
            entries = self._ytdlp_url_entries(url)
        except Exception as exc:
            return [self._message_item('YouTube channel search failed', str(exc))]

        itemlist = []
        for entry in entries:
            item = self._ytdlp_channel_to_item(entry)
            if item:
                itemlist.append(item)

        if not itemlist:
            return [self._message_item('No YouTube channels found', query)]

        return itemlist

    def _parse_live(self, query: str = 'live streams now') -> List[Dict[str, str]]:
        
        url = f'{self.base_url}/results?search_query={quote(query)}&sp=EgJAAQ%253D%253D'
        try:
            entries = self._ytdlp_url_entries(url)
        except Exception as exc:
            return [self._message_item('YouTube live search failed', str(exc))]

        itemlist = []
        for entry in entries:
            item = self._ytdlp_entry_to_item(entry)
            if item:
                itemlist.append(item)

        if not itemlist:
            return [self._message_item('No YouTube live streams found', query)]

        return itemlist

    def _parse_trending(self, category: str = '') -> List[Dict[str, str]]:
       
        itemlist = []
        params = {}
        if category:
            params['type'] = category.title()

        try:
            trending = self._api_get('/trending', params=params)
        except Exception as exc:
            query = f'trending {category} videos' if category else 'trending videos today'
            return self._fallback_items(
                query,
                50,
                'YouTube trending failed',
                str(exc))

        for video in trending:
            itemlist.append(self._video_to_item(video))

        if not itemlist:
            return [self._message_item('No YouTube trending videos found')]

        return itemlist

    def _parse_channel(self, channel_id: str) -> List[Dict[str, str]]:
        
        itemlist = []

        try:
            channel = self._api_get(f'/channels/{channel_id}')
        except Exception as exc:
            return self._parse_channel_url(
                f'{self.base_url}/channel/{channel_id}/videos',
                str(exc))

        name = channel.get('author', 'Unknown')
        description = channel.get('description', '')
        thumbs = channel.get('authorThumbnails', [])
        thumbnail = self._best_thumbnail(thumbs)
        sub_count = channel.get('subCount', 0)
        summary = f'{self._format_views(sub_count).replace(" views", " subscribers")}\n{description}'

        
        itemlist.append({
            'type': 'dir',
            'title': f'[COLOR deepskyblue]{name} – Playlists[/COLOR]',
            'link': f'{self.channel_url}/{channel_id}/playlists',
            'thumbnail': thumbnail,
            'summary': summary,
        })

        
        try:
            videos_data = self._api_get(f'/channels/{channel_id}/videos')
            videos = videos_data.get('videos', [])
        except Exception:
            videos = channel.get('latestVideos', [])

        if not videos:
            return self._parse_channel_url(
                f'{self.base_url}/channel/{channel_id}/videos',
                'Invidious returned no channel videos')

        
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()

        for video in videos:
            title = f"{name} - {video.get('title', 'Untitled')}"
            video_id = video.get('videoId', '')
            link = f'{self.video_url}?v={video_id}'
            vid_thumbnail = self._best_thumbnail(video.get('videoThumbnails', []))
            duration = self._format_duration(video.get('lengthSeconds', 0))
            views = self._format_views(video.get('viewCount', 0))
            published = video.get('publishedText', '')

            liz = xbmcgui.ListItem(title)
            set_video_info(liz, {
                'title': title,
                'plot': f'{views} • {published}\n{description}',
                'duration': video.get('lengthSeconds', 0),
            })
            liz.setArt({
                'thumb': vid_thumbnail or thumbnail,
                'icon': vid_thumbnail or thumbnail,
                'poster': vid_thumbnail or thumbnail,
                'fanart': FANART,
            })
            playlist.add(url=link, listitem=liz)

            itemlist.append({
                'type': 'item',
                'title': f'{title}  [COLOR gray][{duration}][/COLOR]',
                'link': link,
                'thumbnail': vid_thumbnail or thumbnail,
                'summary': f'{views} • {published}',
                'is_playable': 'true',
            })

        if videos:
            xbmc.Player().play(playlist)

        return itemlist

    def _parse_channel_url(
            self,
            channel_url: str,
            failure_summary: str = '') -> List[Dict[str, str]]:
        
        feed_items = self._channel_feed_items(channel_url)
        if feed_items:
            return feed_items

        try:
            entries = self._ytdlp_url_entries(channel_url)
        except Exception as exc:
            summary = str(exc)
            if failure_summary:
                summary = f'{failure_summary}; yt-dlp channel fallback failed: {summary}'
            return [self._message_item('YouTube channel failed', summary)]

        itemlist = self._channel_entries_to_items(entries, channel_url)

        if not itemlist:
            return [self._message_item('No YouTube channel videos found', channel_url)]

        return itemlist

    def _channel_id_from_url(self, channel_url: str) -> str:
        parsed = urlparse(channel_url)
        parts = [part for part in parsed.path.split('/') if part]
        if len(parts) >= 2 and parts[0] == 'channel' and parts[1].startswith('UC'):
            return parts[1]

        lookup_url = f'{parsed.scheme or "https"}://{parsed.netloc or "www.youtube.com"}'
        if parts:
            lookup_url = f'{lookup_url}/{parts[0]}'
        response = self.session.get(lookup_url, timeout=10)
        if hasattr(response, 'raise_for_status'):
            response.raise_for_status()
        html = getattr(response, 'text', '') or ''
        for pattern in (
                r'"channelId":"(UC[^"]+)"',
                r'"externalId":"(UC[^"]+)"',
                r'<meta[^>]+itemprop=["\']channelId["\'][^>]+content=["\'](UC[^"\']+)["\']'):
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return ''

    def _channel_feed_items(self, channel_url: str) -> List[Dict[str, str]]:
        try:
            channel_id = self._channel_id_from_url(channel_url)
            if not channel_id:
                return []
            response = self.session.get(
                f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}',
                timeout=10)
            if hasattr(response, 'raise_for_status'):
                response.raise_for_status()
            root = ET.fromstring(getattr(response, 'text', '') or '')
        except Exception:
            return []

        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'yt': 'http://www.youtube.com/xml/schemas/2015',
            'media': 'http://search.yahoo.com/mrss/',
        }
        itemlist = []
        for entry in root.findall('atom:entry', ns):
            video_id = entry.findtext('yt:videoId', default='', namespaces=ns)
            if not video_id:
                continue
            title = entry.findtext('atom:title', default='Untitled', namespaces=ns)
            author = entry.findtext('atom:author/atom:name', default='', namespaces=ns)
            published = entry.findtext('atom:published', default='', namespaces=ns)
            thumbnail = ''
            media_group = entry.find('media:group', ns)
            if media_group is not None:
                media_thumbnail = media_group.find('media:thumbnail', ns)
                if media_thumbnail is not None:
                    thumbnail = media_thumbnail.get('url', '')
            display_title = f'{author} - {title}' if author else title
            itemlist.append({
                'type': 'item',
                'title': display_title,
                'link': f'{self.video_url}?v={video_id}',
                'thumbnail': thumbnail,
                'summary': published[:10],
                'is_playable': 'true',
            })
        return itemlist

    def _parse_playlist(self, playlist_id: str) -> List[Dict[str, str]]:
        
        itemlist = []

        try:
            data = self._api_get(f'/playlists/{playlist_id}')
        except Exception as exc:
            return [self._message_item('YouTube playlist failed', str(exc))]

        pl_title = data.get('title', 'Playlist')
        author = data.get('author', '')
        videos = data.get('videos', [])

        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()

        for video in videos:
            title = video.get('title', 'Untitled')
            video_id = video.get('videoId', '')
            link = f'{self.video_url}?v={video_id}'
            thumbnail = self._best_thumbnail(video.get('videoThumbnails', []))
            duration = self._format_duration(video.get('lengthSeconds', 0))

            display_title = f'{author} - {title}' if author else title

            liz = xbmcgui.ListItem(display_title)
            set_video_info(liz, {
                'title': display_title,
                'duration': video.get('lengthSeconds', 0),
            })
            liz.setArt({
                'thumb': thumbnail,
                'icon': thumbnail,
                'poster': thumbnail,
                'fanart': FANART,
            })
            playlist.add(url=link, listitem=liz)

            itemlist.append({
                'type': 'item',
                'title': f'{display_title}  [COLOR gray][{duration}][/COLOR]',
                'link': link,
                'thumbnail': thumbnail,
                'is_playable': 'true',
            })

        if videos:
            xbmc.Player().play(playlist)

        return itemlist

   

    def _video_to_item(self, video: dict) -> Dict[str, str]:
        
        title = video.get('title', 'Untitled')
        author = video.get('author', '')
        video_id = video.get('videoId', '')
        thumbnail = self._best_thumbnail(video.get('videoThumbnails', []))
        duration = self._format_duration(video.get('lengthSeconds', 0))
        views = self._format_views(video.get('viewCount', 0))
        published = video.get('publishedText', '')
        display_title = f'{author} - {title}' if author else title

        return {
            'type': 'item',
            'title': f'{display_title}  [COLOR gray][{duration}][/COLOR]',
            'link': f'{self.video_url}?v={video_id}',
            'thumbnail': thumbnail,
            'summary': f'{views} • {published}',
            'is_playable': 'true',
        }

    def _ytdlp_entry_to_item(self, entry: dict) -> Optional[Dict[str, str]]:
        
        video_id = entry.get('id', '')
        if not re.fullmatch(r'[^"&?/\s]{11}', video_id or ''):
            video_id = ''
        if not video_id:
            url = entry.get('url') or entry.get('webpage_url') or ''
            if 'watch?v=' in url:
                video_id = url.split('watch?v=')[-1].split('&')[0]
            elif 'youtu.be/' in url:
                video_id = url.rstrip('/').split('youtu.be/')[-1].split('/')[0]
        if not re.fullmatch(r'[^"&?/\s]{11}', video_id or ''):
            video_id = ''
        if not video_id:
            return None

        title = entry.get('title') or 'Untitled'
        author = entry.get('uploader') or entry.get('channel') or ''
        thumbnail = entry.get('thumbnail') or ''
        if not thumbnail:
            thumbs = entry.get('thumbnails') or []
            if thumbs:
                thumbnail = thumbs[-1].get('url', '')
        duration = self._format_duration(entry.get('duration') or 0)
        views = self._format_views(entry.get('view_count') or 0)
        published = entry.get('upload_date') or entry.get('release_date') or ''
        if len(published) == 8 and published.isdigit():
            published = f'{published[:4]}-{published[4:6]}-{published[6:]}'
        display_title = f'{author} - {title}' if author else title

        summary_parts = [part for part in (views, published) if part]
        return {
            'type': 'item',
            'title': f'{display_title}  [COLOR gray][{duration}][/COLOR]',
            'link': f'{self.video_url}?v={video_id}',
            'thumbnail': thumbnail,
            'summary': ' - '.join(summary_parts),
            'is_playable': 'true',
        }

    def _ytdlp_channel_to_item(self, entry: dict) -> Optional[Dict[str, str]]:
        
        channel_url = entry.get('url') or entry.get('webpage_url') or ''
        channel_id = entry.get('channel_id') or entry.get('id') or ''

        if '/channel/' in channel_url:
            channel_id = channel_url.rstrip('/').split('/channel/')[-1].split('/')[0]
        elif channel_id.startswith('UC'):
            channel_url = f'{self.base_url}/channel/{channel_id}'
        elif channel_url.startswith('/'):
            channel_url = f'{self.base_url}{channel_url}'

        if not channel_url and channel_id:
            channel_url = f'{self.base_url}/channel/{channel_id}'
        if not channel_url:
            return None

        title = entry.get('title') or entry.get('channel') or 'YouTube Channel'
        thumbnail = entry.get('thumbnail') or ''
        if not thumbnail:
            thumbs = entry.get('thumbnails') or []
            if thumbs:
                thumbnail = thumbs[-1].get('url', '')

        sub_count = (
            entry.get('channel_follower_count') or
            entry.get('subscriber_count') or
            entry.get('view_count') or
            0
        )
        summary = self._format_views(sub_count).replace(' views', ' subscribers')
        link = self._make_channel_link(channel_url, channel_id)

        return {
            'type': 'dir',
            'title': f'[COLOR deepskyblue]{title}[/COLOR]',
            'link': link,
            'thumbnail': thumbnail,
            'summary': summary,
        }

    def _make_channel_link(self, channel_url: str = '', channel_id: str = '') -> str:
        if not channel_url and channel_id:
            channel_url = f'{self.base_url}/channel/{channel_id}/videos'
        return f'{self.channel_url}/{quote(self._normalize_channel_url(channel_url), safe="")}'

    def _normalize_channel_url(self, value: str) -> str:
        value = (value or '').strip()
        if not value:
            return self.base_url

        if value.startswith(('youtube.com/', 'www.youtube.com/', 'm.youtube.com/')):
            value = f'https://{value}'
        elif value.startswith('@'):
            value = f'{self.base_url}/{value}'
        elif value.startswith('/'):
            value = f'{self.base_url}{value}'
        elif value.startswith('UC'):
            channel_id = value.split('/')[0]
            return f'{self.base_url}/channel/{channel_id}/videos'
        elif not value.startswith(('http://', 'https://')):
            value = f'{self.base_url}/@{value}'

        parsed = urlparse(value)
        netloc = parsed.netloc or 'www.youtube.com'
        if netloc in ('youtube.com', 'm.youtube.com'):
            netloc = 'www.youtube.com'
        path = parsed.path.rstrip('/')
        if not path.endswith('/videos') and not path.endswith('/streams'):
            path = f'{path}/videos'

        return f'{parsed.scheme or "https"}://{netloc}{path}'

    def _channel_entries_to_items(
            self,
            entries: list,
            source_url: str,
            depth: int = 0) -> List[Dict[str, str]]:
        itemlist = []
        follow_urls = []

        for entry in entries:
            if not entry:
                continue

            nested = entry.get('entries') or []
            if nested:
                itemlist.extend(self._channel_entries_to_items(nested, source_url, depth + 1))

            item = self._ytdlp_entry_to_item(entry)
            if item:
                itemlist.append(item)
                continue

            candidate = entry.get('url') or entry.get('webpage_url') or ''
            if candidate and candidate != source_url:
                follow_urls.append(candidate)

        if itemlist or depth >= 1:
            return itemlist

        for follow_url in follow_urls[:3]:
            try:
                next_url = self._normalize_channel_url(follow_url)
                next_entries = self._ytdlp_url_entries(next_url)
                itemlist.extend(self._channel_entries_to_items(next_entries, next_url, depth + 1))
            except Exception:
                continue
            if itemlist:
                break

        return itemlist



    def play_video(self, item: str) -> Optional[bool]:
        
        if not item.startswith(self.video_url):
            return None

        video_id = item.split('v=')[-1].split('&')[0]

        try:
            video_info = self._api_get(f'/videos/{video_id}')
        except Exception:
            xbmcgui.Dialog().notification(
                'YouTube', 'Failed to resolve video stream',
                xbmcgui.NOTIFICATION_ERROR, 3000
            )
            return False

       
        stream_url = ''
        best_quality = ''

        
        for stream in video_info.get('formatStreams', []):
            quality = stream.get('qualityLabel', '')
            url = stream.get('url', '')
            if url:
                stream_url = url
                best_quality = quality
                
                if '720' in quality:
                    break

        if not stream_url:
            
            stream_url = f'{self.api_base}/latest_version?id={video_id}&itag=22'

        if not stream_url:
            xbmcgui.Dialog().notification(
                'YouTube', 'No playable stream found',
                xbmcgui.NOTIFICATION_ERROR, 3000
            )
            return False

        title = video_info.get('title', 'YouTube Video')
        author = video_info.get('author', '')
        description = video_info.get('description', '')
        thumbnail = self._best_thumbnail(video_info.get('videoThumbnails', []))
        length = video_info.get('lengthSeconds', 0)

        liz = xbmcgui.ListItem(path=stream_url)
        set_video_info(liz, {
            'title': f'{author} - {title}' if author else title,
            'plot': description,
            'duration': length,
        })
        liz.setArt({
            'thumb': thumbnail,
            'icon': thumbnail,
            'poster': thumbnail,
            'fanart': FANART,
        })

        xbmc.Player().play(stream_url, liz)
        return True

  

    def from_keyboard(self, default_text='', header='Search YouTube'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
