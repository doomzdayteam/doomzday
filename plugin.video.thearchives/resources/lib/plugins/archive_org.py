import sys
import json
import re
from html import unescape
from urllib.parse import quote, unquote, urljoin, urlencode
from typing import List, Optional, Dict
import xbmc
import xbmcgui
from xbmcaddon import Addon
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info
from ..DI import DI

FANART = Addon().getAddonInfo('fanart')


BASE_URL     = 'https://archive.org'
SEARCH_API   = f'{BASE_URL}/advancedsearch.php'
METADATA_API = f'{BASE_URL}/metadata'
DETAILS_URL  = f'{BASE_URL}/details'
DOWNLOAD_URL = f'{BASE_URL}/download'


AUDIO_FORMATS = {
    'mp3', 'ogg', 'flac', 'wav', 'aac', 'm4a', 'wma', 'aiff',
    'vbr mp3', '128kbps mp3', '64kbps mp3',
    'ogg vorbis', 'apple lossless audio', '24bit flac',
}
VIDEO_FORMATS = {
    'mp4', 'mpeg4', 'ogv', 'avi', 'mkv', 'webm', 'mov',
    'h.264', 'h.264 hd', 'h.264 ia', 'mpeg2',
    '512kb mpeg4', '256kb mpeg4', 'cinepack', 'quicktime',
}
AUDIO_EXTS = {
    'mp3', 'ogg', 'oga', 'flac', 'wav', 'aac', 'm4a', 'wma',
    'aiff', 'aif', 'opus',
}
VIDEO_EXTS = {
    'mp4', 'm4v', 'avi', 'mkv', 'webm', 'mov', 'ogv',
    'mpeg', 'mpg', 'm2ts', 'ts',
}


def _file_ext(name):
    if not name or '.' not in name:
        return ''
    return name.rsplit('.', 1)[-1].lower()


def _media_kind(file_info):
    name = file_info.get('name', '')
    fmt = file_info.get('format', '').lower()
    mimetype = file_info.get('mimetype', '').lower()
    ext = _file_ext(name)

    if mimetype.startswith('audio/') or ext in AUDIO_EXTS:
        return 'audio'
    if mimetype.startswith('video/') or ext in VIDEO_EXTS:
        return 'video'
    if fmt in AUDIO_FORMATS or any(fmt.startswith(a) for a in AUDIO_FORMATS):
        return 'audio'
    if fmt in VIDEO_FORMATS or any(fmt.startswith(v) for v in VIDEO_FORMATS):
        return 'video'
    return None


def _with_kodi_headers(url, user_agent, referer):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer, safe="")}'
    )


def _identifier_from_url(url, prefix):
    return unquote(url.replace(prefix + '/', '').split('/')[0])


class ArchiveOrg(Plugin):
    name = "archive_org"
    priority = 1050


    def __init__(self):
        self.session = DI.session
        self.base_url = 'https://archive.org'
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        )
        self.session.headers = {
            "User-Agent": self.user_agent,
            "Referer": self.base_url,
            "Accept": "application/json",
        }

       
        self.search_audio_url = f'{self.base_url}/search/audio'
        self.search_video_url = f'{self.base_url}/search/video'
        self.search_all_url   = f'{self.base_url}/search/all'
        self.collection_url   = f'{self.base_url}/collection'
        self.item_url         = f'{self.base_url}/item'
        self.play_url         = f'{self.base_url}/play'

    
    AUDIO_COLLECTIONS = [
        ('audio',             'All Audio'),
        ('etree',             'Live Music Archive'),
        ('librivoxaudio',     'Librivox Free Audio'),
        ('audio_bookspoetry', 'Audio Books & Poetry'),
        ('audio_music',       'Music, Arts & Culture'),
        ('audio_tech',        'Computers, Tech & Science'),
        ('audio_news',        'News & Public Affairs'),
        ('audio_religion',    'Spirituality & Religion'),
        ('podcasts',          'Podcasts'),
        ('oldtimeradio',      'Old Time Radio'),
        ('78rpm',             '78 RPMs & Cylinder Recordings'),
        ('netlabels',         'Netlabels'),
        ('GratefulDead',      'Grateful Dead'),
    ]

    
    VIDEO_COLLECTIONS = [
        ('movies',                 'All Video'),
        ('feature_films',          'Feature Films'),
        ('opensource_movies',      'Community Video'),
        ('animationandcartoons',   'Animation & Cartoons'),
        ('moviesandfilms',         'Movies & Films'),
        ('artsandmusicvideos',     'Arts & Music Videos'),
        ('computersandtechvideos', 'Computers & Technology'),
        ('newsandpublicaffairs',   'News & Public Affairs'),
        ('television',             'Television'),
        ('sports',                 'Sports Videos'),
    ]

    def get_list(self, url):
        
       
        if url in (self.search_audio_url, self.search_video_url, self.search_all_url):
            query = self.from_keyboard()
            if not query:
                sys.exit()

            
            if url == self.search_audio_url:
                mt_filter = ' AND mediatype:audio'
            elif url == self.search_video_url:
                mt_filter = ' AND mediatype:movies'
            else:
                mt_filter = ' AND (mediatype:audio OR mediatype:movies)'

            search_q = f'{query}{mt_filter}'
            fields = '&'.join([
                f'fl[]={f}' for f in
                ['identifier', 'title', 'mediatype', 'creator',
                 'description', 'downloads', 'date', 'collection']
            ])
            api_url = (
                f'{SEARCH_API}?q={quote(search_q)}'
                f'&output=json&rows=50&page=1'
                f'&sort[]=downloads+desc&{fields}'
            )
            response = self.session.get(api_url)
            return response.text

       
        if url.startswith(self.collection_url + '/'):
            parts = url.replace(self.collection_url + '/', '').split('/')
            coll_id = parts[0]
            page = int(parts[1]) if len(parts) > 1 else 1
            fields = '&'.join([
                f'fl[]={f}' for f in
                ['identifier', 'title', 'mediatype', 'creator',
                 'description', 'downloads', 'date']
            ])
            api_url = (
                f'{SEARCH_API}?q=collection:{quote(coll_id)}'
                f'&output=json&rows=50&page={page}'
                f'&sort[]=downloads+desc&{fields}'
            )
            response = self.session.get(api_url)
            return response.text

       
        if url.startswith(self.item_url + '/'):
            identifier = _identifier_from_url(url, self.item_url)
            api_url = f'{METADATA_API}/{identifier}'
            response = self.session.get(api_url)
            return response.text

        if url.startswith(DETAILS_URL + '/'):
            identifier = _identifier_from_url(url, DETAILS_URL)
            api_url = f'{METADATA_API}/{identifier}'
            response = self.session.get(api_url)
            return response.text

        if url.startswith(METADATA_API + '/'):
            response = self.session.get(url)
            return response.text

      
        return None

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        
        if not url.startswith(self.base_url):
            return None

        itemlist = []

       
        if url == self.base_url:
            
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Audio[/COLOR]',
                'link': self.search_audio_url
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search Video[/COLOR]',
                'link': self.search_video_url
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR deepskyblue]Search All[/COLOR]',
                'link': self.search_all_url
            })

            
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── Audio Collections ──[/COLOR]',
                'link': self.base_url  
            })
            for coll_id, coll_name in self.AUDIO_COLLECTIONS:
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR limegreen]♫[/COLOR] {coll_name}',
                    'link': f'{self.collection_url}/{coll_id}',
                    'thumbnail': f'{BASE_URL}/services/img/{coll_id}',
                })

            
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── Video Collections ──[/COLOR]',
                'link': self.base_url
            })
            for coll_id, coll_name in self.VIDEO_COLLECTIONS:
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR red]▶[/COLOR] {coll_name}',
                    'link': f'{self.collection_url}/{coll_id}',
                    'thumbnail': f'{BASE_URL}/services/img/{coll_id}',
                })

            return itemlist

       
        if (url.startswith(SEARCH_API) or
            url.startswith(self.search_audio_url) or
            url.startswith(self.search_video_url) or
            url.startswith(self.search_all_url) or
            url.startswith(self.collection_url + '/')):

            try:
                data = json.loads(response)
            except (json.JSONDecodeError, TypeError):
                return itemlist

            docs = data.get('response', {}).get('docs', [])
            total = data.get('response', {}).get('numFound', 0)

            for doc in docs:
                identifier = doc.get('identifier', '')
                title = doc.get('title', 'Untitled')
                mediatype = doc.get('mediatype', '')
                creator = doc.get('creator', '')
                downloads = doc.get('downloads', 0)
                date = doc.get('date', '')
                description = doc.get('description', '')

                if isinstance(creator, list):
                    creator = ', '.join(creator)
                if isinstance(description, list):
                    description = ' '.join(description)
                description = re.sub(r'<[^>]+>', '', str(description))[:300]

                
                if mediatype == 'audio':
                    type_tag = '[COLOR limegreen]♫[/COLOR]'
                elif mediatype == 'movies':
                    type_tag = '[COLOR red]▶[/COLOR]'
                elif mediatype == 'collection':
                    type_tag = '[COLOR deepskyblue]Collection[/COLOR]'
                else:
                    type_tag = '[COLOR grey]◆[/COLOR]'

                
                try:
                    dl_str = f'{int(downloads):,}'
                except (ValueError, TypeError):
                    dl_str = '0'

                display_title = f'{type_tag} {title}'
                if creator:
                    display_title += f' [COLOR grey]- {creator}[/COLOR]'

                thumbnail = f'{BASE_URL}/services/img/{identifier}'

                year = str(date)[:4] if date else ''
                summary_parts = []
                if year:
                    summary_parts.append(year)
                summary_parts.append(f'Downloads: {dl_str}')
                if description:
                    summary_parts.append(description[:200])
                summary = ' | '.join(summary_parts)

                item_link = (
                    f'{self.collection_url}/{identifier}'
                    if mediatype == 'collection'
                    else f'{self.item_url}/{identifier}'
                )

                itemlist.append({
                    'type': 'dir',
                    'title': display_title,
                    'link': item_link,
                    'thumbnail': thumbnail,
                    'summary': summary,
                })

           
            if url.startswith(self.collection_url + '/'):
                parts = url.replace(self.collection_url + '/', '').split('/')
                coll_id = parts[0]
                current_page = int(parts[1]) if len(parts) > 1 else 1
                total_pages = (total + 49) // 50

                if current_page < total_pages:
                    itemlist.append({
                        'type': 'dir',
                        'title': f'[COLOR deepskyblue]Next Page ({current_page + 1}/{total_pages}) →[/COLOR]',
                        'link': f'{self.collection_url}/{coll_id}/{current_page + 1}',
                    })

            return itemlist

       
        if (url.startswith(self.item_url + '/') or
            url.startswith(DETAILS_URL + '/') or
            url.startswith(METADATA_API + '/')):
            if url.startswith(self.item_url + '/'):
                identifier = _identifier_from_url(url, self.item_url)
            elif url.startswith(DETAILS_URL + '/'):
                identifier = _identifier_from_url(url, DETAILS_URL)
            else:
                identifier = _identifier_from_url(url, METADATA_API)

            try:
                data = json.loads(response)
            except (json.JSONDecodeError, TypeError):
                return itemlist

            metadata = data.get('metadata', {})
            files = data.get('files', [])

            item_title = metadata.get('title', 'Untitled')
            item_creator = metadata.get('creator', '')
            item_description = metadata.get('description', '')
            item_date = metadata.get('date', '')

            if isinstance(item_creator, list):
                item_creator = ', '.join(item_creator)
            if isinstance(item_description, list):
                item_description = ' '.join(item_description)
            item_description = re.sub(r'<[^>]+>', '', str(item_description))[:500]

            thumbnail = f'{BASE_URL}/services/img/{identifier}'

            if metadata.get('mediatype') == 'collection':
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR deepskyblue]Browse Collection: {item_title}[/COLOR]',
                    'link': f'{self.collection_url}/{identifier}',
                    'thumbnail': thumbnail,
                    'summary': item_description,
                })
                return itemlist

            
            audio_files = []
            video_files = []

            for f in files:
                name = f.get('name', '')
                fmt = f.get('format', '').lower()
                size = f.get('size', '0')
                length = f.get('length', '')
                track_title = f.get('title', '')
                source = f.get('source', '')

                kind = _media_kind(f)
                if not kind:
                    continue
                is_audio = kind == 'audio'

               
                if track_title:
                    display = track_title
                else:
                    display = re.sub(r'\.[^.]+$', '', name)

                
                try:
                    size_bytes = int(size)
                    if size_bytes > 1073741824:
                        size_str = f'{size_bytes / 1073741824:.1f} GB'
                    elif size_bytes > 1048576:
                        size_str = f'{size_bytes / 1048576:.1f} MB'
                    elif size_bytes > 1024:
                        size_str = f'{size_bytes / 1024:.1f} KB'
                    else:
                        size_str = f'{size_bytes} B'
                except (ValueError, TypeError):
                    size_str = ''

                
                dur_str = ''
                if length:
                    try:
                        total_secs = float(length)
                        h = int(total_secs // 3600)
                        m = int((total_secs % 3600) // 60)
                        s = int(total_secs % 60)
                        if h:
                            dur_str = f'{h}:{m:02d}:{s:02d}'
                        else:
                            dur_str = f'{m}:{s:02d}'
                    except (ValueError, TypeError):
                        dur_str = ''

                file_format = f.get('format', 'Unknown')
                stream_url = _with_kodi_headers(
                    f'{DOWNLOAD_URL}/{identifier}/{quote(name)}',
                    self.user_agent,
                    f'{DETAILS_URL}/{identifier}'
                )

                info_parts = [file_format]
                if size_str:
                    info_parts.append(size_str)
                if dur_str:
                    info_parts.append(dur_str)
                info_line = ' | '.join(info_parts)

                if is_audio:
                    color_tag = '[COLOR limegreen]♫[/COLOR]'
                    audio_files.append((display, stream_url, info_line, name, file_format, dur_str))
                else:
                    color_tag = '[COLOR red]▶[/COLOR]'
                    video_files.append((display, stream_url, info_line, name, file_format, dur_str))

           
            has_audio = len(audio_files) > 0
            has_video = len(video_files) > 0

            if has_audio and len(audio_files) > 1:
                playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                playlist.clear()
                for display, stream_url, info_line, name, file_format, dur_str in audio_files:
                    liz = xbmcgui.ListItem(f'{item_creator} - {display}' if item_creator else display)
                    set_video_info(liz, {
                        'title': display,
                        'plot': item_description,
                        'year': str(item_date)[:4] if item_date else '',
                    })
                    try:
                        liz.setContentLookup(False)
                    except AttributeError:
                        pass
                    liz.setArt({
                        'thumb': thumbnail,
                        'icon': thumbnail,
                        'poster': thumbnail,
                        'fanart': FANART,
                    })
                    playlist.add(url=stream_url, listitem=liz)

           
            if has_audio:
                if len(audio_files) > 1:
                    itemlist.append({
                        'type': 'item',
                        'title': '[COLOR limegreen]♫ Play All Audio Tracks[/COLOR]',
                        'link': audio_files[0][1],  
                        'thumbnail': thumbnail,
                        'summary': f'{len(audio_files)} audio tracks',
                        'is_playable': 'true',
                    })

                for display, stream_url, info_line, name, file_format, dur_str in audio_files:
                    full_title = f'[COLOR limegreen]♫[/COLOR] {display} [COLOR grey]({info_line})[/COLOR]'
                    itemlist.append({
                        'type': 'item',
                        'title': full_title,
                        'link': stream_url,
                        'thumbnail': thumbnail,
                        'summary': f'{item_creator} | {item_description[:200]}' if item_creator else item_description[:200],
                        'is_playable': 'true',
                    })

            
            if has_video:
                for display, stream_url, info_line, name, file_format, dur_str in video_files:
                    full_title = f'[COLOR red]▶[/COLOR] {display} [COLOR grey]({info_line})[/COLOR]'
                    itemlist.append({
                        'type': 'item',
                        'title': full_title,
                        'link': stream_url,
                        'thumbnail': thumbnail,
                        'summary': f'{item_creator} | {item_description[:200]}' if item_creator else item_description[:200],
                        'is_playable': 'true',
                    })

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No playable audio/video files found[/COLOR]',
                    'link': self.base_url,
                })

            
            if has_audio and len(audio_files) > 1:
                xbmc.Player().play(playlist)

            return itemlist

        return itemlist

    def play_video(self, item: str) -> Optional[bool]:
        
        if not item.startswith(DOWNLOAD_URL):
            return None

        
        liz = xbmcgui.ListItem(path=item)

     
        stream_path = item.split('|', 1)[0]
        ext = _file_ext(stream_path)

        if ext in AUDIO_EXTS:
            set_video_info(liz, {'title': item.split('/')[-1]})
        elif ext in VIDEO_EXTS:
            set_video_info(liz, {'title': item.split('/')[-1]})
            liz.setMimeType(f'video/{ext}')

        liz.setProperty('IsPlayable', 'true')
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(item, liz)
        return True

   
    def from_keyboard(self, default_text='', header='Search Archive.org'):
        
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
