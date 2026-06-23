import json
import re
import sys
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse

import xbmc
import xbmcgui
from bs4 import BeautifulSoup
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://publiciptv.com"
CHANNELS_API_URL = "https://iptv-org.github.io/api/channels.json"
ROUTE_PATH = "/_thearchives_publiciptv"
FANART = Addon().getAddonInfo("fanart")
THUMBNAIL = "resources/media/live_tv.png"


CATEGORIES = [
    "Auto",
    "Animation",
    "Business",
    "Classic",
    "Comedy",
    "Cooking",
    "Culture",
    "Documentary",
    "Education",
    "Entertainment",
    "Family",
    "General",
    "Kids",
    "Legislative",
    "Lifestyle",
    "Movies",
    "Music",
    "News",
    "Outdoor",
    "Relax",
    "Religious",
    "Series",
    "Science",
    "Shop",
    "Sports",
    "Travel",
    "Weather",
    "Other",
]


PINNED_COUNTRIES = [
    ("United States", "us"),
    ("Canada", "ca"),
    ("United Kingdom", "uk"),
    ("Australia", "au"),
    ("Germany", "de"),
    ("France", "fr"),
    ("Japan", "jp"),
]


def _clean_text(value: str) -> str:
    value = unescape(str(value or ""))
    value = value.replace("\ufe0f", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n-")


def _absolute_url(url: str) -> str:
    return urljoin(BASE_URL + "/", url or "")


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


def _category_url(category: str, country_code: str = "us") -> str:
    return f"{BASE_URL}/countries/{quote(country_code.lower(), safe='')}/categories/{quote(category.lower(), safe='')}"


def _channel_url_from_id(channel_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", str(channel_id or "").lower())
    return f"{BASE_URL}/channels/{slug}" if slug else ""


def _listing_route_url(url: str) -> str:
    return _route_url("listing", _absolute_url(url))


def _real_url(url: str) -> str:
    parts = _route_parts(url)
    if parts and parts[0] == "listing" and len(parts) > 1:
        return parts[1]
    return url


def _play_url(stream_url: str, referer: str, title: str = "", thumbnail: str = "", summary: str = "") -> str:
    return "publiciptv://play?" + urlencode({
        "stream": stream_url,
        "referer": referer,
        "title": title,
        "thumbnail": thumbnail,
        "summary": summary,
    })


def _decode_play_url(item: str) -> Dict[str, str]:
    parsed = urlparse(item)
    return {key: values[0] for key, values in parse_qs(parsed.query).items() if values}


def _kodi_header_query(user_agent: str, referer: str) -> str:
    return urlencode({
        "User-Agent": user_agent,
        "Referer": referer,
    })


def _with_kodi_headers(url: str, user_agent: str, referer: str) -> str:
    return f"{url}|{_kodi_header_query(user_agent, referer)}"


def _summary_plot(summary: str) -> str:
    try:
        data = json.loads(summary or "{}")
    except (TypeError, ValueError):
        return _clean_text(summary)

    parts = [
        _clean_text(data.get("description", "")),
        _clean_text(data.get("categories", "")),
        _clean_text(data.get("updated_at", "")),
    ]
    return " | ".join(part for part in parts if part)


def _build_list_item(item: Dict[str, str], user_agent: str) -> xbmcgui.ListItem:
    title = item.get("title") or "Public IPTV"
    referer = item.get("referer") or BASE_URL
    stream_url = _with_kodi_headers(item.get("link", ""), user_agent, referer)
    list_item = xbmcgui.ListItem(title, path=stream_url)
    set_video_info(list_item, {"title": title, "plot": _summary_plot(item.get("summary", ""))})
    thumbnail = item.get("thumbnail", "")
    if thumbnail:
        list_item.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail, "fanart": FANART})
    list_item.setProperty("IsPlayable", "true")
    list_item.setMimeType("application/vnd.apple.mpegurl")
    try:
        list_item.setProperty("inputstream", "inputstream.ffmpegdirect")
        list_item.setProperty("inputstream.ffmpegdirect.is_realtime_stream", "true")
        list_item.setProperty("inputstream.ffmpegdirect.manifest_type", "hls")
        list_item.setProperty("inputstream.ffmpegdirect.stream_headers", _kodi_header_query(user_agent, referer))
        list_item.setContentLookup(False)
    except AttributeError:
        pass
    return list_item


def _item_from_publiciptv_play_url(url: str, fallback: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
    if not isinstance(url, str) or not url.startswith("publiciptv://play?"):
        return None

    fallback = fallback or {}
    data = _decode_play_url(url)
    stream = data.get("stream", "")
    if not stream:
        return None

    return {
        "title": data.get("title") or fallback.get("title") or "Public IPTV",
        "link": stream,
        "referer": data.get("referer") or fallback.get("referer") or BASE_URL,
        "thumbnail": data.get("thumbnail") or fallback.get("thumbnail", ""),
        "summary": data.get("summary") or fallback.get("summary", ""),
    }


class PublicIPTV(Plugin):
    name = "public_iptv"
    priority = 1058

    def __init__(self):
        self.session = DI.session
        self.base_url = BASE_URL
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.user_agent,
            "Referer": f"{BASE_URL}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        if self.session:
            self.session.headers = self.headers

        self.search_url = _route_url("search")
        self.categories_url = _route_url("categories", "us")

    def get_list(self, url: str) -> Optional[str]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        parts = _route_parts(url)
        if parts and parts[0] == "categories":
            return "{}"

        if url == self.search_url:
            query = self.from_keyboard(header="Search Public IPTV")
            if not query:
                sys.exit()
            response = self.session.get(CHANNELS_API_URL, headers=self.headers)
            return json.dumps({"kind": "search", "query": query, "channels": self._load_channels(response.text)})

        response = self.session.get(_real_url(url), headers=self.headers)
        return response.text

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        real_url = _real_url(url)

        if real_url.rstrip("/") == self.base_url:
            return self._root_menu()

        parts = _route_parts(url)
        if parts and parts[0] == "categories":
            country_code = parts[1] if len(parts) > 1 else "us"
            return self._categories_menu(country_code)

        data = self._load_response_json(response)
        if data.get("kind") == "search":
            if "channels" in data:
                return self._parse_search_channels(data.get("channels", []), data.get("query", ""))
            return self._parse_listing(url, BeautifulSoup(data.get("html", ""), "html.parser"), data.get("query", ""))

        soup = BeautifulSoup(response or "", "html.parser")
        path = urlparse(real_url).path
        if path.startswith("/channels/"):
            return self._parse_channel_page(real_url, soup, response or "")
        if path.rstrip("/") == "/countries":
            return self._parse_countries(soup)
        return self._parse_listing(real_url, soup)

    def play_video(self, item: str) -> Optional[bool]:
        if isinstance(item, bytes):
            item = item.decode("utf-8")

        item_data = _item_from_publiciptv_play_url(item)
        if item_data is None:
            try:
                wrapped_item = json.loads(item)
            except (TypeError, ValueError):
                return None
            link = wrapped_item.get("link", "") if isinstance(wrapped_item, dict) else ""
            item_data = _item_from_publiciptv_play_url(link, wrapped_item)

        if item_data is None:
            return None

        stream = item_data.get("link", "")
        if not stream:
            return None

        list_item = _build_list_item(item_data, self.user_agent)
        playback_url = _with_kodi_headers(stream, self.user_agent, item_data.get("referer") or BASE_URL)
        xbmc.Player().play(playback_url, list_item)
        return True

    def _load_response_json(self, response: str) -> Dict[str, str]:
        try:
            data = json.loads(response or "{}")
        except (TypeError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _load_channels(self, response: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(response or "[]")
        except (TypeError, ValueError):
            return []
        return data if isinstance(data, list) else []

    def _root_menu(self) -> List[Dict[str, str]]:
        items = [
            {"type": "dir", "title": "[COLOR deepskyblue]Search[/COLOR]", "link": self.search_url, "thumbnail": THUMBNAIL},
            {"type": "dir", "title": "Countries", "link": f"{BASE_URL}/countries", "thumbnail": THUMBNAIL},
            {"type": "dir", "title": "United States Categories", "link": self.categories_url, "thumbnail": THUMBNAIL},
        ]
        for title, code in PINNED_COUNTRIES:
            items.append({
                "type": "dir",
                "title": title,
                "link": f"{BASE_URL}/countries/{code}",
                "thumbnail": THUMBNAIL,
            })
        return items

    def _categories_menu(self, country_code: str) -> List[Dict[str, str]]:
        return [
            {
                "type": "dir",
                "title": category,
                "link": _category_url(category, country_code),
                "thumbnail": THUMBNAIL,
            }
            for category in CATEGORIES
        ]

    def _parse_countries(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        items = []
        seen = set()
        for anchor in soup.select("a[href^='/countries/'], a[href^='https://publiciptv.com/countries/']"):
            href = _absolute_url(anchor.get("href", ""))
            path = urlparse(href).path
            if "/categories/" in path or path.rstrip("/") == "/countries" or href in seen:
                continue
            title = _clean_text(anchor.get_text(" ", strip=True))
            if not title or title.lower() == "get m3u":
                continue
            seen.add(href)
            items.append({"type": "dir", "title": title, "link": href, "thumbnail": THUMBNAIL})
        return items

    def _parse_listing(self, url: str, soup: BeautifulSoup, query: str = "") -> List[Dict[str, str]]:
        itemlist = []
        seen = set()
        for anchor in soup.select("a[href^='/channels/'], a[href^='https://publiciptv.com/channels/']"):
            item = self._item_from_channel_link(anchor)
            if not item or item["link"] in seen:
                continue
            if query and query.lower() not in item["title"].lower():
                continue
            seen.add(item["link"])
            itemlist.append(item)

        next_link = self._next_page(url, soup)
        if next_link and not query:
            itemlist.append({
                "type": "dir",
                "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                "link": next_link,
                "thumbnail": THUMBNAIL,
            })
        return itemlist

    def _parse_search_channels(self, channels: Any, query: str) -> List[Dict[str, str]]:
        if not isinstance(channels, list):
            return []

        query = _clean_text(query).lower()
        query_words = [word for word in re.split(r"\s+", query) if word]
        itemlist = []
        seen = set()
        for channel in channels:
            if not isinstance(channel, dict):
                continue

            title = _clean_text(channel.get("name", ""))
            channel_id = _clean_text(channel.get("id", ""))
            link = _channel_url_from_id(channel_id)
            if not title or not link or link in seen:
                continue

            searchable = self._searchable_channel_text(channel).lower()
            if query_words and not all(word in searchable for word in query_words):
                continue

            seen.add(link)
            country = _clean_text(channel.get("country", ""))
            categories = self._channel_list_text(channel.get("categories", []))
            itemlist.append({
                "type": "dir",
                "title": title,
                "link": link,
                "thumbnail": THUMBNAIL,
                "summary": " | ".join(part for part in [country, categories] if part),
            })

        return itemlist

    def _searchable_channel_text(self, channel: Dict[str, Any]) -> str:
        parts = [
            channel.get("id", ""),
            channel.get("name", ""),
            self._channel_list_text(channel.get("alt_names", [])),
            self._channel_list_text(channel.get("owners", [])),
            channel.get("network", ""),
            channel.get("country", ""),
            self._channel_list_text(channel.get("categories", [])),
        ]
        return " ".join(_clean_text(part) for part in parts if part)

    def _channel_list_text(self, value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(_clean_text(item) for item in value if _clean_text(item))
        return _clean_text(value)

    def _item_from_channel_link(self, anchor) -> Optional[Dict[str, str]]:
        link = _absolute_url(anchor.get("href", ""))
        if not urlparse(link).path.startswith("/channels/"):
            return None

        image = anchor.select_one("img")
        heading = anchor.select_one("h1, h2, h3, h4, h5")
        raw_text = _clean_text(anchor.get_text(" ", strip=True))
        title = ""
        if heading:
            title = _clean_text(heading.get_text(" ", strip=True))
        if not title and image:
            title = _clean_text(image.get("alt") or image.get("title") or "")
        if not title:
            title = re.sub(r"\s+\d+\s+Streams?.*$", "", raw_text, flags=re.IGNORECASE).strip()
        if not title:
            return None

        summary = raw_text
        if summary.lower().startswith(title.lower()):
            summary = _clean_text(summary[len(title):])
        thumbnail = _absolute_url(image.get("src", "")) if image else ""
        return {
            "type": "dir",
            "title": title,
            "link": link,
            "thumbnail": thumbnail or THUMBNAIL,
            "summary": summary,
        }

    def _parse_channel_page(self, url: str, soup: BeautifulSoup, html: str) -> List[Dict[str, str]]:
        title = self._page_title(soup)
        thumbnail = self._meta_content(soup, 'meta[property="og:image"]')
        description = self._meta_content(soup, 'meta[name="description"]', 'meta[property="og:description"]')
        categories = self._categories_from_page(soup)
        updated_at = self._field_after_dt(soup, "Updated At")
        summary = json.dumps({
            "description": description,
            "categories": categories,
            "updated_at": updated_at,
        })

        itemlist = []
        for index, stream in enumerate(self._extract_streams(html), start=1):
            stream_url = stream.get("address", "")
            if not stream_url:
                continue
            itemlist.append({
                "type": "item",
                "title": f"{title} - Stream {index}",
                "link": _play_url(stream_url, url, f"{title} - Stream {index}", thumbnail, summary),
                "thumbnail": thumbnail or THUMBNAIL,
                "summary": summary,
                "is_playable": "true",
            })
        return itemlist

    def _extract_streams(self, html: str) -> List[Dict[str, str]]:
        normalized = (html or "").replace("\\/", "/").replace('\\"', '"').replace("\\u0026", "&")
        streams = []
        seen = set()
        for block in re.findall(r"\{[^{}]*\"address\"\s*:\s*\"[^\"]+\"[^{}]*\}", normalized):
            address_match = re.search(r"\"address\"\s*:\s*\"([^\"]+)\"", block)
            if not address_match:
                continue
            status = self._json_field(block, "status_code")
            address = address_match.group(1)
            if status and status != "200":
                continue
            if not self._valid_stream(address) or address in seen:
                continue
            seen.add(address)
            streams.append({"address": address, "status_code": status})

        if streams:
            return streams

        for address in re.findall(r"https?://[^\s<>\"'\\]+?\.m3u8[^\s<>\"'\\]*", normalized):
            address = unescape(address)
            if self._valid_stream(address) and address not in seen:
                seen.add(address)
                streams.append({"address": address, "status_code": ""})
        return streams

    def _valid_stream(self, address: str) -> bool:
        parsed = urlparse(address)
        return parsed.scheme in ("http", "https") and ".m3u8" in parsed.path.lower()

    def _json_field(self, block: str, key: str) -> str:
        match = re.search(rf"\"{re.escape(key)}\"\s*:\s*\"([^\"]*)\"", block)
        return match.group(1) if match else ""

    def _page_title(self, soup: BeautifulSoup) -> str:
        title_tag = soup.find("h1")
        title = _clean_text(title_tag.get_text(" ", strip=True) if title_tag else "")
        if title:
            return title
        title = self._meta_content(soup, 'meta[property="og:title"]')
        return _clean_text(title.replace("| Public IPTV", "")) or "Public IPTV"

    def _meta_content(self, soup: BeautifulSoup, *selectors: str) -> str:
        for selector in selectors:
            tag = soup.select_one(selector)
            if tag and tag.get("content"):
                return _absolute_url(tag["content"]) if tag["content"].startswith("/") else tag["content"]
        return ""

    def _categories_from_page(self, soup: BeautifulSoup) -> str:
        categories = []
        for anchor in soup.select("a[href*='/categories/']"):
            category = _clean_text(anchor.get_text(" ", strip=True))
            if category and category.lower() not in [item.lower() for item in categories]:
                categories.append(category)
        return ", ".join(categories)

    def _field_after_dt(self, soup: BeautifulSoup, label: str) -> str:
        for dt in soup.find_all("dt"):
            if _clean_text(dt.get_text(" ", strip=True)).lower() == label.lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    return _clean_text(dd.get_text(" ", strip=True))
        return ""

    def _next_page(self, url: str, soup: BeautifulSoup) -> str:
        for anchor in soup.find_all("a"):
            text = _clean_text(anchor.get_text(" ", strip=True)).lower()
            href = anchor.get("href", "")
            if text == "next" and href:
                return _listing_route_url(href)

        current_page = self._current_page(url)
        best_page = None
        best_link = ""
        for anchor in soup.select("a[href*='page=']"):
            href = _absolute_url(anchor.get("href", ""))
            values = parse_qs(urlparse(href).query).get("page", [])
            if not values:
                continue
            try:
                page_num = int(values[0])
            except ValueError:
                continue
            if page_num > current_page and (best_page is None or page_num < best_page):
                best_page = page_num
                best_link = href
        return _listing_route_url(best_link) if best_link else ""

    def _current_page(self, url: str) -> int:
        values = parse_qs(urlparse(url).query).get("page", [])
        if not values:
            return 0
        try:
            return int(values[0])
        except ValueError:
            return 0

    def from_keyboard(self, default_text="", header="Search Public IPTV"):
        keyboard = xbmc.Keyboard(default_text, header, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return None
