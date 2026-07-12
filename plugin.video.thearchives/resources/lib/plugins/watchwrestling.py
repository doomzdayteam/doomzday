"""WatchWrestling VOD provider for The Archives."""

import base64
import json
import re
from html import unescape
from typing import Dict, List
from urllib.parse import parse_qsl, quote, unquote, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://watchwrestling.ae"
ROUTE_PATH = "/_thearchives_watchwrestling"
PROVIDER_HOSTS = {"watchwrestling.ae", "www.watchwrestling.ae"}
SNAPTIK_HOSTS = {"snaptik.ae", "www.snaptik.ae"}
FASTVID_HOSTS = {"fastvid.xyz", "www.fastvid.xyz"}
BLOCKED_SOURCE_HOSTS = {"dailymotion.com", "www.dailymotion.com", "dai.ly"}
BLOCKED_SOURCE_TEXT = ("dailymotion", "daily motion")
M2LIST_HOSTS = {"m2list.com", "www.m2list.com"}
NEWSONOMICS_HOSTS = {"newsonomics.top", "www.newsonomics.top"}
OK_HOSTS = {"ok.ru", "www.ok.ru", "m.ok.ru", "mobile.ok.ru"}
FANART = Addon().getAddonInfo("fanart")


def _clean_text(value: str) -> str:
    value = unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _absolute_url(value: str, base: str = BASE_URL) -> str:
    value = unescape(str(value or "")).strip()
    if not value:
        return ""
    if value.startswith("//"):
        return "https:" + value
    return urljoin(f"{base.rstrip('/')}/", value)


def _clean_url_query(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if not parsed.query:
        return str(url or "").strip()
    query = urlencode(
        [(key.strip(), value.strip()) for key, value in parse_qsl(parsed.query, keep_blank_values=True)]
    )
    return urlunparse(parsed._replace(query=query))


def _route_url(kind: str, *parts: str) -> str:
    encoded = [quote(str(part), safe="") for part in (kind,) + parts]
    return f"{BASE_URL}{ROUTE_PATH}/" + "/".join(encoded)


def _route_parts(url: str) -> List[str]:
    path = urlparse(str(url or "")).path
    prefix = f"{ROUTE_PATH}/"
    if not path.startswith(prefix):
        return []
    return [unquote(part) for part in path[len(prefix):].split("/") if part]


def _json_data(value: str) -> Dict:
    try:
        data = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _is_provider_url(url: str) -> bool:
    try:
        parsed = urlparse(str(url or ""))
    except (TypeError, ValueError):
        return False
    return parsed.scheme in ("http", "https") and parsed.hostname in PROVIDER_HOSTS


def _is_post_url(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    path = parsed.path.strip("/")
    if not _is_provider_url(url) or not path:
        return False
    blocked = (
        "author/",
        "category/",
        "home",
        "dmca",
        "privacy",
        ROUTE_PATH.strip("/"),
        "page/",
        "wp-",
    )
    return not any(path.startswith(value) for value in blocked)


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


def _kodi_header_query(headers: Dict[str, str]) -> str:
    values = [
        f"{key}={quote(str(value), safe='')}"
        for key, value in headers.items()
        if value
    ]
    return "&".join(values)


def _with_kodi_headers(url: str, headers: Dict[str, str]) -> str:
    header_query = _kodi_header_query(headers)
    return f"{url}|{header_query}" if header_query else url


def _merge_headers(*groups: Dict[str, str]) -> Dict[str, str]:
    headers = {}
    for group in groups:
        if isinstance(group, dict):
            headers.update({key: str(value) for key, value in group.items() if value})
    return headers


def _is_blocked_source(url: str, *labels: str) -> bool:
    text = " ".join([str(url or ""), unquote(str(url or ""))] + [str(label or "") for label in labels]).lower()
    if any(value in text for value in BLOCKED_SOURCE_TEXT):
        return True
    try:
        host = (urlparse(str(url or "")).hostname or "").lower()
    except (TypeError, ValueError):
        return False
    return host in BLOCKED_SOURCE_HOSTS


def _log(message: str, level=None):
    try:
        xbmc.log(f"[TheArchives][WatchWrestling] {message}", level if level is not None else xbmc.LOGINFO)
    except Exception:
        pass


def _normalize_embed_url(value: str) -> str:
    url = _clean_url_query(_absolute_url(value))
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in OK_HOSTS:
        match = re.match(r"/videoembed/([\d-]+)", parsed.path)
        if match:
            return f"https://ok.ru/video/{match.group(1)}"
    return url


def _parse_categories(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows = []
    seen = set()
    selectors = (
        "#main-nav ul.menu > li > a",
        "ul#menu-main-menu > li > a",
        "nav ul.menu > li > a",
    )
    for selector in selectors:
        for anchor in soup.select(selector):
            url = _absolute_url(anchor.get("href", ""))
            title = _clean_text(anchor.get_text(" ", strip=True))
            path = urlparse(url).path.strip("/").lower()
            if not title or not _is_provider_url(url) or url in seen:
                continue
            if title.lower() == "home" or path.startswith(("home", "dmca", "privacy")):
                continue
            seen.add(url)
            rows.append({"title": title, "url": url})
        if rows:
            break
    return rows


def _parse_listing_cards(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows = []
    seen = set()
    for card in soup.select("div.item-post"):
        anchor = card.select_one("h1.entry-title a, h2.entry-title a, a.clip-link")
        url = _absolute_url(anchor.get("href", "")) if anchor else ""
        title = _clean_text(
            (anchor.get("title") or anchor.get_text(" ", strip=True)) if anchor else ""
        )
        if title.lower().startswith("permalink to "):
            title = title[13:]
        if not title or not _is_post_url(url) or url in seen:
            continue
        seen.add(url)
        image = card.select_one(".thumb img, img")
        thumbnail = ""
        if image:
            thumbnail = next(
                (
                    image.get(key)
                    for key in ("data-src", "src")
                    if image.get(key) and not image.get(key).startswith("data:")
                ),
                "",
            )
        summary_node = card.select_one(".entry-summary")
        time_node = card.select_one("time, .time")
        rows.append({
            "title": title,
            "url": url,
            "thumbnail": _absolute_url(thumbnail),
            "summary": _clean_text(summary_node.get_text(" ", strip=True) if summary_node else ""),
            "date": _clean_text(time_node.get_text(" ", strip=True) if time_node else ""),
        })
    return rows


def _next_page_url(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    node = soup.select_one('link[rel="next"]') or soup.select_one("a.next")
    url = _absolute_url(node.get("href", "")) if node else ""
    return url if _is_provider_url(url) else ""


def _textarea_markup(html: str) -> str:
    textarea = re.search(r"<textarea\b[^>]*>(?P<markup>.*?episodeRepeater.*?)</textarea>", html or "", re.S)
    if textarea:
        return unescape(
            textarea.group("markup")
            .replace(r"\/", "/")
            .replace(r"\"", '"')
            .replace(r"\'", "'")
        )
    match = re.search(
        r"append\(\s*\"(?P<markup><textarea\b.*?</textarea>)\"\s*\)",
        html or "",
        re.S,
    )
    if not match:
        return html or ""
    markup = match.group("markup")
    markup = markup.replace(r"\/", "/").replace(r"\"", '"').replace(r"\'", "'")
    return unescape(markup)


def _parse_post_details(html: str) -> Dict[str, object]:
    soup = BeautifulSoup(html or "", "html.parser")
    title_node = soup.select_one("h1.entry-title") or soup.select_one("h1")
    image_node = soup.select_one('meta[property="og:image"]')
    summary_node = soup.select_one('meta[property="og:description"]')
    source_soup = BeautifulSoup(_textarea_markup(html), "html.parser")
    sources = []
    seen = set()
    for block in source_soup.select(".episodeRepeater"):
        heading = _clean_text(block.select_one("h1").get_text(" ", strip=True) if block.select_one("h1") else "Source")
        if "pvp" in heading.lower():
            continue
        for anchor in block.select("a[href]"):
            link = _absolute_url(anchor.get("href", ""))
            label = _clean_text(anchor.get_text(" ", strip=True))
            if not link or link in seen or _is_blocked_source(link, heading, label):
                continue
            query = dict(parse_qsl(urlparse(link).query, keep_blank_values=True))
            if "live streaming" in heading.lower() or (query.get("host") or "").strip().lower() == "sawlive":
                continue
            seen.add(link)
            sources.append({
                "title": " - ".join(value for value in (heading, label) if value),
                "url": link,
            })
    if not sources:
        for frame in source_soup.select("iframe[src], iframe[data-src]"):
            link = _normalize_embed_url(frame.get("src") or frame.get("data-src") or "")
            if link and link not in seen and not _is_blocked_source(link):
                seen.add(link)
                sources.append({"title": "Video", "url": link})
    return {
        "title": _clean_text(title_node.get_text(" ", strip=True)) if title_node else "",
        "thumbnail": _absolute_url(image_node.get("content", "")) if image_node else "",
        "summary": _clean_text(summary_node.get("content", "")) if summary_node else "",
        "sources": sources,
    }

class WatchWrestling(Plugin):
    name = "watchwrestling"
    priority = 1066

    def __init__(self):
        self.session = DI.session
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        headers = getattr(self.session, "headers", None)
        if isinstance(headers, dict):
            headers.update({"User-Agent": self.user_agent, "Referer": f"{BASE_URL}/"})

    def from_keyboard(self, default_text: str = "", header: str = "Search WatchWrestling"):
        keyboard = xbmc.Keyboard(default_text, header, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return None

    def _fetch(self, url: str, referer: str = "") -> str:
        if not self.session:
            return ""
        try:
            headers = {"User-Agent": self.user_agent, "Referer": referer or f"{BASE_URL}/"}
            response = self.session.get(url, headers=headers, timeout=20)
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            return str(getattr(response, "text", "") or "")
        except Exception as exc:
            xbmc.log(f"[TheArchives][WatchWrestling] fetch failed for {url}: {exc}", xbmc.LOGERROR)
            return ""

    @staticmethod
    def _page(parts: List[str], index: int = 1) -> int:
        try:
            return max(1, int(parts[index]))
        except (IndexError, TypeError, ValueError):
            return 1

    def get_list(self, url: str):
        if not _is_provider_url(url):
            return None
        if url.rstrip("/") == BASE_URL:
            return json.dumps({"kind": "root"})
        parts = _route_parts(url)
        if not parts:
            return None
        kind = parts[0]
        if kind == "search" and len(parts) == 1:
            query = self.from_keyboard()
            if not query:
                raise SystemExit()
            return json.dumps({"kind": "redirect", "link": _route_url("search", query, "1")})
        if kind == "latest":
            page = self._page(parts)
            source_url = f"{BASE_URL}/" if page == 1 else f"{BASE_URL}/page/{page}/"
            return json.dumps({"kind": "listing", "html": self._fetch(source_url)})
        if kind == "search" and len(parts) >= 2:
            query = parts[1]
            page = self._page(parts, 2)
            source_url = (
                f"{BASE_URL}/?{urlencode({'s': query})}"
                if page == 1
                else f"{BASE_URL}/page/{page}/?{urlencode({'s': query})}"
            )
            return json.dumps({"kind": "listing", "html": self._fetch(source_url)})
        if kind == "categories":
            return json.dumps({"kind": "categories", "html": self._fetch(f"{BASE_URL}/")})
        if kind == "listing" and len(parts) >= 2:
            source_url = parts[1]
            if not _is_provider_url(source_url):
                return None
            return json.dumps({
                "kind": "listing",
                "html": self._fetch(source_url),
                "source_url": source_url,
            })
        if kind == "post" and len(parts) >= 2:
            post_url = parts[1]
            if not _is_post_url(post_url):
                return None
            return json.dumps({"kind": "post", "html": self._fetch(post_url)})
        return None

    def parse_list(self, url: str, response: str):
        if not _is_provider_url(url):
            return None
        data = _json_data(response)
        kind = data.get("kind")
        if kind == "root":
            return [
                {"type": "dir", "title": "[COLOR deepskyblue]Search[/COLOR]", "link": _route_url("search"), "thumbnail": "resources/media/movies.png", "summary": "Search WatchWrestling shows."},
                {"type": "dir", "title": "Latest Shows", "link": _route_url("latest", "1"), "thumbnail": "resources/media/movies.png", "summary": "Browse the latest wrestling and combat sports shows."},
                {"type": "dir", "title": "Categories", "link": _route_url("categories"), "thumbnail": "resources/media/tv_shows.png", "summary": "Browse WWE, AEW, ROH, UFC, and other categories."},
            ]
        if kind == "redirect":
            return [{"type": "dir", "title": "[COLOR deepskyblue]Search Results[/COLOR]", "link": str(data.get("link") or "")}]
        if kind == "categories":
            rows = [
                {
                    "type": "dir",
                    "title": row["title"],
                    "link": _route_url("listing", row["url"]),
                    "thumbnail": "resources/media/tv_shows.png",
                    "summary": f"Browse {row['title']} shows.",
                }
                for row in _parse_categories(str(data.get("html") or ""))
            ]
            return rows or self._empty_items("No WatchWrestling categories found")
        if kind == "listing":
            return self._listing_items(str(data.get("html") or ""))
        if kind == "post":
            route = _route_parts(url)
            post_url = route[1] if len(route) >= 2 else ""
            details = _parse_post_details(str(data.get("html") or ""))
            rows = [
                {
                    "type": "item",
                    "title": source["title"],
                    "link": source["url"],
                    "thumbnail": details["thumbnail"],
                    "summary": details["summary"] or details["title"],
                    "post_url": post_url,
                    "is_playable": "true",
                }
                for source in details["sources"]
            ]
            return rows or self._empty_items("No WatchWrestling sources found")
        return self._empty_items()

    def play_video(self, item: str):
        data, link = _decode_item(item)
        resolved = self._resolve_source(link, data)
        if resolved.get("delegate") == "ok_ru":
            try:
                from .ok_ru import OKRu

                ok_item = dict(data)
                ok_item["link"] = resolved["url"]
                return OKRu().play_video(json.dumps(ok_item))
            except Exception as exc:
                xbmc.log(f"[TheArchives][WatchWrestling] OK.ru delegate failed: {exc}", xbmc.LOGERROR)
                xbmcgui.Dialog().notification("WatchWrestling", "OK.ru source unavailable", xbmcgui.NOTIFICATION_WARNING, 3000)
                return True
        if not resolved.get("url"):
            _log(f"source unavailable for {link}", getattr(xbmc, "LOGERROR", None))
            xbmcgui.Dialog().notification("WatchWrestling", "Source unavailable", xbmcgui.NOTIFICATION_WARNING, 3000)
            return True

        if str(resolved.get("local_hls") or "").lower() == "true":
            headers = {}
        else:
            headers = {
                "User-Agent": self.user_agent,
                "Referer": str(resolved.get("referer") or f"{BASE_URL}/"),
                "Cookie": str(resolved.get("cookie") or ""),
            }
            headers = _merge_headers(headers, resolved.get("headers") or {})
        protocol = str(resolved.get("protocol") or "")
        if (
            str(resolved.get("local_hls") or "").lower() == "true"
            or protocol == "hls_adaptive"
            or str(resolved.get("headers_only") or "").lower() == "true"
        ):
            play_url = str(resolved["url"])
        else:
            play_url = _with_kodi_headers(str(resolved["url"]), headers)
        _log(
            "playing "
            + f"protocol={protocol or 'direct'} "
            + f"host={(urlparse(str(resolved['url'])).hostname or '')} "
            + f"title={_clean_text(data.get('title') or '')}"
        )
        title = _clean_text(data.get("title") or "WatchWrestling")
        thumbnail = str(data.get("thumbnail") or "")
        list_item = xbmcgui.ListItem(title, path=play_url)
        list_item.setProperty("IsPlayable", "true")
        art = {"fanart": FANART}
        if thumbnail:
            art.update({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail})
        list_item.setArt(art)
        set_video_info(list_item, {
            "title": title,
            "plot": str(data.get("summary") or ""),
        })
        if protocol in ("hls", "hls_adaptive"):
            list_item.setMimeType("application/vnd.apple.mpegurl")
        elif protocol == "dash":
            list_item.setMimeType("application/dash+xml")
        else:
            list_item.setMimeType("video/mp4")
        try:
            if protocol == "hls":
                if str(resolved.get("native_hls") or "").lower() != "true":
                    list_item.setProperty("inputstream", "inputstream.ffmpegdirect")
                    list_item.setProperty("inputstream.ffmpegdirect.manifest_type", "hls")
                    list_item.setProperty(
                        "inputstream.ffmpegdirect.stream_headers",
                        _kodi_header_query(headers),
                    )
            elif protocol == "hls_adaptive":
                header_query = _kodi_header_query(headers)
                list_item.setProperty("inputstream", "inputstream.adaptive")
                list_item.setProperty("inputstream.adaptive.manifest_type", "hls")
                list_item.setProperty("inputstream.adaptive.manifest_headers", header_query)
                list_item.setProperty("inputstream.adaptive.stream_headers", header_query)
                list_item.setProperty("inputstream.adaptive.max_bandwidth", "0")
            list_item.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(play_url, list_item)
        return True

    def _listing_items(self, html: str):
        rows = [
            {
                "type": "dir",
                "title": card["title"],
                "link": _route_url("post", card["url"]),
                "thumbnail": card["thumbnail"],
                "summary": " | ".join(value for value in (card["date"], card["summary"]) if value),
            }
            for card in _parse_listing_cards(html)
        ]
        next_url = _next_page_url(html)
        if next_url:
            rows.append({
                "type": "dir",
                "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                "link": _route_url("listing", next_url),
            })
        return rows or self._empty_items()

    def _resolve_source(self, url: str, data: Dict) -> Dict[str, str]:
        url = _normalize_embed_url(url)
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host in SNAPTIK_HOSTS:
            html = self._fetch(url, referer=str(data.get("post_url") or f"{BASE_URL}/"))
            iframe = self._first_iframe_url(html, url)
            if iframe:
                return self._resolve_source(iframe, data)
        if host in FASTVID_HOSTS:
            return self._resolve_fastvid(url)
        if host in M2LIST_HOSTS:
            return self._resolve_m2list(url)
        if host in NEWSONOMICS_HOSTS:
            return self._resolve_newsonomics(url)
        if host in OK_HOSTS:
            return {"url": url, "delegate": "ok_ru"}
        if _is_blocked_source(url):
            return {}
        if parsed.path.lower().endswith((".m3u8", ".mpd", ".mp4")):
            protocol = "hls" if parsed.path.lower().endswith(".m3u8") else "dash" if parsed.path.lower().endswith(".mpd") else "mp4"
            return {"url": url, "protocol": protocol, "referer": f"{BASE_URL}/", "cookie": ""}
        return {}

    def _resolve_fastvid(self, url: str) -> Dict[str, str]:
        html = self._fetch(url, referer="https://snaptik.ae/")
        file_match = re.search(r"file\s*:\s*window\.atob\(\s*['\"]([^'\"]+)", html)
        if file_match:
            try:
                media = base64.b64decode(file_match.group(1)).decode("utf-8")
            except Exception:
                media = ""
            if media:
                protocol = "hls" if ".m3u8" in media.lower() else "dash" if ".mpd" in media.lower() else "mp4"
                if protocol == "hls" and not self._valid_hls(media, url):
                    return {}
                return {
                    "url": media,
                    "protocol": protocol,
                    "referer": url,
                    "cookie": "",
                }
        iframe = self._first_iframe_url(html, url)
        if iframe:
            return self._resolve_source(iframe, {})
        return {}

    def _resolve_m2list(self, url: str) -> Dict[str, str]:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        mirror = (query.get("mirror") or "").strip()
        mainid = (query.get("mainid") or "").strip()
        if not mirror or not mainid:
            return {}
        pass_url = (
            "https://www.m2list.com/2023update/embed_pass.php?"
            + urlencode({
                "mirror": mirror,
                "mainid": mainid,
                "headlines": "undefined",
                "browser": "Chrome",
                "dimension": "calpheon",
                "country": "US",
                "referrer": "watchwrestling.ae",
            })
        )
        html = self._fetch(pass_url, referer=url)
        iframe = self._first_iframe_url(html, pass_url)
        if iframe and "Mirrorid" not in iframe and "Videoid" not in iframe:
            return self._resolve_source(iframe, {})
        newsonomics = (
            "https://www.newsonomics.top/embed2.php?"
            + urlencode({
                "mirror": mirror,
                "mainid": mainid,
                "headlines": "undefined",
                "browser": "Chrome",
                "dimension": "calpheon",
                "country": "US",
                "referrer": "watchwrestling.ae",
            })
        )
        return self._resolve_newsonomics(newsonomics)

    def _resolve_newsonomics(self, url: str) -> Dict[str, str]:
        html = self._fetch(url, referer="https://www.m2list.com/")
        iframe = self._first_iframe_url(html, url)
        if iframe and "Mirrorid" not in iframe and "Videoid" not in iframe:
            return self._resolve_source(iframe, {})
        return {}

    def _first_iframe_url(self, html: str, base: str) -> str:
        soup = BeautifulSoup(html or "", "html.parser")
        frame = soup.select_one("iframe[data-src], iframe[src]")
        if not frame:
            return ""
        return _normalize_embed_url(_absolute_url(frame.get("data-src") or frame.get("src") or "", base=base))

    def _valid_hls(self, url: str, referer: str, cookie: str = "", extra_headers: Dict[str, str] = None, session=None) -> bool:
        session = session or self.session
        if not session:
            return False
        try:
            headers = _merge_headers({"User-Agent": self.user_agent, "Referer": referer}, extra_headers or {})
            if cookie:
                headers["Cookie"] = cookie
            response = session.get(
                url,
                headers=headers,
                timeout=20,
            )
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            body = str(getattr(response, "text", "") or "")
            ok = body.lstrip().startswith("#EXTM3U")
            if not ok:
                _log(
                    "HLS preflight returned non-playlist "
                    + f"host={(urlparse(str(url)).hostname or '')} "
                    + f"body={body[:80]!r}",
                    getattr(xbmc, "LOGERROR", None),
                )
            return ok
        except Exception as exc:
            _log(
                "HLS preflight exception "
                + f"host={(urlparse(str(url)).hostname or '')} "
                + f"error={exc}",
                getattr(xbmc, "LOGERROR", None),
            )
            return False

    @staticmethod
    def _empty_items(message: str = "No WatchWrestling shows found"):
        return [{"type": "dir", "title": f"[COLOR grey]{message}[/COLOR]", "link": BASE_URL}]
