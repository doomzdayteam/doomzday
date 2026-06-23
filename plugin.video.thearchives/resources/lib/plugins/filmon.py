import json
import re
import sys
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://www.filmon.com"
API_BASE = "https://api.filmon.com/api/vod"
LIVE_ROOT_URL = f"{BASE_URL}/tv/"
LIVE_CHANNEL_URL = f"{BASE_URL}/channel"
ROUTE_PATH = "/_thearchives"
PAGE_SIZE = 50
FANART = Addon().getAddonInfo("fanart")


def _clean_text(value: str) -> str:
    value = unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _absolute_url(url: str) -> str:
    if not isinstance(url, str) or not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return f"{BASE_URL}{url}"
    return f"{BASE_URL}/{url}"


def _route_url(kind: str, *parts: str) -> str:
    route_parts = [quote(str(part), safe="") for part in (kind,) + parts]
    return f"{BASE_URL}{ROUTE_PATH}/" + "/".join(route_parts)


def _route_parts(url: str) -> List[str]:
    parsed = urlparse(url)
    route_prefix = ROUTE_PATH.strip("/") + "/"
    path = parsed.path.strip("/")
    if not path.startswith(route_prefix):
        return []
    return [unquote(part) for part in path[len(route_prefix):].split("/") if part]


def _duration_str(seconds) -> str:
    if not seconds:
        return ""
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return ""
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _json_data(response: str) -> Dict:
    try:
        return json.loads(response or "{}")
    except (TypeError, ValueError):
        return {}


def _response_data(response) -> Dict:
    try:
        return response.json()
    except (AttributeError, ValueError):
        return _json_data(getattr(response, "text", ""))


def _extract_live_groups(html: str) -> List[Dict]:
    marker = "var groups = "
    start = (html or "").find(marker)
    if start < 0:
        return []
    start += len(marker)
    depth = 0
    in_string = False
    escape = False
    end = start
    for index, char in enumerate(html[start:], start):
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end <= start:
        return []
    try:
        groups = json.loads(html[start:end])
    except (TypeError, ValueError):
        return []
    return groups if isinstance(groups, list) else []


def _is_live_channel(channel: Dict) -> bool:
    if not isinstance(channel, dict):
        return False
    if channel.get("is_vod") or channel.get("is_vox"):
        return False
    if channel.get("adult_content") or channel.get("is_adult"):
        return False
    return bool(channel.get("id") and channel.get("title"))


def _image_from_genre(genre: Dict) -> str:
    for image in genre.get("images") or []:
        if isinstance(image, dict) and image.get("url"):
            return _absolute_url(image.get("url"))
    return "resources/media/movies.png"


def _poster_url(item: Dict) -> str:
    poster = item.get("poster")
    if isinstance(poster, dict):
        thumbs = poster.get("thumbs")
        if isinstance(thumbs, dict):
            for key in ("thumb_220p", "thumb_120p"):
                thumb = thumbs.get(key)
                if isinstance(thumb, dict) and thumb.get("url"):
                    return _absolute_url(thumb.get("url"))
        if poster.get("url"):
            return _absolute_url(poster.get("url"))

    artwork = item.get("artwork")
    if isinstance(artwork, list):
        for image in artwork:
            if isinstance(image, dict) and image.get("url"):
                return _absolute_url(image.get("url"))
    if isinstance(artwork, dict):
        for image in artwork.values():
            if isinstance(image, dict) and image.get("url"):
                return _absolute_url(image.get("url"))
    return ""


def _genre_names(item: Dict) -> List[str]:
    genres = item.get("genres") or []
    names = []
    for genre in genres:
        if isinstance(genre, dict):
            value = genre.get("name") or genre.get("slug")
        else:
            value = genre
        value = _clean_text(value)
        if value:
            names.append(value.title())
    return names


def _movie_id(item: Dict) -> str:
    for key in ("original_id", "id"):
        value = item.get(key)
        if value:
            text = str(value)
            if text.isdigit():
                return text
    return ""


def _play_url(movie_id: str) -> str:
    return f"filmon://play?{urlencode({'id': movie_id})}"


def _decode_play_url(url: str) -> Dict[str, str]:
    parsed = urlparse(url)
    return {key: values[0] for key, values in parse_qs(parsed.query).items() if values}


def _kodi_header_query(user_agent: str, referer: str = BASE_URL) -> str:
    return (
        f"User-Agent={quote(user_agent, safe='')}"
        f"&Referer={quote(referer, safe='')}"
        f"&Origin={quote(BASE_URL, safe='')}"
    )


def _with_kodi_headers(url: str, user_agent: str, referer: str = BASE_URL) -> str:
    return f"{url}|{_kodi_header_query(user_agent, referer)}" if url else ""


def _stream_url_from_movie(movie: Dict) -> str:
    streams = movie.get("streams") or {}
    if isinstance(streams, dict):
        for quality in ("high", "low"):
            stream = streams.get(quality)
            if isinstance(stream, dict) and stream.get("url"):
                return stream.get("url")
    public_url = movie.get("public_url") or ""
    if public_url:
        return _absolute_url(public_url)
    return ""


def _stream_url_from_channel(channel: Dict) -> str:
    streams = channel.get("streams") or []
    if isinstance(streams, list):
        fallback = ""
        for stream in streams:
            if not isinstance(stream, dict) or not stream.get("url"):
                continue
            if stream.get("quality") == "low":
                return stream.get("url")
            if not fallback:
                fallback = stream.get("url")
        return fallback
    return ""


def _listing_payload(kind: str, route: str, start_index: int, data: Dict) -> str:
    return json.dumps({
        "kind": "listing",
        "route": route,
        "start_index": start_index,
        "max_results": PAGE_SIZE,
        "items": data.get("response") or [],
        "total_found": data.get("total_found") or data.get("total") or 0,
    })


def _live_payload(kind: str, groups: List[Dict], group_alias: str = "") -> str:
    return json.dumps({
        "kind": kind,
        "groups": groups,
        "group_alias": group_alias,
    })


class FilmOn(Plugin):
    name = "filmon"
    priority = 1055

    def __init__(self):
        self.session = DI.session
        self.base_url = BASE_URL
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        if self.session:
            self.session.headers = {
                "User-Agent": self.user_agent,
                "Referer": f"{BASE_URL}/",
                "Origin": BASE_URL,
                "Accept": "application/json,text/plain,*/*",
            }
        self.search_url = _route_url("search")

    def _api_get(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict:
        url = f"{API_BASE}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"
        return _response_data(self.session.get(url))

    def get_list(self, url: str) -> Optional[str]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        route_parts = _route_parts(url)
        public_genre = self._public_vod_genre(url)
        if self._is_live_root(url):
            return _live_payload("live_root", self._fetch_live_groups())

        if public_genre:
            data = self._api_get("search", {
                "genre": public_genre,
                "max_results": str(PAGE_SIZE),
                "start_index": "0",
                "order_by": "date",
            })
            return _listing_payload("genre", f"genre/{public_genre}", 0, data)

        if url.rstrip("/") == self.base_url or not route_parts:
            genres = self._api_get("genres").get("response") or []
            return json.dumps({"kind": "root", "genres": genres})

        kind = route_parts[0]
        if kind == "live":
            group_alias = route_parts[1] if len(route_parts) > 1 else ""
            return _live_payload("live_group", self._fetch_live_groups(), group_alias)

        if kind == "search":
            if len(route_parts) == 1:
                query = self.from_keyboard(header="Search FilmOn")
                if not query:
                    sys.exit()
                return json.dumps({
                    "kind": "redirect",
                    "link": _route_url("search", query, "0"),
                })
            query = route_parts[1]
            start_index = self._route_start(route_parts, 2)
            data = self._api_get("search", {
                "term": query,
                "max_results": str(PAGE_SIZE),
                "start_index": str(start_index),
            })
            return _listing_payload("search", f"search/{query}", start_index, data)

        if kind == "genre" and len(route_parts) > 1:
            slug = route_parts[1]
            start_index = self._route_start(route_parts, 2)
            data = self._api_get("search", {
                "genre": slug,
                "max_results": str(PAGE_SIZE),
                "start_index": str(start_index),
                "order_by": "date",
            })
            return _listing_payload("genre", f"genre/{slug}", start_index, data)

        return None

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        data = _json_data(response)
        if data.get("kind") == "live_root":
            return self._live_root_menu(data.get("groups") or [])

        if data.get("kind") == "live_group":
            return self._live_group_items(data.get("groups") or [], data.get("group_alias", ""))

        if data.get("kind") == "redirect":
            return [{"type": "dir", "title": "[COLOR deepskyblue]Search Results[/COLOR]", "link": data.get("link", "")}]

        if data.get("kind") == "root" or url.rstrip("/") == self.base_url:
            return self._root_menu(data.get("genres") or [])

        if data.get("kind") == "listing":
            return self._parse_listing(url, data)

        return None

    def play_video(self, item: str) -> Optional[bool]:
        item_data = {}
        link = item
        try:
            if isinstance(item, bytes):
                item = item.decode("utf-8")
            item_data = json.loads(item)
            link = item_data.get("link", "")
        except (TypeError, ValueError, AttributeError):
            link = item.decode("utf-8") if isinstance(item, bytes) else item

        if isinstance(link, str) and link.startswith("filmon://live?"):
            return self._play_live(item_data, link)

        if not isinstance(link, str) or not link.startswith("filmon://play?"):
            return None

        movie_id = _decode_play_url(link).get("id", "")
        if not movie_id:
            return None

        try:
            movie = self._api_get("movie", {"id": movie_id}).get("response") or {}
        except Exception as exc:
            xbmc.log(f"[TheArchives][FilmOn] movie resolve failed: {exc}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification("FilmOn", "Failed to resolve stream", xbmcgui.NOTIFICATION_WARNING, 3000)
            return True

        stream_url = _stream_url_from_movie(movie)
        if not stream_url:
            xbmcgui.Dialog().notification("FilmOn", "Stream not available", xbmcgui.NOTIFICATION_WARNING, 3000)
            return True

        play_url = _with_kodi_headers(stream_url, self.user_agent)
        title = _clean_text(item_data.get("title") or movie.get("title") or "FilmOn")
        thumbnail = item_data.get("thumbnail") or _poster_url(movie)
        summary = item_data.get("summary") or _clean_text(movie.get("description", ""))

        list_item = xbmcgui.ListItem(title, path=play_url)
        list_item.setProperty("IsPlayable", "true")
        if thumbnail:
            list_item.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail, "fanart": FANART})
        set_video_info(list_item, {"title": title, "plot": summary})
        list_item.setMimeType("application/vnd.apple.mpegurl")
        try:
            list_item.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(play_url, list_item)
        return True

    def _play_live(self, item_data: Dict, link: str) -> Optional[bool]:
        data = _decode_play_url(link)
        channel_id = data.get("id", "")
        alias = data.get("alias", "")
        channel_key = channel_id or alias
        if not channel_key:
            return None

        try:
            channel = self._live_channel(channel_key, alias)
        except Exception as exc:
            xbmc.log(f"[TheArchives][FilmOn] live resolve failed: {exc}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification("FilmOn", "Failed to resolve live stream", xbmcgui.NOTIFICATION_WARNING, 3000)
            return True

        stream_url = _stream_url_from_channel(channel)
        if not stream_url:
            xbmcgui.Dialog().notification("FilmOn", "Live stream not available", xbmcgui.NOTIFICATION_WARNING, 3000)
            return True

        referer = f"{LIVE_ROOT_URL}channel/{channel.get('alias') or alias or channel_key}"
        play_url = _with_kodi_headers(stream_url, self.user_agent, referer)
        title = _clean_text(item_data.get("title") or channel.get("title") or "FilmOn Live")
        thumbnail = item_data.get("thumbnail") or channel.get("logo") or channel.get("big_logo") or ""
        summary = item_data.get("summary") or _clean_text(channel.get("description", ""))
        list_item = xbmcgui.ListItem(title, path=play_url)
        list_item.setProperty("IsPlayable", "true")
        if thumbnail:
            list_item.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail, "fanart": FANART})
        set_video_info(list_item, {"title": title, "plot": summary})
        list_item.setMimeType("application/vnd.apple.mpegurl")
        try:
            list_item.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(play_url, list_item)
        return True

    def _root_menu(self, genres: List[Dict]) -> List[Dict[str, str]]:
        items = [{
            "type": "dir",
            "title": "[COLOR deepskyblue]Search[/COLOR]",
            "link": self.search_url,
            "thumbnail": "resources/media/movies.png",
            "summary": "Search FilmOn VOD titles.",
        }]
        for genre in genres:
            if not isinstance(genre, dict):
                continue
            name = _clean_text(genre.get("name", ""))
            slug = _clean_text(genre.get("slug", ""))
            if not name or not slug:
                continue
            items.append({
                "type": "dir",
                "title": name,
                "link": _route_url("genre", slug, "0"),
                "thumbnail": _image_from_genre(genre),
                "summary": _clean_text(genre.get("description") or f"Browse FilmOn {name} VOD titles."),
            })
        return items

    def _live_root_menu(self, groups: List[Dict]) -> List[Dict[str, str]]:
        items = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            channels = [channel for channel in group.get("channels") or [] if _is_live_channel(channel)]
            if not channels:
                continue
            title = _clean_text(group.get("title") or group.get("name") or group.get("group") or "Channels")
            alias = _clean_text(group.get("alias") or group.get("group_alias") or "")
            if not title or not alias:
                continue
            items.append({
                "type": "dir",
                "title": f"[COLOR orange]{title}[/COLOR] ({len(channels)})",
                "link": _route_url("live", alias),
                "thumbnail": _absolute_url(group.get("logo_uri") or group.get("logo_148x148_uri") or "") or "resources/media/live_tv.png",
                "summary": _clean_text(group.get("description") or f"Browse FilmOn {title} live channels."),
            })
        return items or [{
            "type": "dir",
            "title": "[COLOR grey]No FilmOn live groups found[/COLOR]",
            "link": LIVE_ROOT_URL,
        }]

    def _live_group_items(self, groups: List[Dict], group_alias: str) -> List[Dict[str, str]]:
        items = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            alias = _clean_text(group.get("alias") or group.get("group_alias") or "")
            if alias != group_alias:
                continue
            for channel in group.get("channels") or []:
                if not _is_live_channel(channel):
                    continue
                title = _clean_text(channel.get("title", ""))
                channel_id = str(channel.get("id") or "")
                channel_alias = _clean_text(channel.get("alias", ""))
                items.append({
                    "type": "item",
                    "title": f"[COLOR red]>[/COLOR] {title}",
                    "link": f"filmon://live?{urlencode({'id': channel_id, 'alias': channel_alias})}",
                    "thumbnail": _absolute_url(channel.get("logo") or channel.get("big_logo") or ""),
                    "summary": _clean_text(channel.get("description") or channel.get("group") or ""),
                    "is_playable": "true",
                })
        return items or [{
            "type": "dir",
            "title": "[COLOR grey]No FilmOn live channels found[/COLOR]",
            "link": LIVE_ROOT_URL,
        }]

    def _parse_listing(self, url: str, data: Dict) -> List[Dict[str, str]]:
        items = []
        for item in data.get("items") or []:
            parsed = self._item_from_movie(item)
            if parsed:
                items.append(parsed)

        next_link = self._next_page_link(url, data)
        if next_link:
            items.append({
                "type": "dir",
                "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                "link": next_link,
            })
        return items or [{
            "type": "dir",
            "title": "[COLOR grey]No FilmOn titles found[/COLOR]",
            "link": BASE_URL,
        }]

    def _item_from_movie(self, item: Dict) -> Optional[Dict[str, str]]:
        movie_id = _movie_id(item)
        title = _clean_text(item.get("title", ""))
        if not movie_id or not title:
            return None

        duration = _duration_str(item.get("length") or item.get("duration"))
        display = f"[COLOR red]>[/COLOR] {title}"
        if duration:
            display = f"{display} [COLOR grey]({duration})[/COLOR]"
        genres = ", ".join(_genre_names(item))
        summary = _clean_text(item.get("description") or item.get("meta_description") or "")
        if genres and summary:
            summary = f"{genres} | {summary}"
        elif genres:
            summary = genres

        return {
            "type": "item",
            "title": display,
            "link": _play_url(movie_id),
            "thumbnail": _poster_url(item),
            "summary": summary,
            "is_playable": "true",
        }

    def _next_page_link(self, url: str, data: Dict) -> str:
        try:
            start_index = int(data.get("start_index") or 0)
            max_results = int(data.get("max_results") or PAGE_SIZE)
            total_found = int(data.get("total_found") or 0)
        except (TypeError, ValueError):
            return ""

        next_start = start_index + max_results
        if next_start >= total_found:
            return ""

        route_parts = _route_parts(url)
        if route_parts and route_parts[0] == "genre" and len(route_parts) > 1:
            return _route_url("genre", route_parts[1], str(next_start))
        if route_parts and route_parts[0] == "search" and len(route_parts) > 1:
            return _route_url("search", route_parts[1], str(next_start))
        route = data.get("route", "")
        if route.startswith("genre/"):
            return _route_url("genre", route.split("/", 1)[1], str(next_start))
        if route.startswith("search/"):
            return _route_url("search", route.split("/", 1)[1], str(next_start))
        return ""

    def _route_start(self, route_parts: List[str], index: int) -> int:
        try:
            return int(route_parts[index]) if len(route_parts) > index else 0
        except (TypeError, ValueError):
            return 0

    def _is_live_root(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc.endswith("filmon.com") and parsed.path.strip("/") == "tv"

    def _fetch_live_groups(self) -> List[Dict]:
        response = self.session.get(
            LIVE_ROOT_URL,
            headers={
                "User-Agent": self.user_agent,
                "Referer": LIVE_ROOT_URL,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        return _extract_live_groups(getattr(response, "text", ""))

    def _live_channel(self, channel_key: str, alias: str = "") -> Dict:
        referer_alias = alias or channel_key
        response = self.session.get(
            f"{LIVE_CHANNEL_URL}/{quote(str(channel_key), safe='')}",
            headers={
                "User-Agent": self.user_agent,
                "Referer": f"{LIVE_ROOT_URL}channel/{quote(str(referer_alias), safe='')}",
                "Accept": "application/json,text/javascript,*/*;q=0.01",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        return _response_data(response)

    def _public_vod_genre(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path.startswith("vod/"):
            return ""
        slug = path.split("/", 1)[1].strip("/")
        if not slug or "/" in slug:
            return ""
        return unquote(slug)

    def from_keyboard(self, default_text="", header="Search FilmOn"):
        keyboard = xbmc.Keyboard(default_text, header, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return None
