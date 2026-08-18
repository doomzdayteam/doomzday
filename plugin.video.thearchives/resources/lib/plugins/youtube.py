import json
import re
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen
import xbmc
import xbmcgui
import xbmcaddon
from ..plugin import Plugin


INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://vid.puffyan.us",
    "https://invidious.fdn.fr",
    "https://inv.tux.pizza",
    "https://invidious.nerdvpn.de",
]

YOUTUBE_ADDON_ID = "plugin.video.youtube"


def extract_video_id(video_info):
    values = [
        video_info.get("id"),
        video_info.get("url"),
        video_info.get("webpage_url"),
        video_info.get("original_url"),
    ]
    for value in values:
        if not value:
            continue
        value = str(value)
        if re.fullmatch(r"[^\"&?/\s]{11}", value):
            return value
        match = re.search(r"(?:youtube\.com/(?:watch\?v=|embed/|live/)|youtu\.be/)([^\"&?/\s]{11})", value)
        if match:
            return match.group(1)
        parsed = urlparse(value)
        query_id = parse_qs(parsed.query).get("v", [""])[0]
        if re.fullmatch(r"[^\"&?/\s]{11}", query_id):
            return query_id
    return None


def best_thumbnail(video_info, video_id):
    thumbnail = video_info.get("thumbnail")
    if thumbnail:
        return thumbnail
    thumbnails = video_info.get("thumbnails") or []
    if isinstance(thumbnails, list):
        for entry in reversed(thumbnails):
            if isinstance(entry, dict) and entry.get("url"):
                return entry["url"]
    if video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return ""


def best_invidious_thumbnail(video):
    thumbnails = video.get("videoThumbnails") or []
    if isinstance(thumbnails, list):
        preferred = ("maxres", "maxresdefault", "high", "medium", "default")
        for quality in preferred:
            for thumbnail in thumbnails:
                if (
                    isinstance(thumbnail, dict)
                    and thumbnail.get("quality") == quality
                    and thumbnail.get("url")
                ):
                    return thumbnail["url"]
        for thumbnail in reversed(thumbnails):
            if isinstance(thumbnail, dict) and thumbnail.get("url"):
                return thumbnail["url"]
    video_id = video.get("videoId") or video.get("id")
    if video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return ""


def iter_playlist_entries(entries):
    for video_info in entries or []:
        if not isinstance(video_info, dict):
            continue
        nested = video_info.get("entries")
        if nested:
            for entry in iter_playlist_entries(nested):
                yield entry
        else:
            yield video_info


def extract_playlist_id(url):
    url = swap_link(str(url or ""))
    parsed = urlparse(url)
    playlist_id = parse_qs(parsed.query).get("list", [""])[0]
    if playlist_id:
        return playlist_id
    if "plugin.video.youtube/playlist" in url:
        return url.rstrip("/").split("/")[-1]
    return ""


def invidious_playlist_items(playlist_id):
    if not playlist_id:
        return []
    for instance in INVIDIOUS_INSTANCES:
        try:
            request = Request(
                f"{instance}/api/v1/playlists/{playlist_id}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8", "replace"))
        except Exception:
            continue

        author = data.get("author") or ""
        items = []
        for video in data.get("videos") or []:
            video_id = video.get("videoId") or video.get("id")
            if not video_id:
                continue
            title = video.get("title") or "YouTube Video"
            display_title = f"{author} - {title}" if author else title
            items.append({
                "type": "item",
                "title": display_title,
                "link": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": best_invidious_thumbnail(video),
                "summary": display_title,
            })
        if items:
            xbmc.log(f"[TheArchives] Loaded YouTube playlist {playlist_id} via {instance}", getattr(xbmc, "LOGINFO", 1))
            return items
    return []


def youtube_plugin_url(value):
    video_id = extract_video_id({"url": str(value or "")})
    if not video_id:
        return ""
    return "plugin://{}/play/?video_id={}".format(YOUTUBE_ADDON_ID, quote(video_id))


def youtube_addon_available():
    try:
        xbmcaddon.Addon(YOUTUBE_ADDON_ID)
        return True
    except RuntimeError:
        return False


def play_youtube(value, item=None):
    plugin_url = youtube_plugin_url(value)
    if not plugin_url:
        return None
    if not youtube_addon_available():
        xbmcgui.Dialog().notification(
            "The Archives",
            "Install the YouTube add-on to play this video.",
            getattr(xbmcgui, "NOTIFICATION_ERROR", ""),
            5000,
        )
        return True
    xbmc.log("[TheArchives] Opening YouTube video with {}".format(YOUTUBE_ADDON_ID), getattr(xbmc, "LOGINFO", 1))
    xbmc.executebuiltin("RunPlugin({})".format(plugin_url))
    return True


def open_youtube_addon():
    if not youtube_addon_available():
        xbmcgui.Dialog().notification(
            "The Archives",
            "Install the YouTube add-on to use YouTube search.",
            getattr(xbmcgui, "NOTIFICATION_ERROR", ""),
            5000,
        )
        return True
    xbmc.executebuiltin("RunPlugin(plugin://{}/)".format(YOUTUBE_ADDON_ID))
    return True


class youtube(Plugin):
    name = "youtube"
    priority = 120
    
    
    def get_list(self, url):
        if "youtube.com" in url or "plugin.video.youtube" in url:
            items = invidious_playlist_items(extract_playlist_id(url))
            if items:
                return json.dumps({"items": items})
            xbmc.log("[TheArchives] YouTube playlist could not be loaded from Invidious", getattr(xbmc, "LOGWARNING", 2))
            return json.dumps({"items": []})
    
    def create_item(self, video_info: dict):
        title = video_info.get("title") or video_info.get("fulltitle") or "YouTube Video"
        if '[Private video]' in title or '[Deleted video]' in title:
            return None
        video_id = extract_video_id(video_info)
        if not video_id:
            return None
        link = f'https://www.youtube.com/watch?v={video_id}'
        thumbnail = best_thumbnail(video_info, video_id)
        item = {
            'type': 'item',
            'title': title,
            'link': link,
            'thumbnail': thumbnail,
            'summary': title
        }
        return item
    
    def process_item(self, item):
        return None

    def play_video(self, item):
        item = json.loads(item)
        if "link" not in item: return
        link = item["link"]
        if isinstance(link, list) and len(link) > 0: link = link[0]
        link2 = swap_link(link)  
        r = re.findall(r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})", link2)
        if r:
            return play_youtube(link2, item)
    
    def routes(self, plugin):
        @plugin.route("/youtube/search")
        def search():
            open_youtube_addon()

        @plugin.route("/youtube/play/<path:yt_id>")
        def play(yt_id):
            play_youtube(yt_id)

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
    
