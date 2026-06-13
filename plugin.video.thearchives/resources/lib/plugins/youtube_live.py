import json
from urllib.parse import quote, unquote, urlencode

import requests
import xbmc
import xbmcaddon
import xbmcgui

from ..plugin import Plugin, run_hook
from resources.lib.infotagger.helpers import set_video_info

from .youtube_live_core import (
    DEFAULT_USER_AGENT,
    extract_search_results,
    resolve_live_hls,
)


ADDON = xbmcaddon.Addon()
ADDON_ICON = ADDON.getAddonInfo("icon")
ADDON_FANART = ADDON.getAddonInfo("fanart")

SEARCH_PRESETS = {
    "news": {
        "title": "Live News",
        "prompt": "Search live news",
        "default": "live news",
        "terms": ["news", "breaking news", "world news", "weather news"],
    },
    "sports": {
        "title": "Live Sports",
        "prompt": "Search live sports",
        "default": "live sports",
        "terms": ["sports", "football", "soccer", "basketball", "mma"],
    },
    "gaming": {
        "title": "Live Gaming",
        "prompt": "Search live gaming",
        "default": "live gaming",
        "terms": ["gaming", "gameplay", "esports", "live gaming", "gaming livestream"],
    },
    "custom": {
        "title": "Search YouTube Live",
        "prompt": "Search YouTube live",
        "default": "",
        "terms": [],
    },
}


def _message_item(title, summary=""):
    return {
        "type": "item",
        "title": title,
        "link": "message/%s" % quote(summary or title),
        "thumbnail": ADDON_ICON,
        "fanart": ADDON_FANART,
        "summary": summary or title,
    }


def _best_thumbnail(entry):
    thumbnails = entry.get("thumbnails") or []
    if isinstance(thumbnails, list) and thumbnails:
        for thumb in reversed(thumbnails):
            if isinstance(thumb, dict) and thumb.get("url"):
                return thumb["url"]
    thumbnail = entry.get("thumbnail")
    return thumbnail if isinstance(thumbnail, str) else ADDON_ICON


class YouTubeLive(Plugin):
    name = "youtube_live"
    priority = 180

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    def get_list(self, url):
        if not str(url).startswith("youtube-live://"):
            return None

        path = str(url).replace("youtube-live://", "", 1)
        if path in ("", "root"):
            return json.dumps({"kind": "root"})

        if path.startswith("search/"):
            preset = path.split("/", 1)[1]
            return json.dumps({"kind": "search", "preset": preset, "items": self._search(preset)})

        if path.startswith("live/"):
            preset = path.split("/", 1)[1]
            return json.dumps({"kind": "live", "preset": preset, "items": self._preset_items(preset)})

        return json.dumps({"kind": "message", "title": "YouTube Live", "summary": "Unknown YouTube Live view."})

    def parse_list(self, url, response):
        if not str(url).startswith("youtube-live://"):
            return None

        data = json.loads(response or "{}")
        kind = data.get("kind")

        if kind == "root":
            return self._root_items()
        if kind == "live":
            preset = data.get("preset", "")
            title = SEARCH_PRESETS.get(preset, {}).get("title", "Live Streams")
            return data.get("items") or [_message_item("No %s found" % title.lower(), "Try again later.")]
        if kind == "search":
            return data.get("items") or [_message_item("No live streams found", "Try a different search.")]
        if kind == "message":
            return [_message_item(data.get("title", "YouTube Live"), data.get("summary", ""))]

        return []

    def play_video(self, item):
        try:
            data = json.loads(item)
        except Exception:
            return None

        youtube_url = data.get("youtube_live_url")
        if not youtube_url:
            return None

        manifest = resolve_live_hls(youtube_url, self.session)
        if not manifest:
            xbmcgui.Dialog().notification(
                "YouTube Live",
                "No playable live HLS stream found.",
                xbmcgui.NOTIFICATION_WARNING,
                4000,
            )
            return True

        title = data.get("title") or "YouTube Live"
        thumbnail = data.get("thumbnail") or ADDON_ICON
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": "https://www.youtube.com/",
        }
        list_item = xbmcgui.ListItem(title)
        list_item.setProperty("IsPlayable", "true")
        list_item.setArt({"thumb": thumbnail, "icon": thumbnail, "fanart": data.get("fanart", ADDON_FANART)})
        set_video_info(list_item, {"title": title, "plot": data.get("summary", "")})
        list_item.setProperty("inputstream", "inputstream.ffmpegdirect")
        list_item.setProperty("inputstream.ffmpegdirect.manifest_type", "hls")
        list_item.setProperty("inputstream.ffmpegdirect.stream_headers", urlencode(headers))
        list_item.setMimeType("application/x-mpegURL")
        try:
            list_item.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(manifest, list_item)
        return True

    def _root_items(self):
        return [
            {
                "type": "dir",
                "title": "Live News",
                "link": "youtube-live://live/news",
                "thumbnail": ADDON_ICON,
                "fanart": ADDON_FANART,
                "summary": "Browse active YouTube news live streams.",
            },
            {
                "type": "dir",
                "title": "Live Sports",
                "link": "youtube-live://live/sports",
                "thumbnail": ADDON_ICON,
                "fanart": ADDON_FANART,
                "summary": "Browse active YouTube sports live streams.",
            },
            {
                "type": "dir",
                "title": "Live Gaming",
                "link": "youtube-live://live/gaming",
                "thumbnail": ADDON_ICON,
                "fanart": ADDON_FANART,
                "summary": "Browse active YouTube gaming live streams.",
            },
            {
                "type": "dir",
                "title": "Search YouTube Live",
                "link": "youtube-live://search/custom",
                "thumbnail": ADDON_ICON,
                "fanart": ADDON_FANART,
                "summary": "Search for any live stream by keyword.",
            },
        ]

    def _youtube_items_for_query(self, query, empty_title="No live streams found"):
        query = query.strip()
        if "live" not in query.lower():
            query = "live %s" % query

        try:
            params = urlencode({
                "search_query": query,
                "sp": "EgJAAQ==",
            })
            response = self.session.get(
                "https://www.youtube.com/results?%s" % params,
                timeout=15,
            )
            response.raise_for_status()
            entries = extract_search_results(response.text)
        except Exception as exc:
            xbmc.log("[TheArchives] YouTube Live search failed: %s" % exc, xbmc.LOGERROR)
            return [_message_item("YouTube Live search failed", str(exc))]

        seen = set()
        items = []
        for entry in entries:
            video_id = entry.get("id")
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            title = entry.get("title") or "YouTube Live"
            url = entry.get("url") or "https://www.youtube.com/watch?v=%s" % video_id
            thumbnail = entry.get("thumbnail") or ADDON_ICON
            items.append({
                "type": "item",
                "title": title,
                "link": "youtube-live-play://%s" % quote(url, safe=""),
                "youtube_live_url": url,
                "thumbnail": thumbnail,
                "fanart": thumbnail,
                "summary": "YouTube Live search result. Playback will resolve a fresh HLS stream.",
            })

        return items or [_message_item(empty_title, query)]

    def _preset_items(self, preset):
        config = SEARCH_PRESETS.get(preset, SEARCH_PRESETS["custom"])
        query = config["default"] or "live"
        return self._youtube_items_for_query(query, "No %s found" % config["title"].lower())

    def _search(self, preset):
        config = SEARCH_PRESETS.get(preset, SEARCH_PRESETS["custom"])
        default = config["default"]
        query = xbmcgui.Dialog().input(config["prompt"], defaultt=default)
        if not query:
            return [_message_item("Search cancelled", "No search was entered.")]

        return self._youtube_items_for_query(query)
