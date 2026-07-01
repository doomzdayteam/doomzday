"""SuperCartoons VOD provider for The Archives."""

import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Dict, List, Optional
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://www.supercartoons.net"
SERIES_URL = f"{BASE_URL}/serie/series/"
ROUTE_PATH = "/_thearchives"
FANART = Addon().getAddonInfo("fanart")


def _class_names(attrs) -> List[str]:
    return dict(attrs).get("class", "").split()


def _clean_text(value: str) -> str:
    value = unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _absolute_url(value: str) -> str:
    return urljoin(f"{BASE_URL}/", unescape(str(value or ""))) if value else ""


def _route_url(kind: str, *parts: str) -> str:
    encoded = [quote(str(part), safe="") for part in (kind,) + parts]
    return f"{BASE_URL}{ROUTE_PATH}/" + "/".join(encoded)


def _route_parts(url: str) -> List[str]:
    path = urlparse(url).path
    prefix = f"{ROUTE_PATH}/"
    if not path.startswith(prefix):
        return []
    return [unquote(part) for part in path[len(prefix):].split("/") if part]


def _is_provider_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except (TypeError, ValueError):
        return False
    return parsed.scheme in ("http", "https") and parsed.netloc == "www.supercartoons.net"


def _json_data(value: str) -> Dict:
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
        try:
            data = json.loads(item)
        except (TypeError, ValueError):
            data = {}
    link = data.get("link", "") if isinstance(data, dict) else ""
    if not link and isinstance(item, str):
        link = item
    return data if isinstance(data, dict) else {}, str(link or "")


def _is_cartoon_url(url: str) -> bool:
    return _is_provider_url(url) and "/cartoon/" in urlparse(url).path


def _with_kodi_headers(url: str, user_agent: str) -> str:
    headers = (
        f"User-Agent={quote(user_agent, safe='')}"
        f"&Referer={quote(f'{BASE_URL}/', safe='')}"
    )
    return f"{url}|{headers}" if url else ""


class _CardParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards = []
        self._article_depth = 0
        self._card = None
        self._title_depth = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "article":
            if self._article_depth == 0:
                self._card = {"title": "", "url": "", "thumbnail": ""}
            self._article_depth += 1
            return
        if not self._article_depth or self._card is None:
            return
        if tag == "a" and not self._card["url"]:
            self._card["url"] = values.get("href", "")
        elif tag == "img" and not self._card["thumbnail"]:
            self._card["thumbnail"] = values.get("src") or values.get("data-src", "")
        elif tag == "h3" and "title" in _class_names(attrs):
            self._title_depth = 1
        elif self._title_depth:
            self._title_depth += 1

    def handle_endtag(self, tag):
        if tag == "article" and self._article_depth:
            self._article_depth -= 1
            if self._article_depth == 0 and self._card is not None:
                self.cards.append(self._card)
                self._card = None
                self._title_depth = 0
            return
        if self._title_depth:
            self._title_depth -= 1

    def handle_data(self, data):
        if self._title_depth and self._card is not None:
            self._card["title"] += data


class _DetailsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.thumbnail = ""
        self.h1 = ""
        self.plot = ""
        self.genres = []
        self.cast = []
        self._h1_depth = 0
        self._plot_depth = 0
        self._list_target = None
        self._anchor_depth = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = _class_names(attrs)
        if tag == "meta":
            prop = values.get("property", "")
            if prop == "og:title":
                self.title = values.get("content", "")
            elif prop == "og:image":
                self.thumbnail = values.get("content", "")
        elif tag == "h1":
            self._h1_depth = 1
        elif self._h1_depth:
            self._h1_depth += 1

        if "post-content" in classes:
            self._plot_depth = 1
        elif self._plot_depth:
            self._plot_depth += 1

        if tag == "ul" and "single-video-categories" in classes:
            self._list_target = self.genres
        elif tag == "ul" and "single-video-tags" in classes:
            self._list_target = self.cast
        elif tag == "a" and self._list_target is not None:
            self._anchor_depth = 1
        elif self._anchor_depth:
            self._anchor_depth += 1

    def handle_endtag(self, tag):
        if self._h1_depth:
            self._h1_depth -= 1
        if self._plot_depth:
            self._plot_depth -= 1
        if self._anchor_depth:
            self._anchor_depth -= 1
        if tag == "ul":
            self._list_target = None
            self._anchor_depth = 0

    def handle_data(self, data):
        text = _clean_text(data)
        if not text:
            return
        if self._h1_depth:
            self.h1 += (" " if self.h1 else "") + text
        if self._plot_depth:
            self.plot += (" " if self.plot else "") + text
        if self._anchor_depth and self._list_target is not None:
            self._list_target.append(text)


def _parse_cards(html: str, allow_series: bool = False) -> List[Dict[str, str]]:
    parser = _CardParser()
    parser.feed(html or "")
    required_path = "/serie/" if allow_series else "/cartoon/"
    seen = set()
    results = []
    for card in parser.cards:
        url = _absolute_url(card.get("url", ""))
        title = _clean_text(card.get("title", ""))
        if required_path not in urlparse(url).path or not title or url in seen:
            continue
        seen.add(url)
        results.append({
            "title": title,
            "url": url,
            "thumbnail": _absolute_url(card.get("thumbnail", "")),
        })
    return results


def _parse_series(html: str) -> List[Dict[str, str]]:
    return _parse_cards(html, allow_series=True)


def _extract_stream(html: str) -> str:
    match = re.search(r"\bfile\s*:\s*[\"']([^\"']+)[\"']", html or "", re.I)
    return unescape(match.group(1)).strip() if match else ""


def _parse_details(html: str) -> Dict[str, object]:
    parser = _DetailsParser()
    parser.feed(html or "")
    return {
        "title": _clean_text(parser.title or parser.h1),
        "thumbnail": _absolute_url(parser.thumbnail),
        "plot": _clean_text(parser.plot),
        "genres": [_clean_text(value) for value in parser.genres if _clean_text(value)],
        "cast": [_clean_text(value) for value in parser.cast if _clean_text(value)],
        "stream": _extract_stream(html),
    }


def _next_page_number(html: str) -> Optional[int]:
    match = re.search(
        r'<a[^>]+class=["\'][^"\']*\bnext\b[^"\']*["\'][^>]+href=["\']([^"\']+)',
        html or "",
        re.I,
    )
    if not match:
        match = re.search(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]+class=["\'][^"\']*\bnext\b',
            html or "",
            re.I,
        )
    if not match:
        return None
    values = parse_qs(urlparse(unescape(match.group(1))).query).get("paged") or []
    try:
        return int(values[0])
    except (IndexError, TypeError, ValueError):
        return None


class SuperCartoons(Plugin):
    name = "supercartoons"
    priority = 1060

    def __init__(self):
        self.session = DI.session
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        if self.session:
            headers = getattr(self.session, "headers", None)
            if isinstance(headers, dict):
                headers.update({"User-Agent": self.user_agent, "Referer": f"{BASE_URL}/"})

    def from_keyboard(self, default_text: str = "", header: str = "Search SuperCartoons"):
        keyboard = xbmc.Keyboard(default_text, header, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return None

    def _fetch(self, url: str) -> str:
        if not self.session:
            return ""
        try:
            response = self.session.get(url)
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            return str(getattr(response, "text", "") or "")
        except Exception:
            return ""

    def _fetch_strict(self, url: str) -> str:
        if not self.session:
            raise RuntimeError("HTTP session is unavailable")
        response = self.session.get(url)
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        return str(getattr(response, "text", "") or "")

    def get_list(self, url: str) -> Optional[str]:
        if not _is_provider_url(url):
            return None
        if url.rstrip("/") == BASE_URL:
            return json.dumps({"kind": "root"})
        if url.rstrip("/") == SERIES_URL.rstrip("/"):
            return json.dumps({"kind": "series_index", "html": self._fetch(SERIES_URL)})

        parts = _route_parts(url)
        if not parts:
            return None
        kind = parts[0]
        if kind == "search" and len(parts) == 1:
            query = self.from_keyboard(header="Search SuperCartoons")
            if not query:
                raise SystemExit()
            return json.dumps({
                "kind": "redirect",
                "link": _route_url("search", query, "1"),
            })

        route_value = ""
        if kind == "latest":
            page = self._page_number(parts, 1)
            source_url = f"{BASE_URL}/" if page == 1 else f"{BASE_URL}/?paged={page}"
        elif kind == "search" and len(parts) >= 2:
            route_value = parts[1]
            page = self._page_number(parts, 2)
            query = [("s", route_value)] if page == 1 else [("paged", str(page)), ("s", route_value)]
            source_url = f"{BASE_URL}/?{urlencode(query)}"
        elif kind == "series" and len(parts) >= 2:
            route_value = parts[1]
            if not _is_provider_url(route_value) or "/serie/" not in urlparse(route_value).path:
                return None
            page = self._page_number(parts, 2)
            source_url = route_value if page == 1 else f"{route_value}?paged={page}"
        else:
            return None

        return json.dumps({
            "kind": "listing",
            "html": self._fetch(source_url),
            "source_url": source_url,
            "route_kind": kind,
            "route_value": route_value,
            "page": page,
        })

    @staticmethod
    def _page_number(parts: List[str], index: int) -> int:
        try:
            return max(1, int(parts[index]))
        except (IndexError, TypeError, ValueError):
            return 1

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not _is_provider_url(url):
            return None
        data = _json_data(response)
        kind = data.get("kind")
        if kind == "root":
            return self._root_items()
        if kind == "redirect":
            return [{
                "type": "dir",
                "title": "[COLOR deepskyblue]Search Results[/COLOR]",
                "link": str(data.get("link") or ""),
            }]
        if kind == "series_index":
            return self._series_items(str(data.get("html") or ""))
        if kind == "listing":
            return self._listing_items(data)
        return self._empty_items()

    def play_video(self, item: str) -> Optional[bool]:
        data, link = _decode_item(item)
        if not _is_cartoon_url(link):
            return None
        try:
            details = _parse_details(self._fetch_strict(link))
        except Exception as exc:
            xbmc.log(
                f"[TheArchives][SuperCartoons] resolve failed: {exc}",
                xbmc.LOGERROR,
            )
            xbmcgui.Dialog().notification(
                "SuperCartoons",
                "Failed to resolve stream",
                xbmcgui.NOTIFICATION_WARNING,
                3000,
            )
            return True

        stream = str(details.get("stream") or "")
        if not stream:
            xbmcgui.Dialog().notification(
                "SuperCartoons",
                "Stream not available",
                xbmcgui.NOTIFICATION_WARNING,
                3000,
            )
            return True

        play_url = _with_kodi_headers(stream, self.user_agent)
        title = _clean_text(details.get("title") or data.get("title") or "SuperCartoons")
        thumbnail = str(details.get("thumbnail") or data.get("thumbnail") or "")
        list_item = xbmcgui.ListItem(title, path=play_url)
        list_item.setProperty("IsPlayable", "true")
        art = {"fanart": FANART}
        if thumbnail:
            art.update({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail})
        list_item.setArt(art)
        set_video_info(list_item, {
            "title": title,
            "plot": str(details.get("plot") or data.get("summary") or ""),
            "genre": details.get("genres") or [],
            "cast": details.get("cast") or [],
        })
        list_item.setMimeType("video/mp4")
        try:
            list_item.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(play_url, list_item)
        return True

    def _root_items(self) -> List[Dict[str, str]]:
        return [
            {
                "type": "dir",
                "title": "[COLOR deepskyblue]Search[/COLOR]",
                "link": _route_url("search"),
                "thumbnail": "resources/media/movies.png",
                "summary": "Search the SuperCartoons catalog.",
            },
            {
                "type": "dir",
                "title": "Latest Cartoons",
                "link": _route_url("latest", "1"),
                "thumbnail": "resources/media/movies.png",
                "summary": "Browse the latest cartoons.",
            },
            {
                "type": "dir",
                "title": "Series",
                "link": SERIES_URL,
                "thumbnail": "resources/media/tv_shows.png",
                "summary": "Browse all SuperCartoons series.",
            },
        ]

    def _series_items(self, html: str) -> List[Dict[str, str]]:
        items = [
            {
                "type": "dir",
                "title": card["title"],
                "link": _route_url("series", card["url"], "1"),
                "thumbnail": card["thumbnail"],
                "summary": f"Browse {card['title']} cartoons.",
            }
            for card in _parse_series(html)
        ]
        return items or self._empty_items("No SuperCartoons series found")

    def _listing_items(self, data: Dict) -> List[Dict[str, str]]:
        html = str(data.get("html") or "")
        items = [
            {
                "type": "item",
                "title": card["title"],
                "link": card["url"],
                "thumbnail": card["thumbnail"],
                "summary": "",
                "is_playable": "true",
            }
            for card in _parse_cards(html)
        ]
        next_page = _next_page_number(html)
        if next_page:
            route_kind = str(data.get("route_kind") or "latest")
            route_value = str(data.get("route_value") or "")
            parts = (route_value, str(next_page)) if route_value else (str(next_page),)
            items.append({
                "type": "dir",
                "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                "link": _route_url(route_kind, *parts),
            })
        return items or self._empty_items()

    @staticmethod
    def _empty_items(message: str = "No SuperCartoons titles found") -> List[Dict[str, str]]:
        return [{
            "type": "dir",
            "title": f"[COLOR grey]{message}[/COLOR]",
            "link": BASE_URL,
        }]
