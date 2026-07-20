"""Dailymotion provider for The Archives."""

import gzip
import json
import re
import ssl
import urllib.error
import urllib.request
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import quote, unquote, urlencode, urljoin, urlparse

import xbmc
import xbmcgui
import xbmcvfs
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://www.dailymotion.com"
API_URL = "https://api.dailymotion.com"
METADATA_URL = f"{BASE_URL}/player/metadata/video"
ROUTE_PATH = "/_thearchives_dailymotion"
FANART = Addon().getAddonInfo("fanart")
MAX_HLS_HEIGHT = 1080
PLAYBACK_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 7.1.1; Pixel Build/NMF26O) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/55.0.2883.91 Mobile Safari/537.36"
)

FIELDS = (
    "id,title,description,thumbnail_240_url,thumbnail_360_url,"
    "thumbnail_720_url,duration,created_time,owner.screenname,url,channel,mode"
)
LIMIT = 40
CATEGORIES = (
    ("Movies", "shortfilms"),
    ("TV", "tv"),
    ("Kids", "kids"),
    ("Comedy & Entertainment", "fun"),
    ("Music", "music"),
    ("News", "news"),
    ("Sports", "sport"),
    ("Tech", "tech"),
)
LIVE_CATEGORIES = (
    ("Sports", "sport"),
    ("News", "news"),
    ("Music", "music"),
    ("Gaming", "videogames"),
    ("Webcam", "webcam"),
)


def _clean_text(value) -> str:
    value = unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _route_url(kind: str, *parts: str) -> str:
    encoded = [quote(str(value), safe="") for value in (kind,) + parts]
    return f"{BASE_URL}{ROUTE_PATH}/" + "/".join(encoded)


def _route_parts(url: str) -> List[str]:
    path = urlparse(str(url or "")).path
    prefix = f"{ROUTE_PATH}/"
    if not path.startswith(prefix):
        return []
    return [unquote(part) for part in path[len(prefix):].split("/") if part]


def _video_id(value: str) -> str:
    parsed = urlparse(str(value or ""))
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")
    if host.endswith("dailymotion.com"):
        match = re.search(r"(?:^|/)video/([A-Za-z0-9]+)", "/" + path)
        if match:
            return match.group(1)
        match = re.search(r"(?:^|/)([xk][A-Za-z0-9]+)(?:_|$)", path)
        if match:
            return match.group(1)
    if host == "dai.ly":
        return path.split("/", 1)[0]
    match = re.search(r"\b([xk][A-Za-z0-9]{4,})\b", str(value or ""))
    return match.group(1) if match else ""


def _canonical_url(video_id: str) -> str:
    return f"{BASE_URL}/video/{video_id}" if video_id else ""


def _json_data(value) -> Dict:
    if isinstance(value, dict):
        return value
    try:
        data = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _decode_item(item) -> (Dict, str):
    if isinstance(item, bytes):
        item = item.decode("utf-8")
    if isinstance(item, dict):
        data = item
    else:
        data = _json_data(item)
    link = data.get("link", "") if isinstance(data, dict) else ""
    if not link and isinstance(item, str):
        link = item
    return data if isinstance(data, dict) else {}, str(link or "")


def _page_number(parts: List[str], index: int) -> int:
    try:
        return max(1, int(parts[index]))
    except (IndexError, TypeError, ValueError):
        return 1


def _duration_text(seconds) -> str:
    try:
        seconds = int(seconds or 0)
    except (TypeError, ValueError):
        seconds = 0
    if seconds <= 0:
        return ""
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _api_url(path: str, params: Dict[str, str]) -> str:
    clean = {key: value for key, value in params.items() if value not in (None, "")}
    return f"{API_URL}{path}?{urlencode(clean)}"


def _kodi_header_query(headers: Dict[str, str]) -> str:
    return "&".join(
        f"{key}={quote(str(value), safe='')}"
        for key, value in headers.items()
        if value
    )


def _with_kodi_headers(url: str, headers: Dict[str, str]) -> str:
    header_query = _kodi_header_query(headers)
    return f"{url}|{header_query}" if header_query else url


def _playback_headers() -> Dict[str, str]:
    return {
        "User-Agent": PLAYBACK_USER_AGENT,
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
        "Cookie": "lang=en_US; ff=on",
        "Accept-Language": "en-US,en",
        "Accept-Encoding": "gzip",
    }


def _http11_text(url: str, headers: Dict[str, str], timeout: int = 20, session=None) -> str:
    try:
        request = urllib.request.Request(url, headers={key: str(value) for key, value in headers.items() if value})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if "gzip" in (response.headers.get("Content-Encoding") or "").lower():
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", "ignore")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        xbmc.log(f"[TheArchives][Dailymotion] simple playlist fetch failed: {exc}", xbmc.LOGWARNING)

    try:
        import requests
        response = requests.get(url, headers=headers, timeout=timeout)
        if getattr(response, "status_code", 0) < 400:
            return getattr(response, "text", "") or ""
        xbmc.log(
            f"[TheArchives][Dailymotion] fresh playlist fetch failed: HTTP {response.status_code}",
            xbmc.LOGWARNING,
        )
    except Exception as exc:
        xbmc.log(f"[TheArchives][Dailymotion] fresh playlist fetch failed: {exc}", xbmc.LOGWARNING)

    if session:
        try:
            response = session.get(url, headers=headers, timeout=timeout)
            if getattr(response, "status_code", 0) < 400:
                return getattr(response, "text", "") or ""
            xbmc.log(
                f"[TheArchives][Dailymotion] session playlist fetch failed: HTTP {response.status_code}",
                xbmc.LOGWARNING,
            )
        except Exception as exc:
            xbmc.log(f"[TheArchives][Dailymotion] session playlist fetch failed: {exc}", xbmc.LOGWARNING)

    try:
        cert_file = xbmcvfs.translatePath("special://xbmc/system/certs/cacert.pem")
    except Exception:
        cert_file = ""
    context = ssl.create_default_context(cafile=cert_file or None)
    try:
        context.set_alpn_protocols(["http/1.1"])
    except NotImplementedError:
        pass
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
    request = urllib.request.Request(url)
    parsed = urlparse(url)
    request.add_unredirected_header("Host", parsed.netloc)
    request.add_unredirected_header("Referer", headers.get("Referer") or f"{parsed.scheme}://{parsed.netloc}/")
    for key, value in headers.items():
        if value:
            request.add_header(key, str(value))
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read()
            if "gzip" in (response.headers.get("Content-Encoding") or "").lower():
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", "ignore")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        xbmc.log(f"[TheArchives][Dailymotion] playlist fetch failed: {exc}", xbmc.LOGWARNING)
        return ""


def _stream_height(info: str) -> int:
    match = re.search(r"RESOLUTION=\d+x(\d+)", info or "", re.I)
    if match:
        return int(match.group(1))
    match = re.search(r'(?:NAME|VIDEO)=["\']?(\d+)', info or "", re.I)
    return int(match.group(1)) if match else 0


def _select_hls_variant(master_url: str, playlist: str, max_height: int = MAX_HLS_HEIGHT) -> str:
    variants = []
    lines = [line.strip() for line in (playlist or "").splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF"):
            continue
        for candidate in lines[index + 1:]:
            if candidate.startswith("#"):
                continue
            height = _stream_height(line)
            variants.append((height, urljoin(master_url, candidate).split("#cell", 1)[0]))
            break
    if not variants:
        return ""
    allowed = [row for row in variants if row[0] <= max_height]
    selected = max(allowed or variants, key=lambda row: row[0])
    return selected[1]


def _resolve_hls_variant(stream_url: str, headers: Dict[str, str], session=None) -> str:
    playlist = _http11_text(stream_url, headers, session=session)
    if not playlist.lstrip().startswith("#EXTM3U"):
        return ""
    return _select_hls_variant(stream_url, playlist)


def _session_cookie_header(session) -> str:
    cookies = getattr(session, "cookies", None)
    if not cookies:
        return ""
    try:
        values = cookies.get_dict(domain=".dailymotion.com")
        values.update(cookies.get_dict(domain="www.dailymotion.com"))
    except Exception:
        values = {}
    if not values:
        try:
            values = cookies.get_dict()
        except Exception:
            values = {}
    return "; ".join(f"{key}={value}" for key, value in values.items())


def _best_thumbnail(item: Dict) -> str:
    return (
        item.get("thumbnail_720_url")
        or item.get("thumbnail_360_url")
        or item.get("thumbnail_240_url")
        or ""
    )


def _rows_from_videos(data: Dict) -> List[Dict[str, str]]:
    rows = []
    seen = set()
    for video in (data or {}).get("list") or []:
        if not isinstance(video, dict):
            continue
        video_id = str(video.get("id") or _video_id(video.get("url", "")))
        title = _clean_text(video.get("title"))
        if not video_id or not title or video_id in seen:
            continue
        seen.add(video_id)
        duration = _duration_text(video.get("duration"))
        owner = _clean_text(video.get("owner.screenname"))
        is_live = str(video.get("mode") or "").lower() == "live"
        title_prefix = "[COLOR lime][LIVE][/COLOR] " if is_live else ""
        display = f"[COLOR red]>[/COLOR] {title_prefix}{title}"
        details = []
        if duration:
            details.append(duration)
        if owner:
            details.append(owner)
        if details:
            display += f"  [COLOR gray][{' | '.join(details)}][/COLOR]"
        summary = _clean_text(video.get("description") or title)
        rows.append({
            "type": "item",
            "title": display,
            "link": _canonical_url(video_id),
            "thumbnail": _best_thumbnail(video),
            "summary": summary,
            "provider": "dailymotion",
            "is_playable": "true",
            "duration": str(video.get("duration") or ""),
        })
    return rows


def _quality_rank(name: str) -> int:
    if str(name).isdigit():
        return int(name)
    return {"auto": 10000}.get(str(name).lower(), 0)


def _select_stream(metadata: Dict) -> Dict[str, str]:
    qualities = (metadata or {}).get("qualities") or {}
    candidates = []
    for quality, media_list in qualities.items():
        if isinstance(media_list, dict):
            media_list = [media_list]
        if not isinstance(media_list, list):
            continue
        for media in media_list:
            if not isinstance(media, dict):
                continue
            url = str(media.get("url") or "")
            media_type = str(media.get("type") or "")
            if not url.startswith(("http://", "https://")):
                continue
            protocol = "hls" if "mpegurl" in media_type.lower() or ".m3u8" in url.lower() else "mp4"
            candidates.append({
                "url": url,
                "protocol": protocol,
                "rank": _quality_rank(str(quality)),
            })
    if not candidates:
        return {}
    hls = [candidate for candidate in candidates if candidate["protocol"] == "hls"]
    return max(hls or candidates, key=lambda candidate: candidate["rank"])


def _subtitle_urls(metadata: Dict) -> List[str]:
    subtitles = (((metadata or {}).get("subtitles") or {}).get("data") or [])
    urls = []
    for track in subtitles:
        if isinstance(track, dict):
            url = track.get("url") or track.get("src")
            if url:
                urls.append(url)
    return urls


class Dailymotion(Plugin):
    name = "dailymotion"
    priority = 1065

    def __init__(self):
        self.session = DI.session
        self.base_url = BASE_URL
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        if self.session:
            self.session.headers.update({
                "User-Agent": self.user_agent,
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
                "Referer": f"{BASE_URL}/",
            })

    @staticmethod
    def _response_json(response) -> Dict:
        try:
            data = response.json()
        except (AttributeError, TypeError, ValueError):
            data = _json_data(getattr(response, "text", "") or "{}")
        return data if isinstance(data, dict) else {}

    def _api_get(self, path: str, params: Dict[str, str]) -> Dict:
        response = self.session.get(
            _api_url(path, params),
            headers={"Accept": "application/json"},
            timeout=20,
        )
        return self._response_json(response)

    def get_list(self, url: str) -> Optional[str]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        route = _route_parts(url)
        if not route:
            return json.dumps({"kind": "root"})

        kind = route[0]
        if kind == "live_root":
            return json.dumps({"kind": "live_root"})

        if kind == "search":
            if len(route) == 1:
                query = self.from_keyboard()
                if not query:
                    return json.dumps({"kind": "message", "title": "Search cancelled"})
                return json.dumps({"kind": "redirect", "link": _route_url("search", query, "1")})
            query = route[1]
            page = _page_number(route, 2)
            return json.dumps({
                "kind": "videos",
                "title": f"Search: {query}",
                "page": page,
                "data": self._api_get("/videos", {
                    "fields": FIELDS,
                    "limit": str(LIMIT),
                    "page": str(page),
                    "search": query,
                }),
                "next": _route_url("search", query, str(page + 1)),
            })

        if kind == "live":
            page = _page_number(route, 1)
            return json.dumps({
                "kind": "videos",
                "title": "Live Now",
                "page": page,
                "data": self._api_get("/videos", {
                    "fields": FIELDS,
                    "limit": str(LIMIT),
                    "page": str(page),
                    "live_onair": "true",
                    "mode": "live",
                    "sort": "live-audience",
                }),
                "next": _route_url("live", str(page + 1)),
            })


        if kind == "live_categories":
            return json.dumps({"kind": "live_categories"})

        if kind == "live_channel" and len(route) > 1:
            channel = route[1]
            page = _page_number(route, 2)
            return json.dumps({
                "kind": "videos",
                "title": f"Live {channel}",
                "page": page,
                "data": self._api_get("/videos", {
                    "fields": FIELDS,
                    "limit": str(LIMIT),
                    "page": str(page),
                    "channel": channel,
                    "live_onair": "true",
                    "mode": "live",
                    "sort": "live-audience",
                }),
                "next": _route_url("live_channel", channel, str(page + 1)),
            })

        if kind == "popular":
            page = _page_number(route, 1)
            return json.dumps({
                "kind": "videos",
                "title": "Popular",
                "page": page,
                "data": self._api_get("/videos", {
                    "fields": FIELDS,
                    "limit": str(LIMIT),
                    "page": str(page),
                    "sort": "visited",
                }),
                "next": _route_url("popular", str(page + 1)),
            })

        if kind == "recent":
            page = _page_number(route, 1)
            return json.dumps({
                "kind": "videos",
                "title": "Recently Added",
                "page": page,
                "data": self._api_get("/videos", {
                    "fields": FIELDS,
                    "limit": str(LIMIT),
                    "page": str(page),
                    "sort": "recent",
                }),
                "next": _route_url("recent", str(page + 1)),
            })

        if kind == "channel" and len(route) > 1:
            channel = route[1]
            page = _page_number(route, 2)
            return json.dumps({
                "kind": "videos",
                "title": channel,
                "page": page,
                "data": self._api_get("/videos", {
                    "fields": FIELDS,
                    "limit": str(LIMIT),
                    "page": str(page),
                    "channel": channel,
                    "sort": "visited",
                }),
                "next": _route_url("channel", channel, str(page + 1)),
            })

        return None

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None
        data = _json_data(response)
        kind = data.get("kind")
        if kind == "root":
            return self._root_menu()
        if kind == "live_root":
            return self._live_menu()
        if kind == "message":
            return [{
                "type": "item",
                "title": f"[COLOR grey]{data.get('title', 'Dailymotion')}[/COLOR]",
                "link": "",
                "is_playable": "false",
            }]
        if kind == "live_categories":
            return self._live_category_menu()
        if kind == "redirect":
            return [{
                "type": "dir",
                "title": "[COLOR deepskyblue]Search Results[/COLOR]",
                "link": data.get("link", ""),
            }]
        if kind != "videos":
            return None

        rows = _rows_from_videos(data.get("data") or {})
        if (data.get("data") or {}).get("has_more"):
            rows.append({
                "type": "dir",
                "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                "link": data.get("next", ""),
                "thumbnail": "resources/media/movies.png",
            })
        return rows

    def play_video(self, item: str) -> Optional[bool]:
        item_data, link = _decode_item(item)
        if item_data and item_data.get("provider") not in (None, "", "dailymotion"):
            return None

        video_id = _video_id(link)
        if not video_id:
            return None

        canonical_url = _canonical_url(video_id)
        try:
            playback_headers = _playback_headers()
            metadata_headers = dict(playback_headers)
            metadata_headers["Accept"] = "application/json"
            try:
                import requests
                response = requests.get(
                    f"{METADATA_URL}/{video_id}",
                    headers=metadata_headers,
                    timeout=20,
                )
            except Exception:
                response = self.session.get(
                    f"{METADATA_URL}/{video_id}",
                    headers=metadata_headers,
                    timeout=20,
                )
            metadata = self._response_json(response)
            if metadata.get("error"):
                message = _clean_text((metadata.get("error") or {}).get("title") or "Video unavailable")
                xbmcgui.Dialog().notification("Dailymotion", message, xbmcgui.NOTIFICATION_WARNING, 3000)
                return True
            if metadata.get("private") or metadata.get("is_password_protected"):
                xbmcgui.Dialog().notification("Dailymotion", "Video requires access", xbmcgui.NOTIFICATION_WARNING, 3000)
                return True

            stream = _select_stream(metadata)
            if not stream:
                xbmcgui.Dialog().notification("Dailymotion", "No playable stream found", xbmcgui.NOTIFICATION_WARNING, 3000)
                return True

            title = _clean_text(item_data.get("title") or metadata.get("title") or "Dailymotion")
            title = re.sub(r"\[/?COLOR[^\]]*\]", "", title, flags=re.IGNORECASE).strip()
            summary = _clean_text(item_data.get("summary") or metadata.get("description") or title)
            thumbnails = metadata.get("thumbnails") or {}
            poster = (
                item_data.get("thumbnail")
                or thumbnails.get("720")
                or thumbnails.get("480")
                or thumbnails.get("360")
                or ""
            )
            headers = dict(playback_headers)
            headers["Accept"] = "application/vnd.apple.mpegurl,application/x-mpegURL,*/*"
            stream_url = stream["url"]
            use_adaptive = False
            if stream["protocol"] == "hls":
                variant_url = _resolve_hls_variant(stream_url, headers, session=self.session)
                if variant_url:
                    stream_url = variant_url
                else:
                    use_adaptive = True
                    xbmc.log("[TheArchives][Dailymotion] using inputstream.adaptive master manifest fallback", xbmc.LOGWARNING)
            play_url = stream_url if use_adaptive else _with_kodi_headers(stream_url, headers)

            list_item = xbmcgui.ListItem(title, path=play_url)
            list_item.setProperty("IsPlayable", "true")
            if poster:
                list_item.setArt({
                    "thumb": poster,
                    "icon": poster,
                    "poster": poster,
                    "fanart": FANART,
                })
            info = {"title": title, "plot": summary}
            if metadata.get("duration"):
                info["duration"] = metadata.get("duration")
            set_video_info(list_item, info)
            subtitles = _subtitle_urls(metadata)
            if subtitles:
                try:
                    list_item.setSubtitles(subtitles)
                except AttributeError:
                    pass
            if stream["protocol"] == "hls":
                header_query = _kodi_header_query(headers)
                if use_adaptive:
                    list_item.setProperty("inputstream", "inputstream.adaptive")
                    list_item.setProperty("inputstream.adaptive.manifest_type", "hls")
                    list_item.setProperty("inputstream.adaptive.manifest_headers", header_query)
                    list_item.setProperty("inputstream.adaptive.stream_headers", header_query)
                    list_item.setProperty("inputstream.adaptive.common_headers", header_query)


                list_item.setMimeType("application/vnd.apple.mpegurl")
            else:
                list_item.setMimeType("video/mp4")
            try:
                list_item.setContentLookup(False)
            except AttributeError:
                pass
            xbmc.Player().play(play_url, list_item)
            return True
        except Exception as exc:
            xbmc.log(f"[TheArchives][Dailymotion] stream resolve failed: {exc}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification("Dailymotion", "Failed to resolve stream", xbmcgui.NOTIFICATION_WARNING, 3000)
            return True

    def from_keyboard(self, default_text="", header="Search Dailymotion"):
        keyboard = xbmc.Keyboard(default_text, header, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return None

    def _live_menu(self) -> List[Dict[str, str]]:
        return [
            {
                "type": "dir",
                "title": "[COLOR lime]Live Now[/COLOR]",
                "link": _route_url("live", "1"),
                "thumbnail": "resources/media/live_tv.png",
                "summary": "Browse live Dailymotion streams that are on air now.",
            },
            {
                "type": "dir",
                "title": "Live Categories",
                "link": _route_url("live_categories"),
                "thumbnail": "resources/media/live_tv.png",
                "summary": "Browse Dailymotion live streams by category.",
            },
        ]

    def _root_menu(self) -> List[Dict[str, str]]:
        rows = [
            {
                "type": "dir",
                "title": "[COLOR deepskyblue]Search[/COLOR]",
                "link": _route_url("search"),
                "thumbnail": "resources/media/movies.png",
                "summary": "Search Dailymotion videos.",
            },
            {
                "type": "dir",
                "title": "[COLOR lime]Live Now[/COLOR]",
                "link": _route_url("live", "1"),
                "thumbnail": "resources/media/movies.png",
                "summary": "Browse live Dailymotion streams that are on air now.",
            },

            {
                "type": "dir",
                "title": "Live Categories",
                "link": _route_url("live_categories"),
                "thumbnail": "resources/media/movies.png",
                "summary": "Browse Dailymotion live streams by category.",
            },
            {
                "type": "dir",
                "title": "Popular",
                "link": _route_url("popular", "1"),
                "thumbnail": "resources/media/movies.png",
                "summary": "Browse popular Dailymotion videos.",
            },
            {
                "type": "dir",
                "title": "Recently Added",
                "link": _route_url("recent", "1"),
                "thumbnail": "resources/media/movies.png",
                "summary": "Browse recent Dailymotion uploads.",
            },
        ]
        for title, channel in CATEGORIES:
            rows.append({
                "type": "dir",
                "title": title,
                "link": _route_url("channel", channel, "1"),
                "thumbnail": "resources/media/movies.png",
                "summary": f"Browse Dailymotion {title}.",
            })
        return rows

    def _live_category_menu(self) -> List[Dict[str, str]]:
        rows = []
        for title, channel in LIVE_CATEGORIES:
            rows.append({
                "type": "dir",
                "title": title,
                "link": _route_url("live_channel", channel, "1"),
                "thumbnail": "resources/media/movies.png",
                "summary": f"Browse live Dailymotion {title} streams.",
            })
        return rows
