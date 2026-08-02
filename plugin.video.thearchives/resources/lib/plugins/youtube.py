import json
import os
import re
import sys
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
import xbmc
import xbmcgui
import xbmcvfs
from xbmcaddon import Addon
from ..plugin import Plugin, run_hook
from ..DI import DI


INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://vid.puffyan.us",
    "https://invidious.fdn.fr",
    "https://inv.tux.pizza",
    "https://invidious.nerdvpn.de",
]


def load_ytdlp():
    external_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "external"))
    if external_path not in sys.path:
        sys.path.insert(0, external_path)
    import yt_dlp
    return yt_dlp


def ytdlp_cache_dir():
    addon_id = Addon().getAddonInfo("id") or "plugin.video.thearchives"
    special_path = f"special://profile/addon_data/{addon_id}/yt-dlp-cache"
    try:
        if hasattr(xbmcvfs, "mkdirs"):
            xbmcvfs.mkdirs(special_path)
        else:
            xbmcvfs.mkdir(special_path)
    except Exception:
        pass

    cache_path = xbmcvfs.translatePath(special_path)
    if isinstance(cache_path, bytes):
        cache_path = cache_path.decode("utf-8")

    try:
        os.makedirs(cache_path, exist_ok=True)
    except Exception as exc:
        xbmc.log(f"[TheArchives] yt-dlp cache directory unavailable: {exc}", getattr(xbmc, "LOGWARNING", 2))
        return False

    return cache_path


def ytdlp_params(extra=None):
    params = {
        "quiet": True,
        "no_warnings": True,
        "cachedir": ytdlp_cache_dir(),
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb"],
                "player_skip": ["configs"],
                "skip": ["authcheck"],
            },
            "youtubetab": {
                "skip": ["authcheck"],
            },
        },
    }
    if extra:
        params.update(extra)
    return params


def make_youtube_url(value):
    value = value.strip()
    if re.fullmatch(r"[^\"&?/\s]{11}", value):
        return f"https://www.youtube.com/watch?v={value}"
    return swap_link(value)


def make_kodi_stream_url(url, headers=None):
    if not headers:
        return url
    return f"{url}|{urlencode(headers)}"


def make_inputstream_headers(headers=None):
    if not headers:
        return ""
    return "&".join(f"{key}={value}" for key, value in headers.items())


def is_hls_format(stream):
    protocol = stream.get("protocol") or ""
    url = stream.get("url") or ""
    return protocol.startswith("m3u8") or ".m3u8" in url


def has_audio_and_video(stream):
    return (
        stream.get("url")
        and stream.get("vcodec") != "none"
        and stream.get("acodec") != "none"
    )


def select_highest(streams):
    return max(streams, key=lambda stream: stream.get("height") or 0)


def select_playable_format(info):
    formats = [stream for stream in info.get("formats", []) if has_audio_and_video(stream)]
    progressive = [
        stream for stream in formats
        if not is_hls_format(stream) and stream.get("protocol") in (None, "http", "https")
    ]
    if progressive:
        return select_highest(progressive)
    hls = [stream for stream in formats if is_hls_format(stream)]
    if hls:
        return select_highest(hls)
    if info.get("url"):
        return info
    raise ValueError("yt-dlp did not return a playable audio/video stream URL")


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


def configure_youtube_list_item(list_item, stream_info, headers=None):
    if is_hls_format(stream_info):
        list_item.setProperty("inputstream", "inputstream.ffmpegdirect")
        list_item.setProperty("inputstream.ffmpegdirect.manifest_type", "hls")
        stream_headers = make_inputstream_headers(headers)
        if stream_headers:
            list_item.setProperty("inputstream.ffmpegdirect.stream_headers", stream_headers)
        list_item.setMimeType("application/x-mpegURL")


def resolve_youtube_stream(value):
    yt_dlp = load_ytdlp()
    params = ytdlp_params({
        "noplaylist": True,
        "ignore_no_formats_error": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["all"],
                "skip": ["authcheck"],
            },
        },
    })
    with yt_dlp.YoutubeDL(params) as ydl:
        info = ydl.extract_info(make_youtube_url(value), download=False)
    if "entries" in info and info["entries"]:
        info = info["entries"][0]
    stream_info = select_playable_format(info)
    headers = stream_info.get("http_headers") or info.get("http_headers")
    if is_hls_format(stream_info):
        return info, stream_info, stream_info["url"], headers
    return info, stream_info, make_kodi_stream_url(stream_info["url"], headers), headers


def play_youtube(value, item=None):
    info, stream_info, stream_url, headers = resolve_youtube_stream(value)
    title = (item or {}).get("title") or info.get("title") or "YouTube"
    list_item = xbmcgui.ListItem(title)
    thumbnail = (item or {}).get("thumbnail") or info.get("thumbnail")
    if thumbnail:
        list_item.setArt({"thumb": thumbnail, "fanart": (item or {}).get("fanart", thumbnail)})
    from resources.lib.infotagger.helpers import set_video_info
    set_video_info(list_item, {"title": title})
    configure_youtube_list_item(list_item, stream_info, headers)
    xbmc.Player().play(stream_url, list_item)
    return True


class youtube(Plugin):
    name = "youtube"
    priority = 120
    
    
    def get_list(self, url):
        if "youtube.com" in url or 'plugin.video.youtube' in url :
            yt_dlp = load_ytdlp()
            url = swap_link(url)
            params = ytdlp_params({
                "noplaylist": False,
                "extract_flat": "in_playlist",
                "ignoreerrors": True,
            })
            
            with yt_dlp.YoutubeDL(params) as ydl:
                playlist_info = ydl.extract_info(url, download=False)
            
            items = []
            
            playlist_entries = list(iter_playlist_entries(playlist_info.get("entries")))
            if not playlist_entries:
                fallback_items = invidious_playlist_items(extract_playlist_id(url))
                if fallback_items:
                    return json.dumps({"items": fallback_items})

            for video_info in playlist_entries:
                try:
                    item = self.create_item(video_info)
                    if item:
                        items.append(item)
                except Exception as exc:
                    xbmc.log(f"[TheArchives] Skipping YouTube playlist entry: {exc}", getattr(xbmc, "LOGWARNING", 2))
                    continue
            return json.dumps({'items': items})
    
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
            return play_youtube(item['ytdlp'], item)
        if "link" not in item: return
        link = item["link"]
        if isinstance(link, list) and len(link) > 0: link = link[0]
        link2 = swap_link(link)  
        r = re.findall(r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})", link2)
        if r:
            return play_youtube(link2, item)
    
    def routes(self, plugin):
        @plugin.route("/ytdlp/search")
        def search():
            query = xbmcgui.Dialog().input("Search")
            if query == "": return
            yt_dlp = load_ytdlp()
            with yt_dlp.YoutubeDL(ytdlp_params({"noplaylist": True, "extract_flat": "in_playlist"})) as ydl:
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
    
