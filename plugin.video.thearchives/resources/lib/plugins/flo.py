import sys
import json
import re
from html import unescape
from urllib.parse import quote, urljoin
from typing import List, Optional, Dict
import xbmc
import xbmcgui
from xbmcaddon import Addon
from bs4 import BeautifulSoup
from ..plugin import Plugin
from ..DI import DI

FANART = Addon().getAddonInfo('fanart')


class Flo(Plugin):
    name = "flo"
    priority = 1100
    
    def __init__(self):
        self.session = DI.session
        self.base_url = 'https://freelistenonline.com'
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
        self.session.headers = {"User-Agent": self.user_agent, "Referer": self.base_url}
        self.genre_url = urljoin(self.base_url, '/tag')
        self.artist_url = urljoin(self.base_url, '/artist')
        self.search_url = f'{self.base_url}/Music/Search'
    
    def get_list(self, url):
        if url != self.search_url:
            return
        query = self.from_keyboard()
        if not query:
            sys.exit()
        url = f'{self.search_url}?q={quote(query)}&type=1'
        response = self.session.get(url)
        return response.text
    
    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not url.startswith(self.base_url):
            return
            
        itemlist = []
        title = ''
        link = ''
        soup = BeautifulSoup(response, 'html.parser')
        if url == self.base_url:
            itemlist.append(
                {
                    'type': 'dir',
                    'title': '[COLOR deepskyblue]Search[/COLOR]',
                    'link': self.search_url
                }
            )
            itemlist.append(
                {
                    'type': 'dir',
                    'title': '[COLOR deepskyblue]Artists[/COLOR]',
                    'link': self.artist_url
                }
            )
            for category in soup.find_all(class_='maintags'):
                title = category.text
                link = urljoin(self.base_url, category['href'])
                
                itemlist.append(
                    {
                        'type': 'dir',
                        'title': title,
                        'link': link
                    }
                )
        
        elif url.startswith(self.search_url): 
            main_artist = soup.find(class_='artist_photo')
            title = main_artist.div.img['alt']
            link = urljoin(self.base_url, main_artist.a['href'])
            thumbnail = urljoin(self.base_url, main_artist.div.img['src'])
            itemlist.append(
                {
                    'type': 'dir',
                    'title': title,
                    'link': link,
                    'thumbnail': thumbnail
                }
            )
            
            more_artists = soup.find_all(class_='col-md-2 more_artis_results')
            for artist in more_artists:
                title = artist.div.div.a.img['alt']
                link = urljoin(self.base_url, artist.div.div.a['href'])
                thumbnail = urljoin(self.base_url, artist.div.div.a.img['src'])
                itemlist.append(
                    {
                        'type': 'dir',
                        'title': title,
                        'link': link,
                        'thumbnail': thumbnail
                    }
                )
            tracks = soup.find_all(class_='border-bottom')
            for track in tracks:
                match = re.findall("TrackTableClick\((.+?), '(.+?)', '(.+?)'\)", str(track))
                if not match:
                    continue
                for track_id, track_title, artist in match:
                    title = f'{artist} - {track_title}'
                    link = f'{self.base_url}/music/vkstream/{track_id}'
                    itemlist.append(
                        {
                            'type': 'item',
                            'title': title,
                            'link': link
                        }
                    )
        
        elif url == self.artist_url or url.startswith(self.genre_url):
            artist_list = soup.find(class_='list-inline artists_list')
            for li in artist_list.find_all('li'):
                title = li.strong.a.text
                link = urljoin(self.base_url, li.a['href'])
                thumbnail = urljoin(self.base_url, li.a.img['src'])
                itemlist.append(
                    {
                        'type': 'dir',
                        'title': title,
                        'link': link,
                        'thumbnail': thumbnail
                    }
                )
            
        elif url.startswith(self.artist_url):
            tracks = json.loads(soup.find('script').text)
            name = unescape(tracks['name'])
            thumbnail = urljoin(self.base_url, tracks['image'][0])
            artist_id = thumbnail.split('/')[-1].rstrip('.png')
            summary = unescape(tracks['description'])
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            playlist.clear()
            
            if str.isdecimal(artist_id):
                tracks = self.session.post(f'{self.base_url}/Music/ReturnTrackTable?sEcho=1&iDisplayStart=0&iDisplayLength=1000&idSource={artist_id}').json()['aaData']
                for track in tracks:
                    title = f"{name} - {unescape(track['Name'])}"
                    track_id = track['Id']
                    link = f'{self.base_url}/music/vkstream/{track_id}'
                    liz = xbmcgui.ListItem(title)
                    liz.setInfo('audio', {'title': title, 'plot': summary})
                    liz.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail, 'fanart': FANART})
                    playlist.add(url=link, listitem=liz)
                    itemlist.append(
                        {
                            'type': 'item',
                            'title': title,
                            'link': link,
                            'thumbnail': thumbnail,
                            'summary': summary,
                            'is_playable': 'true'
                        }
                    )
            
            else:
                for track in tracks['track']:
                    title = f"{name} - {unescape(track['name'])}"
                    track_id = track['audio'].split('#Play')[-1]
                    link = f'{self.base_url}/music/vkstream/{track_id}'
                    liz = xbmcgui.ListItem(title)
                    liz.setInfo('audio', {'title': title, 'plot': summary})
                    liz.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail, 'fanart': FANART})
                    playlist.add(url=link, listitem=liz)
                    itemlist.append(
                        {
                            'type': 'item',
                            'title': title,
                            'link': link,
                            'thumbnail': thumbnail,
                            'summary': summary,
                            'is_playable': 'true'
                        }
                    )
            xbmc.Player().play(playlist)
        return itemlist
            

    def play_video(self, item: str) -> Optional[bool]:
        pass
    
    def from_keyboard(self, default_text='', header='Search'):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if (kb.isConfirmed()):
            return kb.getText()
        return None
