import json
import re
import xbmc
import xbmcgui
from ..plugin import Plugin, run_hook
from ..DI import DI
# from ..external import yt_dlp


class youtube(Plugin):
    name = "youtube"
    priority = 120
    
    
    def get_list(self, url):
        if "youtube.com" in url or 'plugin.video.youtube' in url :
            from ..external import yt_dlp
            url = swap_link(url)
            params = {
                'quiet': True,
                'noplaylist': False
            }
            
            ydl = yt_dlp.YoutubeDL(params)
            playlist_info = ydl.extract_info(url, download=False, process=False)
            
            items = []
            
            for video_info in playlist_info['entries']:
                try:
                    if 'entries' in video_info:
                        for entry in video_info['entries']:
                            try:
                                item = self.create_item(entry)
                                items.append(item)
                            except:
                                continue
                    else:
                        item = self.create_item(video_info)
                        if item:
                            items.append(item)
                except:
                    continue
            return json.dumps({'items': items})
    
    def create_item(self, video_info: dict):
        title = video_info['title']
        if '[Private video]' in title or '[Deleted video]' in title:
            return None
        video_id = video_info['id']
        link = f'https://www.youtube.com/watch?v={video_id}'
        thumbnail = video_info['thumbnails'][-1]['url']
        item = {
            'type': 'item',
            'title': title,
            'link': link,
            'thumbnail': thumbnail,
            'summary': title
        }
        return item
    
    def process_item(self, item):
        if 'ytdlp' in item:
            option = item['ytdlp']
            if option == "search":
                item["link"] = "ytdlp/search"
                item["is_dir"] = True
                list_item = xbmcgui.ListItem(item.get("title", item.get("name", "")))
            else:
                item["link"] = f"ytdlp/play/{option}"
                item["is_dir"] = False
                list_item = xbmcgui.ListItem(item.get("title", item.get("name", "")))
                list_item.setArt({"thumb": item.get("thumbnail"), "fanart": item.get("fanart")})
            item["list_item"] = list_item
            return item
        
    def play_video(self, item):
        item = json.loads(item)
        if 'ytdlp' in item:
            xbmc.executebuiltin(f"RunPlugin(plugin://plugin.video.youtube/play/?video_id={item['ytdlp']})")
            return True
        if "link" not in item: return
        link = item["link"]
        if isinstance(link, list) and len(link) > 0: link = link[0]
        link2 = swap_link(link)  
        r = re.findall(r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})", link2)
        if r:
            link = f"plugin://plugin.video.youtube/play/?video_id={r[0]}"
            xbmc.Player().play(link)
            return True
    
    def routes(self, plugin):
        @plugin.route("/ytdlp/search")
        def search():
            query = xbmcgui.Dialog().input("Search")
            if query == "": return
            from ..external import yt_dlp
            with yt_dlp.YoutubeDL({"noplaylist": True, "extract_flat": "in_playlist", "quiet": True}) as ydl:
                info = ydl.extract_info("ytsearch50:" + query, download=False)
            jen_list = [{
                "title": entry["title"],
                "thumbnail": entry["thumbnails"][0]["url"],
                "fanart": entry["thumbnails"][0]["url"],
                "ytdlp": entry["id"],
                "type": "item"
            } for entry in info["entries"]]
            
            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list]
            run_hook("display_list", jen_list)

        @plugin.route("/ytdlp/play/<path:yt_id>")
        def play(yt_id):
            link = f"plugin://plugin.video.youtube/play/?video_id={yt_id}"
            xbmc.Player().play(link)

#####
def swap_link(link) :
    if 'youtube.com/playlist?list=' in link:
        return link
    elif 'youtube.com/playlist_list=' in link:
        return link.replace('playlist_list', 'playlist?list')
    pl_base = 'https://www.youtube.com/playlist?list='
    ch_base1 = 'https://www.youtube.com/channel/'
    ch_base2 = 'https://www.youtube.com/'
    vid_base = 'https://www.youtube.com/watch?v=' 
    link = link.rstrip('/')
    splitted = link.split('/')
    if 'plugin.video.youtube/playlist' in link :
        new_link = pl_base + link.split('/')[-1]
        
    elif 'plugin.video.youtube/channel' in link :
        channel_id = splitted[-1]
        if channel_id.startswith('@'):
            new_link = ch_base2 + channel_id
        else:
            new_link = ch_base1 + channel_id
        
    elif 'plugin.video.youtube/watch' in link :   
        new_link = vid_base + link.split('=')[-1]
        
    elif 'youtube.com/watch' in link :   
        new_link = vid_base + link.split('=')[-1]

    else :
        new_link = link
  
    return new_link
    
