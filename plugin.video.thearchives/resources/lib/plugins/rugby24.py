"""Rugby24 VOD provider for The Archives."""

import base64
import json
import re
from html import unescape
from typing import Dict, List
from urllib.parse import parse_qsl, quote, unquote, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://rugby24.net"
ROUTE_PATH = "/_thearchives_rugby24"
PROVIDER_HOSTS = {"rugby24.net", "www.rugby24.net"}
OK_HOSTS = {"ok.ru", "www.ok.ru", "m.ok.ru", "mobile.ok.ru", "odnoklassniki.ru", "www.odnoklassniki.ru"}
BYSE_HOSTS = {"bysesukior.com", "www.bysesukior.com"}
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
    blocked = ("search", "content-policy", "dmca", ROUTE_PATH.strip("/"), "css", "js", ".s")
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


def _owns_playback_item(data: Dict, link: str) -> bool:
    if not isinstance(data, dict):
        return False
    if str(data.get("provider") or data.get("source") or "").lower() == "rugby24":
        return True
    post_url = str(data.get("post_url") or "")
    return bool(post_url and _is_post_url(post_url))


def _kodi_header_query(headers: Dict[str, str]) -> str:
    return "&".join(
        f"{key}={quote(str(value), safe='')}"
        for key, value in headers.items()
        if value
    )


def _with_kodi_headers(url: str, headers: Dict[str, str]) -> str:
    header_query = _kodi_header_query(headers)
    return f"{url}|{header_query}" if header_query else url


def _log(message: str, level=None):
    try:
        xbmc.log(f"[TheArchives][Rugby24] {message}", level if level is not None else xbmc.LOGINFO)
    except Exception:
        pass


def _host(url: str) -> str:
    try:
        return (urlparse(str(url or "")).hostname or "").lower()
    except (TypeError, ValueError):
        return ""


def _base64url_decode(value: str) -> bytes:
    value = str(value or "")
    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


def _normalize_embed_url(value: str, base: str = BASE_URL) -> str:
    url = _absolute_url(value, base=base)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in OK_HOSTS:
        match = re.match(r"/videoembed/([\d-]+)", parsed.path)
        if match:
            return f"https://ok.ru/video/{match.group(1)}"
    return url


def _source_title(label: str, url: str, index: int) -> str:
    host = _host(url)
    if host in OK_HOSTS:
        return "OK.ru"
    if host in BYSE_HOSTS:
        return "Byse"
    title = _clean_text(label)
    return title or f"Source {index}"


def _parse_categories(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows = []
    seen = set()
    for anchor in soup.select("ul#list_cat a[href], .jquery-accordion-menu a[href]"):
        url = _absolute_url(anchor.get("href", ""))
        title = _clean_text(anchor.get_text(" ", strip=True))
        path = urlparse(url).path.strip("/").lower()
        if not title or not _is_provider_url(url) or url in seen:
            continue
        if url.rstrip("/") == BASE_URL or path.startswith(("content-policy", "dmca", "search")):
            continue
        seen.add(url)
        rows.append({"title": title, "url": url})
    return rows


def _parse_listing_cards(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows = []
    seen = set()
    for card in soup.select("div.short_item"):
        anchor = card.select_one("h3 a[href]")
        url = _absolute_url(anchor.get("href", "")) if anchor else ""
        title = _clean_text(anchor.get_text(" ", strip=True) if anchor else "")
        if not title or not _is_post_url(url) or url in seen:
            continue
        seen.add(url)
        image = card.select_one(".poster img, img")
        category = card.select_one(".short_cat")
        summary = card.select_one(".short_descr")
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
        rows.append({
            "title": title,
            "url": url,
            "thumbnail": _absolute_url(thumbnail),
            "summary": " | ".join(
                value
                for value in (
                    _clean_text(category.get_text(" ", strip=True) if category else ""),
                    _clean_text(summary.get_text(" ", strip=True) if summary else ""),
                )
                if value
            ),
        })
    return rows


def _parse_search_cards(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows = []
    seen = set()
    for title_node in soup.select(".eTitle a[href]"):
        url = _absolute_url(title_node.get("href", ""))
        title = _clean_text(title_node.get_text(" ", strip=True))
        if not title or not _is_post_url(url) or url in seen:
            continue
        seen.add(url)
        rows.append({"title": title, "url": url, "thumbnail": "", "summary": "Rugby24 search result."})
    return rows


def _next_page_url(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    node = soup.select_one(".paging-wrapper-bottom a.swchItem-next[href]")
    if not node:
        for anchor in soup.select(".paging-wrapper-bottom a[href]"):
            if "»" in anchor.get_text(" ", strip=True) or "&raquo;" in str(anchor):
                node = anchor
                break
    url = _absolute_url(node.get("href", "")) if node else ""
    return url if _is_provider_url(url) else ""


def _meta_content(soup: BeautifulSoup, name: str) -> str:
    node = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
    return _clean_text(node.get("content", "")) if node else ""


def _parse_post_details(html: str, post_url: str) -> Dict[str, object]:
    soup = BeautifulSoup(html or "", "html.parser")
    title_node = soup.select_one("h1") or soup.select_one(".eTitle")
    image_node = soup.find("meta", attrs={"property": "og:image"})
    title = _clean_text(title_node.get_text(" ", strip=True) if title_node else "") or _meta_content(soup, "og:title")
    thumbnail = _absolute_url(image_node.get("content", "")) if image_node else ""
    if not thumbnail:
        image = soup.select_one(".poster img, .eMessage img, img[alt]")
        thumbnail = _absolute_url(image.get("src", ""), base=post_url) if image else ""
    summary = _meta_content(soup, "og:description") or title
    sources = []
    seen = set()
    for frame in soup.select(".video-responsive iframe[src], .video-responsive iframe[data-src], iframe[src], iframe[data-src]"):
        link = _normalize_embed_url(frame.get("src") or frame.get("data-src") or "", base=post_url)
        if not link or link in seen:
            continue
        seen.add(link)
        label_node = frame.find_previous(["p", "h2", "h3", "strong", "b"])
        label = _clean_text(label_node.get_text(" ", strip=True) if label_node else "")
        sources.append({"title": _source_title(label, link, len(sources) + 1), "url": link})
    for anchor in soup.select("a[href]"):
        link = _normalize_embed_url(anchor.get("href", ""), base=post_url)
        if link in seen or not re.search(r"\.(?:m3u8|mp4|mpd)(?:$|\?)", link, re.I):
            continue
        seen.add(link)
        sources.append({"title": _clean_text(anchor.get_text(" ", strip=True)) or "Video", "url": link})
    return {"title": title, "thumbnail": thumbnail, "summary": summary, "sources": sources}


class Rugby24(Plugin):
    name = "rugby24"
    priority = 1067

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

    def from_keyboard(self, default_text: str = "", header: str = "Search Rugby24"):
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
            xbmc.log(f"[TheArchives][Rugby24] fetch failed for {url}: {exc}", xbmc.LOGERROR)
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
            source_url = f"{BASE_URL}/" if page == 1 else f"{BASE_URL}/?page{page}"
            return json.dumps({"kind": "listing", "html": self._fetch(source_url), "source_url": source_url})
        if kind == "search" and len(parts) >= 2:
            query = parts[1]
            page = self._page(parts, 2)
            params = {"q": query}
            if page > 1:
                params.update({"t": "0", "p": str(page)})
            source_url = f"{BASE_URL}/search/?{urlencode(params)}"
            return json.dumps({"kind": "search_results", "html": self._fetch(source_url), "source_url": source_url})
        if kind == "categories":
            return json.dumps({"kind": "categories", "html": self._fetch(f"{BASE_URL}/")})
        if kind == "listing" and len(parts) >= 2:
            source_url = parts[1]
            if not _is_provider_url(source_url):
                return None
            return json.dumps({"kind": "listing", "html": self._fetch(source_url), "source_url": source_url})
        if kind == "post" and len(parts) >= 2:
            post_url = parts[1]
            if not _is_post_url(post_url):
                return None
            return json.dumps({"kind": "post", "html": self._fetch(post_url), "post_url": post_url})
        return None

    def parse_list(self, url: str, response: str):
        if not _is_provider_url(url):
            return None
        data = _json_data(response)
        kind = data.get("kind")
        if kind == "root":
            return [
                {"type": "dir", "title": "[COLOR deepskyblue]Search[/COLOR]", "link": _route_url("search"), "thumbnail": "resources/media/movies.png", "summary": "Search Rugby24 replays."},
                {"type": "dir", "title": "Latest Replays", "link": _route_url("latest", "1"), "thumbnail": "resources/media/movies.png", "summary": "Browse the latest Rugby24 replays."},
                {"type": "dir", "title": "Categories", "link": _route_url("categories"), "thumbnail": "resources/media/tv_shows.png", "summary": "Browse Rugby24 competitions and teams."},
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
                    "summary": f"Browse {row['title']} replays.",
                }
                for row in _parse_categories(str(data.get("html") or ""))
            ]
            return rows or self._empty_items("No Rugby24 categories found")
        if kind in ("listing", "search_results"):
            source_url = str(data.get("source_url") or "")
            parser = _parse_search_cards if kind == "search_results" or "/search/" in source_url else _parse_listing_cards
            return self._listing_items(str(data.get("html") or ""), parser=parser)
        if kind == "post":
            post_url = str(data.get("post_url") or "")
            details = _parse_post_details(str(data.get("html") or ""), post_url)
            rows = []
            for source in details["sources"]:
                if _host(source["url"]) in BYSE_HOSTS and not self._resolve_byse(source["url"]):
                    continue
                rows.append({
                    "type": "item",
                    "title": source["title"],
                    "link": source["url"],
                    "thumbnail": details["thumbnail"],
                    "summary": details["summary"] or details["title"],
                    "post_url": post_url,
                    "provider": self.name,
                    "is_playable": "true",
                })
            return rows or self._empty_items("No Rugby24 sources found")
        return self._empty_items()

    def play_video(self, item: str):
        data, link = _decode_item(item)
        if not _owns_playback_item(data, link):
            return None
        resolved = self._resolve_source(link, data)
        if resolved.get("delegate") == "ok_ru":
            try:
                from .ok_ru import OKRu

                ok_item = dict(data)
                ok_item["link"] = resolved["url"]
                return OKRu().play_video(json.dumps(ok_item))
            except Exception as exc:
                xbmc.log(f"[TheArchives][Rugby24] OK.ru delegate failed: {exc}", xbmc.LOGERROR)
                xbmcgui.Dialog().notification("Rugby24", "OK.ru source unavailable", xbmcgui.NOTIFICATION_WARNING, 3000)
                return True
        if not resolved.get("url"):
            xbmcgui.Dialog().notification("Rugby24", "Source unavailable", xbmcgui.NOTIFICATION_WARNING, 3000)
            return True

        headers = {
            "User-Agent": self.user_agent,
            "Referer": str(resolved.get("referer") or data.get("post_url") or f"{BASE_URL}/"),
        }
        play_url = _with_kodi_headers(str(resolved["url"]), headers)
        protocol = str(resolved.get("protocol") or "")
        title = _clean_text(data.get("title") or "Rugby24")
        thumbnail = str(data.get("thumbnail") or "")
        list_item = xbmcgui.ListItem(title, path=play_url)
        list_item.setProperty("IsPlayable", "true")
        art = {"fanart": FANART}
        if thumbnail:
            art.update({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail})
        list_item.setArt(art)
        set_video_info(list_item, {"title": title, "plot": str(data.get("summary") or "")})
        if protocol == "hls":
            list_item.setMimeType("application/vnd.apple.mpegurl")
            try:
                list_item.setProperty("inputstream", "inputstream.ffmpegdirect")
                list_item.setProperty("inputstream.ffmpegdirect.manifest_type", "hls")
                list_item.setProperty("inputstream.ffmpegdirect.stream_headers", _kodi_header_query(headers))
            except AttributeError:
                pass
        elif protocol == "dash":
            list_item.setMimeType("application/dash+xml")
        else:
            list_item.setMimeType("video/mp4")
        try:
            list_item.setContentLookup(False)
        except AttributeError:
            pass
        _log(f"playing host={(urlparse(str(resolved['url'])).hostname or '')} title={title}")
        xbmc.Player().play(play_url, list_item)
        return True

    def _listing_items(self, html: str, parser=_parse_listing_cards):
        rows = [
            {
                "type": "dir",
                "title": card["title"],
                "link": _route_url("post", card["url"]),
                "thumbnail": card["thumbnail"],
                "summary": card["summary"],
            }
            for card in parser(html)
        ]
        next_url = _next_page_url(html)
        if next_url:
            rows.append({
                "type": "dir",
                "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                "link": _route_url("listing", next_url),
            })
        return rows or self._empty_items()

    def _resolve_source(self, url: str, data: Dict, depth: int = 0) -> Dict[str, str]:
        url = _normalize_embed_url(url, base=str(data.get("post_url") or BASE_URL))
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host in OK_HOSTS:
            return {"url": url, "delegate": "ok_ru"}
        if host in BYSE_HOSTS:
            return self._resolve_byse(url)
        if parsed.path.lower().endswith((".m3u8", ".mpd", ".mp4")):
            protocol = "hls" if parsed.path.lower().endswith(".m3u8") else "dash" if parsed.path.lower().endswith(".mpd") else "mp4"
            return {"url": url, "protocol": protocol, "referer": str(data.get("post_url") or f"{BASE_URL}/")}
        if depth >= 3 or parsed.scheme not in ("http", "https"):
            return {}
        html = self._fetch(url, referer=str(data.get("post_url") or f"{BASE_URL}/"))
        media = self._first_media_url(html, url)
        if media:
            return self._resolve_source(media, data, depth + 1)
        return {}

    def _resolve_byse(self, url: str) -> Dict[str, str]:
        code_match = re.search(r"/e/([^/?#]+)", urlparse(url).path)
        if not code_match or not self.session:
            return {}
        code = code_match.group(1)
        api_url = f"https://bysesukior.com/api/videos/{quote(code, safe='')}"
        try:
            response = self.session.get(
                api_url,
                headers={
                    "User-Agent": self.user_agent,
                    "Referer": url,
                    "Accept": "application/json,text/plain,*/*",
                },
                timeout=20,
            )
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            data = response.json()
        except Exception as exc:
            _log(f"Byse API failed for {code}: {exc}", getattr(xbmc, "LOGERROR", None))
            return {}
        playback = data.get("playback") if isinstance(data, dict) else {}
        config = self._decrypt_byse_playback(playback if isinstance(playback, dict) else {})
        sources = config.get("sources") if isinstance(config, dict) else []
        if not isinstance(sources, list):
            return {}
        for source in sources:
            if not isinstance(source, dict):
                continue
            media = str(source.get("url") or "")
            if not media:
                continue
            mime_type = str(source.get("mime_type") or source.get("mimeType") or "").lower()
            protocol = "hls" if ".m3u8" in media.lower() or "mpegurl" in mime_type else "mp4"
            if protocol == "hls" and not self._valid_hls(media, url):
                continue
            return {
                "url": media,
                "protocol": protocol,
                "referer": url,
            }
        return {}

    def _decrypt_byse_playback(self, playback: Dict) -> Dict:
        if not playback:
            return {}
        try:
            from resources.lib.external.yt_dlp.aes import aes_gcm_decrypt_and_verify_bytes

            key_parts = playback.get("key_parts") if isinstance(playback.get("key_parts"), list) else []
            selected = self._byse_key_parts(str(playback.get("version") or ""), key_parts)
            key = b"".join(_base64url_decode(part) for part in selected)
            payload = _base64url_decode(str(playback.get("payload") or ""))
            iv = _base64url_decode(str(playback.get("iv") or ""))
            if len(payload) <= 16 or not key or not iv:
                return {}
            plaintext = aes_gcm_decrypt_and_verify_bytes(payload[:-16], key, payload[-16:], iv)
            data = json.loads(plaintext.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            _log(f"Byse decrypt failed: {exc}", getattr(xbmc, "LOGERROR", None))
            return {}

    @staticmethod
    def _byse_key_parts(version: str, key_parts: List[str]) -> List[str]:
        mapping = {str(number): (number ^ 0, 31 - number ^ 0) for number in range(1, 21)}
        indexes = mapping.get(str(version or "").strip())
        if indexes and all(1 <= index <= len(key_parts) for index in indexes):
            selected = [key_parts[index - 1] for index in indexes if key_parts[index - 1]]
            if selected:
                return selected
        return key_parts

    def _valid_hls(self, url: str, referer: str) -> bool:
        if not self.session:
            return False
        try:
            response = self.session.get(
                url,
                headers={"User-Agent": self.user_agent, "Referer": referer},
                timeout=20,
            )
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            body = str(getattr(response, "text", "") or "")
            return body.lstrip().startswith("#EXTM3U")
        except Exception as exc:
            _log(f"HLS preflight failed for {_host(url)}: {exc}", getattr(xbmc, "LOGERROR", None))
            return False

    def _first_media_url(self, html: str, base: str) -> str:
        soup = BeautifulSoup(html or "", "html.parser")
        for selector in ("source[src]", "video[src]", "iframe[data-src]", "iframe[src]"):
            node = soup.select_one(selector)
            if node:
                return _normalize_embed_url(node.get("src") or node.get("data-src") or "", base=base)
        for pattern in (
            r"""file\s*[:=]\s*["']([^"']+\.(?:m3u8|mp4|mpd)(?:\?[^"']*)?)["']""",
            r"""src\s*[:=]\s*["']([^"']+\.(?:m3u8|mp4|mpd)(?:\?[^"']*)?)["']""",
            r"""["'](https?://[^"']+\.(?:m3u8|mp4|mpd)(?:\?[^"']*)?)["']""",
        ):
            match = re.search(pattern, html or "", re.I)
            if match:
                return _absolute_url(match.group(1), base=base)
        return ""

    @staticmethod
    def _empty_items(message: str = "No Rugby24 replays found"):
        return [{"type": "dir", "title": f"[COLOR grey]{message}[/COLOR]", "link": BASE_URL}]
