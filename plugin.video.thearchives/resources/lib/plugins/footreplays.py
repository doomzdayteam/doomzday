"""FootReplays VOD provider for The Archives."""

import json
import re
from html import unescape
from typing import Dict, List
from urllib.parse import quote, unquote, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://www.footreplays.com"
ROUTE_PATH = "/_thearchives_footreplays"
PROVIDER_HOSTS = {"footreplays.com", "www.footreplays.com"}
HQ_HOSTS = {"hglink.to", "hgcloud.to"}
HQ_DOMAINS = (
    "audinifer.com",
    "vibuxere.com",
    "streamhg.com",
    "dhcplay.com",
    "cybervynx.com",
)
VK_HOSTS = {"vk.com", "www.vk.com", "vkvideo.ru", "www.vkvideo.ru"}
DAILYMOTION_HOSTS = {"dailymotion.com", "www.dailymotion.com", "dai.ly"}
OK_HOSTS = {"ok.ru", "www.ok.ru", "m.ok.ru", "mobile.ok.ru"}
FANART = Addon().getAddonInfo("fanart")
PACKER_RE = re.compile(
    r"eval\(function\(p,a,c,k,e,d\)\{.*?\}\('((?:[^'\\]|\\.)*)',\s*\d+,\s*\d+,\s*'((?:[^'\\]|\\.)*)'\s*(?:\.split\('\|'\))?\)\)",
    re.S,
)
VK_STREAM_RE = re.compile(
    r'"(hls|hls_ondemand|dash|dash_sep|dash_ondemand)"\s*:\s*"([^"]+)"',
    re.I,
)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()


def _absolute_url(value: str) -> str:
    if str(value or "").startswith("//"):
        return "https:" + str(value)
    return urljoin(f"{BASE_URL}/", str(value or ""))


def _normalize_source_url(value: str) -> str:
    url = _absolute_url(value).strip()
    parsed = urlparse(url)
    if parsed.hostname in OK_HOSTS:
        match = re.match(r"/videoembed/([\d-]+)", parsed.path)
        if match:
            return f"https://ok.ru/video/{match.group(1)}"
    return url


def _base36(value: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    output = ""
    while value:
        value, remainder = divmod(value, 36)
        output = digits[remainder] + output
    return output


def _unpack_packer(payload: str, symbols: List[str]) -> str:
    unpacked = payload
    for index in range(len(symbols) - 1, -1, -1):
        if symbols[index]:
            unpacked = re.sub(
                rf"\b{re.escape(_base36(index))}\b",
                lambda _match, replacement=symbols[index]: replacement,
                unpacked,
            )
    return unpacked


def _resolve_hq_source(session, source_url: str) -> Dict[str, str]:
    path = urlparse(_normalize_source_url(source_url)).path
    if not path:
        return {}
    for domain in HQ_DOMAINS:
        base_url = f"https://{domain}"
        try:
            response = session.get(
                f"{base_url}{path}",
                headers={"Referer": "https://hgcloud.to/"},
                timeout=20,
            )
            html = str(getattr(response, "text", "") or "")
        except Exception:
            continue
        if len(html) <= 2000:
            continue
        file_match = re.search(
            r"\$\.cookie\(['\"]file_id['\"],\s*['\"]([^'\"]+)", html
        )
        packer = PACKER_RE.search(html)
        if not file_match or not packer:
            continue
        aff_match = re.search(
            r"\$\.cookie\(['\"]aff['\"],\s*['\"]([^'\"]*)", html
        )
        ref_match = re.search(
            r"\$\.cookie\(['\"]ref_url['\"],\s*['\"]([^'\"]+)", html
        )
        unpacked = _unpack_packer(packer.group(1), packer.group(2).split("|"))
        candidates = re.findall(r":\s*[\"']([^\"']+)[\"']", unpacked)
        cookie = (
            f"file_id={file_match.group(1)}; "
            f"aff={aff_match.group(1) if aff_match else ''}; tsn=7"
        )
        if ref_match:
            cookie += f"; ref_url={quote(ref_match.group(1), safe='')}"
        media_candidates = []
        media_candidates.extend(
            value
            for value in candidates
            if value.startswith("http") and ".m3u8" in value.lower()
        )
        media_candidates.extend(
            f"{base_url}{value}"
            for value in candidates
            if value.startswith("/")
            and ".m3u8" in value.lower()
            and not value.startswith(("/dl", "/assets"))
        )
        fallback = re.search(r"[\"']([^\"']*\.m3u8[^\"']*)[\"']", unpacked)
        if fallback:
            value = fallback.group(1)
            media_candidates.append(f"{base_url}{value}" if value.startswith("/") else value)
        seen_media = set()
        for media in media_candidates:
            if media in seen_media:
                continue
            seen_media.add(media)
            try:
                media_response = session.get(
                    media,
                    headers={"Referer": base_url, "Cookie": cookie},
                    timeout=20,
                )
                if hasattr(media_response, "raise_for_status"):
                    media_response.raise_for_status()
                media_text = str(getattr(media_response, "text", "") or "")
            except Exception:
                continue
            if not media_text.lstrip().startswith("#EXTM3U"):
                continue
            return {
                "url": media,
                "referer": base_url,
                "cookie": cookie,
                "protocol": "hls",
            }
    return {}


def _extract_vk_streams(text: str) -> List[Dict[str, str]]:
    if "hash429" in (text or "") or "challenge.html" in (text or ""):
        return []
    normalized = (text or "").replace(r'\"', '"').replace(r"\/", "/")
    results = []
    seen = set()
    for match in VK_STREAM_RE.finditer(normalized):
        url = match.group(2).replace("\\", "")
        if not url or url in seen:
            continue
        seen.add(url)
        results.append({
            "url": url,
            "protocol": "dash" if "dash" in match.group(1).lower() else "hls",
        })
    return results


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


def _source_provider(url: str) -> str:
    host = (urlparse(str(url or "")).hostname or "").lower()
    if host in DAILYMOTION_HOSTS:
        return "dailymotion"
    if host in OK_HOSTS:
        return "ok_ru"
    return "footreplays"


def _parse_competitions(html: str) -> List[Dict[str, object]]:
    soup = BeautifulSoup(html or "", "html.parser")
    menu = soup.select_one("ul#menu-main-menu-1") or soup.select_one("ul.main-menu")
    results = []
    seen = set()
    if not menu:
        return results
    for node in menu.find_all("li", recursive=False):
        anchor = node.find("a", recursive=False)
        if not anchor:
            continue
        url = _absolute_url(anchor.get("href", ""))
        title = _clean_text(anchor.get_text(" ", strip=True))
        if not title or not _is_provider_url(url) or url in seen:
            continue
        seen.add(url)
        children = []
        child_seen = set()
        submenu = node.find("ul", class_="sub-menu", recursive=False)
        for child in submenu.find_all("li") if submenu else []:
            child_anchor = child.find("a")
            child_url = _absolute_url(child_anchor.get("href", "")) if child_anchor else ""
            child_title = _clean_text(child_anchor.get_text(" ", strip=True)) if child_anchor else ""
            if child_title and _is_provider_url(child_url) and child_url not in child_seen:
                child_seen.add(child_url)
                children.append({"title": child_title, "url": child_url})
        results.append({"title": title, "url": url, "children": children})
    return results


def _parse_match_cards(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html or "", "html.parser")
    results = []
    seen = set()
    for card in soup.select("div.p-wrap"):
        category_node = card.select_one("a.p-category")
        category_url = _absolute_url(category_node.get("href", "")) if category_node else ""
        category_classes = category_node.get("class", []) if category_node else []
        if "/news/" in category_url or "category-id-283" in category_classes:
            continue
        anchor = card.select_one("a.p-flink") or card.select_one(".entry-title a")
        url = _absolute_url(anchor.get("href", "")) if anchor else ""
        title = _clean_text((anchor.get("title") or anchor.get_text(" ", strip=True)) if anchor else "")
        if not title or not _is_provider_url(url) or url in seen:
            continue
        seen.add(url)
        image = card.select_one("div.p-featured img") or card.select_one("img")
        thumbnail = ""
        if image:
            thumbnail = next(
                (
                    image.get(key)
                    for key in ("fifu-data-src", "data-src", "src")
                    if image.get(key) and not image.get(key).startswith("data:")
                ),
                "",
            )
        time_node = card.select_one("time")
        results.append({
            "title": title,
            "url": url,
            "thumbnail": _absolute_url(thumbnail),
            "category": _clean_text(category_node.get_text(" ", strip=True)) if category_node else "",
            "date": _clean_text(time_node.get_text(" ", strip=True)) if time_node else "",
        })
    return results


def _next_page_url(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    node = soup.select_one('link[rel="next"]') or soup.select_one("a.next.page-numbers")
    url = _absolute_url(node.get("href", "")) if node else ""
    return url if _is_provider_url(url) else ""


def _parse_match_details(html: str) -> Dict[str, object]:
    soup = BeautifulSoup(html or "", "html.parser")
    title_node = soup.select_one("h1.s-title") or soup.select_one("h1")
    image_node = soup.select_one('meta[property="og:image"]')
    summary_node = soup.select_one('meta[property="og:description"]')
    sources = []
    seen = set()
    for table in soup.select("table.video-table"):
        heading = table.select_one("thead th[colspan]")
        source_name = _clean_text(heading.get_text(" ", strip=True)) if heading else "Source"
        for row in table.select("tbody tr"):
            cells = row.select("td")
            button = row.select_one("a.play-button[onclick]")
            if not cells or not button:
                continue
            match = re.search(r"loadVideo\(\s*(['\"])(.*?)\1\s*\)", button.get("onclick", ""), re.I)
            if not match:
                continue
            url = _absolute_url(unescape(match.group(2)).strip())
            if not url.startswith(("http://", "https://")) or url in seen:
                continue
            seen.add(url)
            labels = [source_name]
            labels.extend(_clean_text(cell.get_text(" ", strip=True)) for cell in cells[:3])
            labels = [value for value in labels if value]
            title = " - ".join(labels)
            host = (urlparse(url).hostname or "").lower()
            if "match tv" in title.lower() and host not in OK_HOSTS:
                continue
            sources.append({"title": title, "url": url})
    return {
        "title": _clean_text(title_node.get_text(" ", strip=True)) if title_node else "",
        "thumbnail": _absolute_url(image_node.get("content", "")) if image_node else "",
        "summary": _clean_text(summary_node.get("content", "")) if summary_node else "",
        "sources": sources,
    }


class FootReplays(Plugin):
    name = "footreplays"
    priority = 1065

    def __init__(self):
        self.session = DI.session
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        self._source_available_cache = {}
        headers = getattr(self.session, "headers", None)
        if isinstance(headers, dict):
            headers.update({"User-Agent": self.user_agent, "Referer": f"{BASE_URL}/"})

    def from_keyboard(self, default_text: str = "", header: str = "Search FootReplays"):
        keyboard = xbmc.Keyboard(default_text, header, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return None

    def _fetch(self, url: str) -> str:
        if not self.session:
            return ""
        try:
            response = self.session.get(url, timeout=20)
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            return str(getattr(response, "text", "") or "")
        except Exception as exc:
            xbmc.log(f"[TheArchives][FootReplays] fetch failed for {url}: {exc}", xbmc.LOGERROR)
            return ""

    def _source_is_listable(self, source: Dict[str, str]) -> bool:
        title = str((source or {}).get("title") or "").lower()
        link = _normalize_source_url(str((source or {}).get("url") or ""))
        host = (urlparse(link).hostname or "").lower()
        if not any(value in title for value in ("bbc", "fox sports", "foxsports")):
            return True
        if host not in HQ_HOSTS:
            return False
        if link not in self._source_available_cache:
            resolved = _resolve_hq_source(self.session, link) if self.session else {}
            self._source_available_cache[link] = bool(resolved.get("url"))
            if not self._source_available_cache[link]:
                xbmc.log(
                    f"[TheArchives][FootReplays] hiding unresolved source: {source.get('title')} {link}",
                    xbmc.LOGWARNING,
                )
        return self._source_available_cache[link]

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
            query = self.from_keyboard(header="Search FootReplays")
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
        if kind == "competitions":
            return json.dumps({"kind": "competitions", "html": self._fetch(f"{BASE_URL}/")})
        if kind in ("competition", "listing") and len(parts) >= 2:
            source_url = parts[1]
            if not _is_provider_url(source_url):
                return None
            return json.dumps({
                "kind": "competition" if kind == "competition" else "listing",
                "html": self._fetch(source_url),
                "source_url": source_url,
            })
        if kind == "match" and len(parts) >= 2:
            match_url = parts[1]
            if not _is_provider_url(match_url):
                return None
            return json.dumps({"kind": "match", "html": self._fetch(match_url)})
        return None

    def parse_list(self, url: str, response: str):
        if not _is_provider_url(url):
            return None
        data = _json_data(response)
        kind = data.get("kind")
        if kind == "root":
            return [
                {"type": "dir", "title": "[COLOR deepskyblue]Search[/COLOR]", "link": _route_url("search"), "thumbnail": "resources/media/movies.png", "summary": "Search FootReplays matches."},
                {"type": "dir", "title": "Latest Matches", "link": _route_url("latest", "1"), "thumbnail": "resources/media/movies.png", "summary": "Browse the latest full match replays and highlights."},
                {"type": "dir", "title": "Competitions", "link": _route_url("competitions"), "thumbnail": "resources/media/tv_shows.png", "summary": "Browse countries and competitions."},
            ]
        if kind == "redirect":
            return [{"type": "dir", "title": "[COLOR deepskyblue]Search Results[/COLOR]", "link": str(data.get("link") or "")}]
        if kind == "competitions":
            items = [
                {"type": "dir", "title": group["title"], "link": _route_url("competition", group["url"]), "thumbnail": "resources/media/tv_shows.png", "summary": f"Browse {group['title']} competitions and matches."}
                for group in _parse_competitions(str(data.get("html") or ""))
            ]
            return items or self._empty_items("No FootReplays competitions found")
        if kind == "competition":
            html = str(data.get("html") or "")
            source_url = str(data.get("source_url") or "")
            groups = _parse_competitions(html)
            current = next((group for group in groups if group["url"].rstrip("/") == source_url.rstrip("/")), None)
            items = []
            if current:
                items.extend(
                    {"type": "dir", "title": child["title"], "link": _route_url("listing", child["url"]), "thumbnail": "resources/media/tv_shows.png", "summary": f"Browse {child['title']} matches."}
                    for child in current["children"]
                )
            items.extend(self._listing_items(html))
            return items or self._empty_items()
        if kind == "listing":
            return self._listing_items(str(data.get("html") or ""))
        if kind == "match":
            details = _parse_match_details(str(data.get("html") or ""))
            items = []
            for source in details["sources"]:
                if not self._source_is_listable(source):
                    continue
                items.append({
                    "type": "item",
                    "title": source["title"],
                    "link": _normalize_source_url(source["url"]),
                    "thumbnail": details["thumbnail"],
                    "summary": details["summary"],
                    "provider": _source_provider(source["url"]),
                    "is_playable": "true",
                })
            return items or self._empty_items("No replay sources found")
        return self._empty_items()

    def play_video(self, item: str):
        data, link = _decode_item(item)
        if data.get("provider") and data.get("provider") != self.name:
            return None
        link = _normalize_source_url(link)
        parsed = urlparse(link)
        host = (parsed.hostname or "").lower()
        if host in {
            "youtube.com", "www.youtube.com", "youtu.be",
            *OK_HOSTS,
        }:
            return None

        resolved = {}
        if host in HQ_HOSTS:
            resolved = _resolve_hq_source(self.session, link) if self.session else {}
        elif host in VK_HOSTS:
            html = self._fetch_source(link, referer="https://vkvideo.ru/")
            streams = _extract_vk_streams(html)
            if streams:
                resolved = dict(streams[0])
                resolved.update({"referer": "https://vkvideo.ru/", "cookie": ""})
        elif parsed.path.lower().endswith((".m3u8", ".mpd", ".mp4")):
            protocol = "hls" if parsed.path.lower().endswith(".m3u8") else "dash" if parsed.path.lower().endswith(".mpd") else "mp4"
            resolved = {"url": link, "protocol": protocol, "referer": f"{BASE_URL}/", "cookie": ""}
        else:
            return None

        if not resolved.get("url"):
            xbmc.log(
                f"[TheArchives][FootReplays] source unavailable: {host}",
                xbmc.LOGERROR,
            )
            xbmcgui.Dialog().notification(
                "FootReplays",
                "Source unavailable",
                xbmcgui.NOTIFICATION_WARNING,
                3000,
            )
            return True

        headers = {
            "User-Agent": self.user_agent,
            "Referer": str(resolved.get("referer") or f"{BASE_URL}/"),
            "Cookie": str(resolved.get("cookie") or ""),
        }
        play_url = _with_kodi_headers(str(resolved["url"]), headers)
        title = _clean_text(data.get("title") or "FootReplays")
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
        mime_types = {
            "hls": "application/vnd.apple.mpegurl",
            "dash": "application/dash+xml",
            "mp4": "video/mp4",
        }
        protocol = str(resolved.get("protocol"))
        list_item.setMimeType(mime_types.get(protocol, "video/mp4"))
        try:
            if protocol == "hls":
                list_item.setProperty("inputstream", "inputstream.ffmpegdirect")
                list_item.setProperty(
                    "inputstream.ffmpegdirect.manifest_type", "hls"
                )
                list_item.setProperty(
                    "inputstream.ffmpegdirect.stream_headers",
                    _kodi_header_query(headers),
                )
            list_item.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(play_url, list_item)
        return True

    def _fetch_source(self, url: str, referer: str) -> str:
        if not self.session:
            return ""
        try:
            response = self.session.get(
                url,
                headers={"User-Agent": self.user_agent, "Referer": referer},
                timeout=20,
            )
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            return str(getattr(response, "text", "") or "")
        except Exception as exc:
            xbmc.log(
                f"[TheArchives][FootReplays] source fetch failed for {url}: {exc}",
                xbmc.LOGERROR,
            )
            return ""

    def _listing_items(self, html: str):
        items = [
            {
                "type": "dir",
                "title": card["title"],
                "link": _route_url("match", card["url"]),
                "thumbnail": card["thumbnail"],
                "summary": " | ".join(value for value in (card["category"], card["date"]) if value),
            }
            for card in _parse_match_cards(html)
        ]
        next_url = _next_page_url(html)
        if next_url:
            items.append({"type": "dir", "title": "[COLOR deepskyblue]Next Page[/COLOR]", "link": _route_url("listing", next_url)})
        return items or self._empty_items()

    @staticmethod
    def _empty_items(message: str = "No FootReplays matches found"):
        return [{"type": "dir", "title": f"[COLOR grey]{message}[/COLOR]", "link": BASE_URL}]
