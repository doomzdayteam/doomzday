import json
import re
import sys
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse

import xbmc
import xbmcgui
from bs4 import BeautifulSoup
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://www.documentaryarea.com"
VIDEO_URL = f"{BASE_URL}/videoHD.php"
ROUTE_PATH = "/_thearchives"
FANART = Addon().getAddonInfo("fanart")


GENRES = [
    ("Art", ["Architecture", "Cinematography", "Dance", "Literature", "Music", "Painting", "Photography", "Sculpture"]),
    ("Culture", ["Anthropology and Sociology", "Current Topics", "Ideas and Movements", "Peoples", "Politics", "Religions", "Sports", "Travel"]),
    ("History", ["Prehistory", "Ancient", "Middle Age", "Modern", "Contemporary", "Archaeology", "Biographies", "War"]),
    ("Medicine", ["Diseases", "Drugs", "Genetics", "Health", "Physiology", "Sexuality", "The Brain", "Therapies"]),
    ("Nature", ["Agriculture and Livestock", "Climate", "Ecosystems", "Environmentalism", "Places on the Globe", "The Earth", "The Universe", "Wildlife"]),
    ("Science", ["Astronomy", "Biology", "Chemistry", "Economics", "Geology", "Mathematics", "Palaeontology", "Physics"]),
    ("Technology", ["Computer Science", "Energy", "Engineering", "Industry", "Internet", "Nuclear", "Space", "The Future"]),
]


def _clean_text(value: str) -> str:
    value = unescape(value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


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


def _paged_query_url(path: str, page: str, params: List[tuple]) -> str:
    query = []
    try:
        page_num = int(page or 0)
    except ValueError:
        page_num = 0
    if page_num > 0:
        query.append(("page", str(page_num)))
    query.extend(params)
    return f"{BASE_URL}/{path}?{urlencode(query)}"


def _real_url(url: str) -> str:
    parts = _route_parts(url)
    if not parts:
        return url

    kind = parts[0]
    if kind == "recent":
        page = parts[1] if len(parts) > 1 else "0"
        return _paged_query_url("results-recent.php", page, [("search", "")])
    if kind == "mostviewed":
        page = parts[1] if len(parts) > 1 else "0"
        return _paged_query_url("results-mostviewed.php", page, [("search", "")])
    if kind == "genre" and len(parts) > 1:
        page = parts[2] if len(parts) > 2 else "0"
        return _paged_query_url("results.php", page, [("genre", parts[1])])
    if kind == "search" and len(parts) > 1:
        page = parts[2] if len(parts) > 2 else "0"
        return _paged_query_url("results.php", page, [("search", parts[1])])
    return url


def _meta_content(soup: BeautifulSoup, *selectors: str) -> str:
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag and tag.get("content"):
            return _absolute_url(tag["content"]) if tag["content"].startswith("/") else tag["content"]
    return ""


def _title_from_player_url(url: str) -> str:
    parsed = urlparse(url)
    query_title = parse_qs(parsed.query).get("title", [""])[0]
    if not query_title and parsed.path.startswith("/video/"):
        query_title = parsed.path.replace("/video/", "", 1).strip("/")
    return _clean_text(query_title.replace("+", " "))


def _route_safe_player_url(url: str) -> str:
    absolute = _absolute_url(url)
    title = _title_from_player_url(absolute)
    if title:
        return f"{BASE_URL}/video/{quote(title.replace(' ', '+'), safe='+')}/"
    return absolute


def _canonical_player_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("documentaryarea.com") and parsed.path.startswith("/video/") and not parsed.path.endswith("/"):
        return url + "/"
    return _route_safe_player_url(url)


def _play_url(video_url: str, referer: str) -> str:
    params = {"referer": referer}
    if video_url:
        params["video"] = video_url
    return "documentaryarea://play?" + urlencode(params)


def _decode_play_url(item: str) -> Dict[str, str]:
    parsed = urlparse(item)
    return {key: values[0] for key, values in parse_qs(parsed.query).items() if values}


def _cookie_header(session) -> str:
    cookies = getattr(session, "cookies", None)
    if not cookies:
        return ""
    try:
        items = cookies.items()
    except AttributeError:
        items = ((cookie.name, cookie.value) for cookie in cookies)
    return "; ".join(f"{name}={value}" for name, value in items if name and value)


def _build_playback_url(video_url: str, referer: str, user_agent: str, cookie_header: str = "") -> str:
    referer = _canonical_player_url(referer)
    headers = {"User-Agent": user_agent, "Referer": referer}
    if cookie_header:
        headers["Cookie"] = cookie_header
    headers = urlencode(headers)
    return f"{video_url}|{headers}"


class DocumentaryArea(Plugin):
    name = "documentary_area"
    priority = 1060

    def __init__(self):
        self.session = DI.session
        self.base_url = BASE_URL
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        self.session.headers = {
            "User-Agent": self.user_agent,
            "Referer": self.base_url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.home_url = f"{self.base_url}/home.php"
        self.search_url = _route_url("search")
        self.new_url = _route_url("recent", "0")
        self.views_url = _route_url("mostviewed", "0")
        self.series_url = f"{self.base_url}/series.php"
        self.threed_url = f"{self.base_url}/3D.php"

    def get_list(self, url):
        if url == self.search_url:
            query = self.from_keyboard(header="Search DocumentaryArea")
            if not query:
                sys.exit()
            url = _route_url("search", query, "0")

        if not url.startswith(self.base_url):
            return None

        response = self.session.get(_real_url(url))
        return response.text

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not url.startswith(self.base_url):
            return None

        if url.rstrip("/") == self.base_url:
            return self._root_menu()

        soup = BeautifulSoup(response or "", "html.parser")

        if "/player.php" in url or "/video/" in urlparse(url).path:
            return self._parse_player(url, soup)

        return self._parse_listing(url, soup)

    def play_video(self, item: str) -> Optional[bool]:
        item_data = {}
        if not item.startswith("documentaryarea://play?"):
            try:
                item_data = json.loads(item)
                item = item_data.get("link", "")
            except (TypeError, ValueError):
                return None

        if not item.startswith("documentaryarea://play?"):
            return None

        data = _decode_play_url(item)
        video_url = data.get("video") or ""
        referer = data.get("referer") or self.base_url

        response = None
        try:
            response = self.session.get(referer)
        except Exception as exc:
            xbmc.log(f"[TheArchives][DocumentaryArea] player warmup failed: {exc}", xbmc.LOGERROR)
        if not video_url and response is not None:
            video_url = self._extract_stream_url(getattr(response, "text", ""))
        if not video_url:
            video_url = VIDEO_URL

        stream_url = _build_playback_url(video_url, referer, self.user_agent, _cookie_header(self.session))
        title = item_data.get("title") or _title_from_player_url(referer) or "DocumentaryArea"
        thumbnail = item_data.get("thumbnail", "")
        summary = item_data.get("summary", "")
        list_item = xbmcgui.ListItem(title, path=stream_url)
        set_video_info(list_item, {"title": title, "plot": summary})
        if thumbnail:
            list_item.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail, "fanart": FANART})
        list_item.setProperty("IsPlayable", "true")
        list_item.setMimeType("video/mp4")
        try:
            list_item.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(stream_url, list_item)
        return True

    def _root_menu(self) -> List[Dict[str, str]]:
        items = [
            {"type": "dir", "title": "[COLOR deepskyblue]Search[/COLOR]", "link": self.search_url},
            {"type": "dir", "title": "Home", "link": self.home_url},
            {"type": "dir", "title": "Newly Added", "link": self.new_url},
            {"type": "dir", "title": "Most Viewed", "link": self.views_url},
            {"type": "dir", "title": "All Series", "link": self.series_url},
            {"type": "dir", "title": "3D Documentaries", "link": self.threed_url},
        ]
        for genre, subgenres in GENRES:
            items.append({"type": "dir", "title": f"[COLOR orange]{genre}[/COLOR]", "link": self._genre_url(genre)})
            for subgenre in subgenres:
                items.append({"type": "dir", "title": f"  {subgenre}", "link": self._genre_url(subgenre)})
        return items

    def _parse_listing(self, url: str, soup: BeautifulSoup) -> List[Dict[str, str]]:
        itemlist = []
        seen = set()

        for article in soup.find_all("article"):
            item = self._item_from_article(article)
            if item and item["link"] not in seen:
                seen.add(item["link"])
                itemlist.append(item)

        if not itemlist:
            for card in soup.select(".w3l-movie-gride-agile"):
                item = self._item_from_card(card)
                if item and item["link"] not in seen:
                    seen.add(item["link"])
                    itemlist.append(item)

        next_link = self._next_page(url, soup)
        if next_link:
            itemlist.append({
                "type": "dir",
                "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                "link": next_link,
            })

        return itemlist

    def _parse_player(self, url: str, soup: BeautifulSoup) -> List[Dict[str, str]]:
        title_tag = soup.find("h1")
        title = _clean_text(title_tag.get_text(" ", strip=True) if title_tag else "") or _title_from_player_url(url)
        description_tag = soup.select_one(".comments")
        summary = _clean_text(description_tag.get_text(" ", strip=True) if description_tag else "")
        if not summary:
            summary = _clean_text(_meta_content(soup, 'meta[property="og:description"]', 'meta[name="Description"]'))

        thumbnail = _meta_content(soup, 'meta[property="og:image"]', 'meta[name="thumbnail"]')
        stream_url = self._extract_stream_url(str(soup)) or VIDEO_URL
        item = {
            "type": "item",
            "title": title or "Play Documentary",
            "link": _play_url(stream_url, url),
            "thumbnail": thumbnail,
            "summary": summary,
            "is_playable": "true",
        }
        return [item]

    def _item_from_article(self, article) -> Optional[Dict[str, str]]:
        title_link = article.select_one("h2 a[href*='player.php?title=']")
        if not title_link:
            return None

        link = _route_safe_player_url(title_link.get("href", ""))
        title = _clean_text(title_link.get_text(" ", strip=True))
        image = article.select_one("img")
        thumbnail = _absolute_url(image.get("data-src") or image.get("src") or "") if image else ""
        summary_tag = article.select_one(".comments-space")
        summary = _clean_text(summary_tag.get_text(" ", strip=True) if summary_tag else "")
        details_text = _clean_text(article.get_text(" ", strip=True))
        year_match = re.search(r"\b(19|20)\d{2}\b", details_text)
        genre = self._genre_from_text(details_text)
        meta = " | ".join(part for part in [
            year_match.group(0) if year_match else "",
            genre,
            "HD" if re.search(r"\bHD\b", details_text) else "",
        ] if part)
        if meta and summary:
            summary = f"{meta} | {summary}"
        elif meta:
            summary = meta

        return {
            "type": "item",
            "title": title,
            "link": _play_url("", link),
            "thumbnail": thumbnail,
            "summary": summary,
            "is_playable": "true",
        }

    def _item_from_card(self, card) -> Optional[Dict[str, str]]:
        title_link = card.select_one("a[href*='player.php?title=']")
        if not title_link:
            return None

        image = card.select_one("img")
        title = ""
        if image:
            title = image.get("title") or image.get("alt") or ""
        title = _clean_text(title or title_link.get_text(" ", strip=True))
        if not title:
            return None

        return {
            "type": "item",
            "title": title,
            "link": _play_url("", _route_safe_player_url(title_link.get("href", ""))),
            "thumbnail": _absolute_url((image.get("data-src") or image.get("src") or "") if image else ""),
            "is_playable": "true",
        }

    def _next_page(self, url: str, soup: BeautifulSoup) -> str:
        current_page = self._current_page(url)
        best_page = None
        best_link = ""

        for anchor in soup.select("a[href*='page=']"):
            href = anchor.get("href", "")
            page_values = parse_qs(urlparse(_absolute_url(href)).query).get("page", [])
            if not page_values:
                continue
            try:
                page_num = int(page_values[0])
            except ValueError:
                continue
            if page_num > current_page and (best_page is None or page_num < best_page):
                best_page = page_num
                best_link = _absolute_url(href)

        if best_page is None:
            return ""

        route_parts = _route_parts(url)
        if route_parts:
            kind = route_parts[0]
            if kind in ("recent", "mostviewed"):
                return _route_url(kind, str(best_page))
            if kind == "genre" and len(route_parts) > 1:
                return _route_url("genre", route_parts[1], str(best_page))
            if kind == "search" and len(route_parts) > 1:
                return _route_url("search", route_parts[1], str(best_page))

        return best_link

    def _current_page(self, url: str) -> int:
        route_parts = _route_parts(url)
        if route_parts:
            try:
                if route_parts[0] in ("recent", "mostviewed") and len(route_parts) > 1:
                    return int(route_parts[1])
                if route_parts[0] in ("genre", "search") and len(route_parts) > 2:
                    return int(route_parts[2])
            except ValueError:
                return 0

        values = parse_qs(urlparse(url).query).get("page", [])
        if not values:
            return 0
        try:
            return int(values[0])
        except ValueError:
            return 0

    def _genre_from_text(self, text: str) -> str:
        all_genres = []
        for genre, subgenres in GENRES:
            all_genres.append(genre)
            all_genres.extend(subgenres)
        for genre in all_genres:
            if re.search(rf"\b{re.escape(genre)}\b", text, re.IGNORECASE):
                return genre
        return ""

    def _genre_url(self, genre: str) -> str:
        return _route_url("genre", genre, "0")

    def _extract_stream_url(self, html: str) -> str:
        match = re.search(r'file\s*:\s*["\']([^"\']+video(?:HD)?\.php[^"\']*)["\']', html)
        if match:
            return _absolute_url(match.group(1))
        return ""

    def from_keyboard(self, default_text="", header="Search DocumentaryArea"):
        keyboard = xbmc.Keyboard(default_text, header, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return None
