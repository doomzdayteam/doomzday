import base64
import gzip
import json
import re
import sys
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://famelack.com/tv"
ROUTE_BASE = "https://famelack.com/_thearchives_famelack"
DATA_ROOT = "https://raw.githubusercontent.com/famelack/famelack-data/main/tv/compressed"
COUNTRIES_METADATA_URL = f"{DATA_ROOT}/countries_metadata.json"
THUMBNAIL = "resources/media/live_tv.png"
FANART = Addon().getAddonInfo("fanart")

CATEGORIES = [
    ("All Channels", "all"),
    ("Top News", "top-news"),
    ("News", "news"),
    ("Music", "music"),
    ("Sports", "sports"),
    ("Auto", "auto"),
    ("Animation", "animation"),
    ("Business", "business"),
    ("Classic", "classic"),
    ("Comedy", "comedy"),
    ("Cooking", "cooking"),
    ("Culture", "culture"),
    ("Documentary", "documentary"),
    ("Education", "education"),
    ("Entertainment", "entertainment"),
    ("Family", "family"),
    ("General", "general"),
    ("Kids", "kids"),
    ("Legislative", "legislative"),
    ("Lifestyle", "lifestyle"),
    ("Movies", "movies"),
    ("Outdoor", "outdoor"),
    ("Relax", "relax"),
    ("Religious", "religious"),
    ("Series", "series"),
    ("Science", "science"),
    ("Shop", "shop"),
    ("Travel", "travel"),
    ("Weather", "weather"),
]


def _decode_json_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        payload = payload.encode("latin-1")
    if not isinstance(payload, (bytes, bytearray)):
        return None
    raw = bytes(payload)
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()


def _country_data_url(code: str) -> str:
    return f"{DATA_ROOT}/countries/{quote(str(code).lower(), safe='')}.json"


def _category_data_url(slug: str) -> str:
    return f"{DATA_ROOT}/categories/{quote(str(slug).lower(), safe='')}.json"


def _country_route(code: str) -> str:
    return f"{ROUTE_BASE}/country/{quote(str(code).lower(), safe='')}"


def _category_route(slug: str) -> str:
    return f"{ROUTE_BASE}/category/{quote(str(slug).lower(), safe='')}"


def _route_parts(url: str) -> List[str]:
    if not isinstance(url, str) or not url.startswith(ROUTE_BASE + "/"):
        return []
    path = urlparse(url).path
    prefix = urlparse(ROUTE_BASE).path.rstrip("/") + "/"
    if not path.startswith(prefix):
        return []
    return [unquote(part) for part in path[len(prefix):].split("/") if part]


def _play_url(source_url: str, title: str, summary: str = "") -> str:
    return "famelack://play?" + urlencode({
        "source": source_url,
        "title": title,
        "summary": summary,
    })


def _decode_play_url(url: str) -> Dict[str, str]:
    if not isinstance(url, str) or not url.startswith("famelack://play?"):
        return {}
    values = parse_qs(urlparse(url).query)
    return {key: entries[0] for key, entries in values.items() if entries}


def _kodi_header_query(user_agent: str, referer: str = BASE_URL) -> str:
    return urlencode({"User-Agent": user_agent, "Referer": referer})


def _with_kodi_headers(url: str, user_agent: str, referer: str = BASE_URL) -> str:
    return f"{url}|{_kodi_header_query(user_agent, referer)}"


def _build_list_item(item: Dict[str, str], user_agent: str) -> xbmcgui.ListItem:
    title = item.get("title") or "Famelack TV"
    source = item.get("source", "")
    playback_url = _with_kodi_headers(source, user_agent)
    list_item = xbmcgui.ListItem(title, path=playback_url)
    set_video_info(list_item, {"title": title, "plot": item.get("summary", "")})
    thumbnail = item.get("thumbnail", "")
    if thumbnail:
        list_item.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail, "fanart": FANART})
    list_item.setProperty("IsPlayable", "true")
    if ".m3u8" in urlparse(source).path.lower():
        list_item.setMimeType("application/vnd.apple.mpegurl")
        try:
            list_item.setProperty("inputstream", "inputstream.ffmpegdirect")
            list_item.setProperty("inputstream.ffmpegdirect.is_realtime_stream", "true")
            list_item.setProperty("inputstream.ffmpegdirect.manifest_type", "hls")
            list_item.setProperty(
                "inputstream.ffmpegdirect.stream_headers",
                _kodi_header_query(user_agent),
            )
            list_item.setContentLookup(False)
        except AttributeError:
            pass
    return list_item


def _valid_http_url(url: Any) -> bool:
    parsed = urlparse(str(url or ""))
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _normalize_youtube_url(url: Any) -> str:
    if not _valid_http_url(url):
        return ""
    parsed = urlparse(str(url))
    host = parsed.netloc.lower().split(":", 1)[0]
    video_id = ""
    if host in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.strip("/").split("/", 1)[0]
    elif host in (
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    ):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/embed/", "/live/", "/shorts/")):
            video_id = parsed.path.strip("/").split("/", 1)[1].split("/", 1)[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id or ""):
        return ""
    return f"https://www.youtube.com/watch?v={video_id}"


def _channel_route(channel: Dict[str, Any]) -> str:
    raw = json.dumps(channel, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{ROUTE_BASE}/channel/{token}"


def _decode_channel_route(url: str) -> Dict[str, Any]:
    prefix = f"{ROUTE_BASE}/channel/"
    if not isinstance(url, str) or not url.startswith(prefix):
        return {}
    token = url[len(prefix):].split("/", 1)[0]
    token += "=" * (-len(token) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8"))
    except (TypeError, ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _response_payload(response: Any) -> Any:
    content = getattr(response, "content", None)
    if isinstance(content, (bytes, bytearray)) and content:
        return content
    return getattr(response, "text", "")


class FamelackTV(Plugin):
    name = "famelack_tv"
    priority = 1059

    def __init__(self):
        self.session = DI.session
        self.base_url = "https://famelack.com"
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.user_agent,
            "Referer": "https://famelack.com/tv",
            "Accept": "application/json,text/plain,*/*",
        }
        if self.session:
            self.session.headers = self.headers
        self.search_url = f"{ROUTE_BASE}/search"
        self.countries_url = f"{ROUTE_BASE}/countries"
        self.categories_url = f"{ROUTE_BASE}/categories"

    def get_list(self, url: str) -> Optional[str]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None
        try:
            if url == BASE_URL or url in (self.categories_url,):
                return "{}"
            if url == self.search_url:
                query = self.from_keyboard(header="Search Famelack TV")
                if not query:
                    sys.exit()
                channels = self._fetch_json(_category_data_url("all"), [])
                return json.dumps({"kind": "search", "query": query, "channels": channels})
            if url == self.countries_url:
                return json.dumps(self._fetch_json(COUNTRIES_METADATA_URL, {}))
            parts = _route_parts(url)
            if parts and parts[0] == "country" and len(parts) > 1:
                return json.dumps(self._fetch_json(_country_data_url(parts[1]), []))
            if parts and parts[0] == "category" and len(parts) > 1:
                return json.dumps(self._fetch_json(_category_data_url(parts[1]), []))
            if parts and parts[0] == "channel":
                return "{}"
        except (OSError, TypeError, ValueError, UnicodeError) as exc:
            xbmc.log(f"Famelack TV data error: {exc}", xbmc.LOGERROR)
            return "{}"
        return None

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None
        if url == BASE_URL:
            return self._root_menu()
        if url == self.countries_url:
            return self._countries_menu(self._load_response(response, {}))
        if url == self.categories_url:
            return self._categories_menu()
        parts = _route_parts(url)
        if parts and parts[0] == "channel":
            return self._source_menu(_decode_channel_route(url))
        if parts and parts[0] in ("country", "category"):
            return self._channels_menu(self._load_response(response, []))
        if url == self.search_url:
            data = self._load_response(response, {})
            query = _clean_text(data.get("query", "")).lower() if isinstance(data, dict) else ""
            channels = data.get("channels", []) if isinstance(data, dict) else []
            matches = [
                channel for channel in channels
                if isinstance(channel, dict) and query in _clean_text(channel.get("name", "")).lower()
            ]
            return self._channels_menu(matches)
        return []

    def play_video(self, item: str) -> Optional[bool]:
        if isinstance(item, bytes):
            item = item.decode("utf-8")

        data = _decode_play_url(item)
        fallback = {}
        if not data:
            try:
                fallback = json.loads(item)
            except (TypeError, ValueError):
                return None
            if not isinstance(fallback, dict):
                return None
            data = _decode_play_url(fallback.get("link", ""))
        if not data:
            return None

        source = data.get("source", "")
        if not _valid_http_url(source):
            return None
        playback_item = {
            "source": source,
            "title": data.get("title") or fallback.get("title") or "Famelack TV",
            "summary": data.get("summary") or fallback.get("summary", ""),
            "thumbnail": fallback.get("thumbnail", ""),
        }
        list_item = _build_list_item(playback_item, self.user_agent)
        xbmc.Player().play(_with_kodi_headers(source, self.user_agent), list_item)
        return True

    def _fetch_json(self, url: str, default: Any) -> Any:
        try:
            response = self.session.get(url, headers=self.headers)
            data = _decode_json_payload(_response_payload(response))
        except Exception as exc:
            xbmc.log(f"Famelack TV request error for {url}: {exc}", xbmc.LOGERROR)
            return default
        return data if isinstance(data, type(default)) else default

    def _load_response(self, response: str, default: Any) -> Any:
        try:
            data = json.loads(response or "")
        except (TypeError, ValueError):
            return default
        return data if isinstance(data, type(default)) else default

    def _root_menu(self) -> List[Dict[str, str]]:
        return [
            {"type": "dir", "title": "[COLOR deepskyblue]Search[/COLOR]", "link": self.search_url, "thumbnail": THUMBNAIL},
            {"type": "dir", "title": "Countries", "link": self.countries_url, "thumbnail": THUMBNAIL},
            {"type": "dir", "title": "Categories", "link": self.categories_url, "thumbnail": THUMBNAIL},
        ]

    def _countries_menu(self, metadata: Any) -> List[Dict[str, str]]:
        if not isinstance(metadata, dict):
            return []
        items = []
        for code, country in metadata.items():
            if not isinstance(country, dict) or not country.get("hasChannels"):
                continue
            name = _clean_text(country.get("country"))
            if not name:
                continue
            count = country.get("channelCount", 0)
            items.append({
                "type": "dir",
                "title": f"{name} ({count})",
                "link": _country_route(code),
                "thumbnail": THUMBNAIL,
            })
        return sorted(items, key=lambda item: item["title"].lower())

    def _categories_menu(self) -> List[Dict[str, str]]:
        return [
            {"type": "dir", "title": title, "link": _category_route(slug), "thumbnail": THUMBNAIL}
            for title, slug in CATEGORIES
        ]

    def _channels_menu(self, channels: Any) -> List[Dict[str, str]]:
        if not isinstance(channels, list):
            return []
        items = []
        for channel in channels:
            if not isinstance(channel, dict):
                continue
            title = _clean_text(channel.get("name"))
            if not title:
                continue
            items.append({
                "type": "dir",
                "title": title,
                "link": _channel_route(channel),
                "thumbnail": THUMBNAIL,
                "summary": self._channel_summary(channel),
            })
        return items

    def _channel_summary(self, channel: Dict[str, Any]) -> str:
        country = _clean_text(channel.get("country", "")).upper()
        languages = channel.get("languages", [])
        language_text = ", ".join(_clean_text(value).upper() for value in languages if _clean_text(value)) if isinstance(languages, list) else ""
        parts = [country, language_text]
        if channel.get("isGeoBlocked"):
            parts.append("Geo-restricted")
        return " | ".join(part for part in parts if part)

    def _source_menu(self, channel: Dict[str, Any]) -> List[Dict[str, str]]:
        if not isinstance(channel, dict):
            return []
        title = _clean_text(channel.get("name"))
        sources = channel.get("sources", {})
        if not title or not isinstance(sources, dict):
            return []

        candidates = []
        for url in sources.get("streams", []) if isinstance(sources.get("streams", []), list) else []:
            if not _valid_http_url(url):
                continue
            source_url = str(url)
            source_type = "HLS" if ".m3u8" in urlparse(source_url).path.lower() else "Stream"
            candidates.append((source_url, source_type, False))
        for url in sources.get("youtube", []) if isinstance(sources.get("youtube", []), list) else []:
            source_url = _normalize_youtube_url(url)
            if source_url:
                candidates.append((source_url, "YouTube", True))

        summary = self._channel_summary(channel)
        items = []
        seen = set()
        for source_url, source_type, is_youtube in candidates:
            if source_url in seen:
                continue
            seen.add(source_url)
            index = len(items) + 1
            source_title = f"{title} - {source_type} Source {index}"
            items.append({
                "type": "item",
                "title": source_title,
                "link": source_url if is_youtube else _play_url(source_url, source_title, summary),
                "thumbnail": THUMBNAIL,
                "summary": summary,
                "is_playable": "true",
            })
        return items

    def from_keyboard(self, default_text="", header="Search Famelack TV"):
        keyboard = xbmc.Keyboard(default_text, header, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return None
