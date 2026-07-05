import json
import re
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import quote, unquote, urlparse

import xbmc
import xbmcgui
from bs4 import BeautifulSoup
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


BASE_URL = "https://ok.ru"
ROUTE_PATH = "/_thearchives"
FANART = Addon().getAddonInfo("fanart")

CATEGORIES = (
    ("Videos", "showcase"),
    ("Series", "serial"),
)


def _clean_text(value) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()


def _absolute_url(value: str) -> str:
    value = _clean_text(value)
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("/"):
        return BASE_URL + value
    return value


def _canonical_video_url(value: str, fallback_id: str = "") -> str:
    match = re.search(r"/video/(?!c)([\d-]+)", value or "")
    video_id = match.group(1) if match else fallback_id
    return f"{BASE_URL}/video/{video_id}" if video_id else ""


def _route_url(kind: str, *parts: str) -> str:
    encoded = [quote(str(value), safe="") for value in (kind,) + parts]
    return f"{BASE_URL}{ROUTE_PATH}/" + "/".join(encoded)


def _route_parts(url: str) -> List[str]:
    path = urlparse(url).path.strip("/")
    prefix = ROUTE_PATH.strip("/") + "/"
    if not path.startswith(prefix):
        return []
    return [unquote(value) for value in path[len(prefix):].split("/") if value]


def _parse_video_cards(markup: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(markup or "", "html.parser")
    rows = []
    seen = set()
    for container in soup.select("div.ugrid_i"):
        card = container.select_one("div.video-card")
        if not card:
            continue
        link_node = card.select_one("a.video-card_lk")
        title_node = card.select_one("a.video-card_n")
        image_node = card.select_one("img.video-card_img")
        duration_node = card.select_one("div.video-card_duration")
        link = _canonical_video_url(
            link_node.get("href", "") if link_node else "",
            card.get("data-id", ""),
        )
        title = _clean_text(title_node.get_text(" ") if title_node else "")
        if not link or not title or link in seen:
            continue
        seen.add(link)
        duration = _clean_text(duration_node.get_text(" ") if duration_node else "")
        display = f"[COLOR red]>[/COLOR] {title}"
        if duration:
            display += f"  [COLOR gray][{duration}][/COLOR]"
        rows.append({
            "type": "item",
            "title": display,
            "link": link,
            "thumbnail": _absolute_url(image_node.get("src", "") if image_node else ""),
            "summary": title,
            "is_playable": "true",
        })
    return rows


def _parse_series_sliders(markup: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(markup or "", "html.parser")
    rows = []
    seen = set()

    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    for slider in soup.select("video-channels-vitrine-slider[data-props]"):
        try:
            data = json.loads(unescape(slider.get("data-props", "")))
        except (TypeError, ValueError):
            continue
        for item in walk(data):
            link = _absolute_url(item.get("href", ""))
            title = _clean_text(item.get("name") or item.get("title"))
            if not title or "/video/c" not in link or link in seen:
                continue
            seen.add(link)
            rows.append({
                "type": "dir",
                "title": title,
                "link": link,
                "thumbnail": _absolute_url(item.get("imageUrl", "")),
                "summary": f"Browse {title} episodes on OK.ru.",
            })
    return rows


def _parse_episode_cards(markup: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(markup or "", "html.parser")
    rows = []
    seen = set()
    for container in soup.select("div.ugrid_i.js-seen-item-movie"):
        card = container.select_one("div.video-card")
        if not card:
            continue
        video_id = _clean_text(card.get("data-id", ""))
        title_node = card.select_one("a.video-card_n")
        image_node = card.select_one("img.video-card_img")
        duration_node = card.select_one("div.video-card_duration")
        title = _clean_text(title_node.get_text(" ") if title_node else "")
        link = _canonical_video_url("", video_id)
        if not link or not title or link in seen:
            continue
        seen.add(link)
        duration = _clean_text(duration_node.get_text(" ") if duration_node else "")
        display = f"[COLOR red]>[/COLOR] {title}"
        if duration:
            display += f"  [COLOR gray][{duration}][/COLOR]"
        rows.append({
            "type": "item",
            "title": display,
            "link": link,
            "thumbnail": _absolute_url(image_node.get("src", "") if image_node else ""),
            "summary": title,
            "is_playable": "true",
        })
    return rows


def _last_element(markup: str) -> str:
    soup = BeautifulSoup(markup or "", "html.parser")
    loader = soup.select_one("[data-module=Loader][data-last-element], .loader-container[data-last-element]")
    return _clean_text(loader.get("data-last-element", "")) if loader else ""


def _search_rows(data: Dict) -> List[Dict[str, str]]:
    videos = (data or {}).get("videos") or {}
    rows = []
    seen = set()
    for item in videos.get("list") or []:
        if not isinstance(item, dict):
            continue
        movie = item.get("movie") or {}
        video_id = str(movie.get("id") or "")
        title = _clean_text(movie.get("title") or item.get("name"))
        thumbnail = movie.get("thumbnail") or {}
        link = _canonical_video_url("", video_id)
        if not link or not title or link in seen:
            continue
        seen.add(link)
        rows.append({
            "type": "item",
            "title": f"[COLOR red]>[/COLOR] {title}",
            "link": link,
            "thumbnail": _absolute_url(thumbnail.get("big") or thumbnail.get("small") or item.get("imageUrl", "")),
            "summary": title,
            "is_playable": "true",
        })
    return rows


def _search_data_from_html(markup: str) -> Dict:
    soup = BeautifulSoup(markup or "", "html.parser")
    node = soup.find("video-search-result", attrs={"data-props": True})
    if not node:
        return {}
    try:
        return json.loads(unescape(node.get("data-props", "")))
    except (TypeError, ValueError):
        return {}


def _player_options(markup: str, video_id: str) -> Dict:
    soup = BeautifulSoup(markup or "", "html.parser")
    fallback = {}
    for node in soup.find_all(attrs={"data-options": True}):
        raw = unescape(node.get("data-options", ""))
        try:
            options = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(options, dict) or not options.get("flashvars"):
            continue
        if not fallback:
            fallback = options
        if str(video_id) in raw:
            return options
    return fallback


def _metadata_from_options(options: Dict, session) -> Dict:
    flashvars = (options or {}).get("flashvars") or {}
    metadata = flashvars.get("metadata")
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str) and metadata:
        try:
            return json.loads(metadata)
        except (TypeError, ValueError):
            pass

    metadata_url = unquote(str(flashvars.get("metadataUrl") or "")).replace("\\u0026", "&")
    if not metadata_url:
        return {}
    form = {}
    if flashvars.get("location"):
        form["st.location"] = flashvars.get("location")
    response = session.post(metadata_url, data=form, timeout=20)
    try:
        data = response.json()
    except (AttributeError, TypeError, ValueError):
        try:
            data = json.loads(getattr(response, "text", "") or "{}")
        except (TypeError, ValueError):
            data = {}
    return data if isinstance(data, dict) else {}


def _select_stream(metadata: Dict) -> Optional[Dict[str, str]]:
    hls = (metadata or {}).get("hlsManifestUrl") or (metadata or {}).get("ondemandHls")
    if isinstance(hls, str) and hls.startswith(("http://", "https://")):
        return {"url": hls, "protocol": "hls"}
    ranks = {
        "mobile": 0,
        "lowest": 1,
        "low": 2,
        "sd": 3,
        "hd": 4,
        "full": 5,
        "quad": 6,
        "ultra": 7,
    }
    streams = [
        row for row in ((metadata or {}).get("videos") or [])
        if isinstance(row, dict) and str(row.get("url") or "").startswith(("http://", "https://"))
    ]
    if not streams:
        return None
    best = max(streams, key=lambda row: ranks.get(str(row.get("name") or "").lower(), -1))
    return {"url": best["url"], "protocol": "http"}


def _availability_reason(metadata: Dict) -> str:
    if _select_stream(metadata):
        return ""
    if (metadata or {}).get("paymentInfo"):
        return "paid"
    return "unavailable"


def _kodi_headers(url: str, user_agent: str, referer: str) -> str:
    headers = (
        f"User-Agent={quote(user_agent, safe='')}"
        f"&Referer={quote(referer, safe='')}"
        f"&Origin={quote(BASE_URL, safe='')}"
    )
    return f"{url}|{headers}" if url else ""


class OKRu(Plugin):
    name = "ok_ru"
    priority = 1060

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
                "Referer": f"{BASE_URL}/video/showcase",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            }

    @staticmethod
    def _response_text(response) -> str:
        return getattr(response, "text", "") or ""

    @staticmethod
    def _page_number(parts: List[str], index: int) -> int:
        try:
            return max(1, int(parts[index]))
        except (IndexError, TypeError, ValueError):
            return 1

    def get_list(self, url: str) -> Optional[str]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None

        parsed = urlparse(url)
        route = _route_parts(url)
        if parsed.path.rstrip("/") in ("", urlparse(self.base_url).path.rstrip("/")) and not route:
            return json.dumps({"kind": "root"})

        album_match = re.fullmatch(r"/video/(c\d+)", parsed.path.rstrip("/"))
        if album_match:
            response = self.session.get(url, timeout=20)
            return json.dumps({
                "kind": "album",
                "album_id": album_match.group(1),
                "page": 1,
                "html": self._response_text(response),
                "fetched_all": str(getattr(response, "headers", {}).get("fetchedall", "")).lower() == "true",
            })

        if not route:
            return None

        kind = route[0]
        if kind == "search":
            if len(route) == 1:
                query = self.from_keyboard()
                if not query:
                    return json.dumps({"kind": "message", "title": "Search cancelled"})
                return json.dumps({"kind": "redirect", "link": _route_url("search", query, "1")})
            query = route[1]
            page = self._page_number(route, 2)
            if page == 1:
                endpoint = (
                    f"{BASE_URL}/video/search?st.cmd=video&st.psft=showcase&st.m=SEARCH"
                    "&st.ft=search&st.fuvh=on&st.furl=%2Fvideo%2Fshowcase&cmd=VideoContentBlock"
                )
                response = self.session.post(endpoint, data={
                    "st.v.sq": query,
                    "gwt.requested": "9579ea2eT1774883610506",
                }, timeout=20)
                return json.dumps({
                    "kind": "search_html",
                    "query": query,
                    "page": page,
                    "html": self._response_text(response),
                    "fetched_all": str(getattr(response, "headers", {}).get("fetchedall", "")).lower() == "true",
                })

            request = {
                "id": page,
                "parameters": {
                    "displayMode": "Movie",
                    "videosOffset": (page - 1) * 30,
                    "channelsOffset": 0,
                    "searchQuery": query,
                    "currentStateId": "video",
                    "durationType": "ANY",
                    "hd": False,
                },
            }
            response = self.session.post(
                f"{BASE_URL}/web-api/v2/video/fetchSearchResult",
                data=json.dumps(request),
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Content-Type": "text/plain;charset=UTF-8",
                    "ok-screen": "anonymVideo",
                    "x-client-flags": "ms:0;dcss:0;mpv2:1;dz:0",
                },
                timeout=20,
            )
            try:
                data = response.json()
            except (AttributeError, TypeError, ValueError):
                data = {}
            return json.dumps({"kind": "search_api", "query": query, "page": page, "data": data})

        if kind == "catalog" and len(route) > 1:
            catalog_path = route[1].strip("/")
            page = self._page_number(route, 2)
            cursor = route[3] if len(route) > 3 else ""
            source_url = f"{BASE_URL}/video/{catalog_path}"
            if page == 1:
                response = self.session.get(source_url, timeout=20)
            else:
                is_showcase = catalog_path == "showcase"
                is_series = catalog_path == "serial"
                tag = catalog_path.rsplit("/", 1)[-1]
                parent = catalog_path.rsplit("/", 1)[0] if "/" in catalog_path else catalog_path
                ft = "serial" if is_series else parent.rsplit("/", 1)[-1]
                if is_showcase:
                    endpoint = (
                        f"{source_url}?st.cmd=anonymVideo&st.m=SHOWCASE&st.ft=showcase"
                        "&st.furl=%2Fvideo%2Fshowcase&cmd=VideoUniversalContentBlock"
                    )
                else:
                    endpoint = (
                        f"{BASE_URL}/video/{parent}?st.cmd=anonymVideo&st.fltag={quote(tag)}"
                        f"&st.m=ALBUMS_CATALOG&st.ft={quote(ft)}&st.furl={quote('/video/' + catalog_path, safe='')}"
                        "&cmd=VideoUniversalContentBlock"
                    )
                response = self.session.post(endpoint, data={
                    "fetch": "false",
                    "st.page": str(page),
                    "st.lastelem": cursor,
                    "gwt.requested": "9579ea2eT1774883610506",
                }, headers={
                    "ok-screen": "anonymVideo",
                    "X-Requested-With": "XMLHttpRequest",
                }, timeout=20)
            return json.dumps({
                "kind": "series" if catalog_path == "serial" else "catalog",
                "catalog_path": catalog_path,
                "page": page,
                "html": self._response_text(response),
                "fetched_all": str(getattr(response, "headers", {}).get("fetchedall", "")).lower() == "true",
            })

        if kind == "album" and len(route) > 1:
            album_id = route[1]
            page = self._page_number(route, 2)
            cursor = route[3] if len(route) > 3 else ""
            album_url = f"{BASE_URL}/video/{album_id}"
            endpoint = (
                f"{album_url}?st.cmd=anonymVideo&st.m=ALBUM&st.ft=album"
                f"&st.aid={quote(album_id)}&cmd=VideoAlbumBlock"
            )
            response = self.session.post(endpoint, data={
                "fetch": "false",
                "st.page": str(page),
                "st.lastelem": cursor,
            }, headers={
                "Referer": album_url,
                "X-Requested-With": "XMLHttpRequest",
            }, timeout=20)
            return json.dumps({
                "kind": "album",
                "album_id": album_id,
                "page": page,
                "html": self._response_text(response),
                "fetched_all": str(getattr(response, "headers", {}).get("fetchedall", "")).lower() == "true",
            })

        return None

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not isinstance(url, str) or not url.startswith(self.base_url):
            return None
        try:
            data = json.loads(response or "{}")
        except (TypeError, ValueError):
            return None
        kind = data.get("kind")
        if kind == "root":
            return self._root_menu()
        if kind == "message":
            return [{
                "type": "item",
                "title": f"[COLOR grey]{data.get('title', 'OK.ru')}[/COLOR]",
                "link": "",
                "is_playable": "false",
            }]
        if kind == "redirect":
            return [{"type": "dir", "title": "[COLOR deepskyblue]Search Results[/COLOR]", "link": data.get("link", "")}]
        if kind == "catalog":
            rows = _parse_video_cards(data.get("html", ""))
        elif kind == "search_html":
            search_data = _search_data_from_html(data.get("html", ""))
            rows = _search_rows(search_data)
            videos = search_data.get("videos") or {}
            if videos.get("hasMore"):
                rows.append({
                    "type": "dir",
                    "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                    "link": _route_url("search", data.get("query", ""), str(int(data.get("page", 1)) + 1)),
                })
            return rows
        elif kind == "series":
            rows = _parse_series_sliders(data.get("html", ""))
        elif kind == "album":
            rows = _parse_episode_cards(data.get("html", ""))
        elif kind == "search_api":
            videos = (((data.get("data") or {}).get("result") or {}).get("videos") or {})
            rows = _search_rows({"videos": videos})
            if videos.get("hasMore"):
                rows.append({
                    "type": "dir",
                    "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                    "link": _route_url("search", data.get("query", ""), str(int(data.get("page", 1)) + 1)),
                })
            return rows
        else:
            return None

        cursor = _last_element(data.get("html", ""))
        if cursor and not data.get("fetched_all"):
            page = int(data.get("page") or 1) + 1
            if kind in ("catalog", "series"):
                next_link = _route_url("catalog", data.get("catalog_path", ""), str(page), cursor)
            elif kind == "album":
                next_link = _route_url("album", data.get("album_id", ""), str(page), cursor)
            else:
                next_link = ""
            if next_link:
                rows.append({
                    "type": "dir",
                    "title": "[COLOR deepskyblue]Next Page[/COLOR]",
                    "link": next_link,
                })
        return rows

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

        match = re.match(
            r"https?://(?:(?:www|m|mobile)\.)?(?:ok|odnoklassniki)\.ru/video/(?!c)([\d-]+)",
            str(link or ""),
            re.IGNORECASE,
        )
        if not match:
            return None

        video_id = match.group(1)
        canonical_url = f"{BASE_URL}/video/{video_id}"
        try:
            response = self.session.get(canonical_url, headers={
                "User-Agent": self.user_agent,
                "Referer": str(link),
            }, timeout=20)
            options = _player_options(self._response_text(response), video_id)
            if not options:
                xbmcgui.Dialog().notification("OK.ru", "Video unavailable", xbmcgui.NOTIFICATION_WARNING, 3000)
                return True
            if options.get("isExternalPlayer"):
                xbmcgui.Dialog().notification("OK.ru", "External video is not supported", xbmcgui.NOTIFICATION_WARNING, 3000)
                return True
            metadata = _metadata_from_options(options, self.session)
            stream = _select_stream(metadata)
            if not stream:
                message = "Paid video" if _availability_reason(metadata) == "paid" else "Video unavailable"
                xbmcgui.Dialog().notification("OK.ru", message, xbmcgui.NOTIFICATION_WARNING, 3000)
                return True

            movie = metadata.get("movie") or {}
            title = _clean_text(item_data.get("title") or movie.get("title") or "OK.ru Video")
            title = re.sub(r"\[/?COLOR[^\]]*\]", "", title, flags=re.IGNORECASE).strip()
            poster = item_data.get("thumbnail") or movie.get("poster") or options.get("poster") or ""
            summary = _clean_text(item_data.get("summary") or movie.get("description") or title)
            play_url = _kodi_headers(stream["url"], self.user_agent, canonical_url)

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
            if movie.get("duration"):
                info["duration"] = movie.get("duration")
            set_video_info(list_item, info)

            subtitles = [
                track.get("url") for track in (movie.get("subtitleTracks") or [])
                if isinstance(track, dict) and track.get("url")
            ]
            if subtitles:
                try:
                    list_item.setSubtitles(subtitles)
                except AttributeError:
                    pass
            if stream["protocol"] == "hls":
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
            xbmc.log(f"[TheArchives][OK.ru] stream resolve failed: {exc}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification("OK.ru", "Failed to resolve stream", xbmcgui.NOTIFICATION_WARNING, 3000)
            return True

    def from_keyboard(self, default_text="", header="Search OK.ru"):
        keyboard = xbmc.Keyboard(default_text, header, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            return keyboard.getText()
        return None

    def _root_menu(self) -> List[Dict[str, str]]:
        rows = [{
            "type": "dir",
            "title": "[COLOR deepskyblue]Search[/COLOR]",
            "link": _route_url("search"),
            "thumbnail": "resources/media/movies.png",
            "summary": "Search OK.ru videos.",
        }]
        for title, path in CATEGORIES:
            rows.append({
                "type": "dir",
                "title": title,
                "link": _route_url("catalog", path, "1"),
                "thumbnail": "resources/media/movies.png",
                "summary": f"Browse OK.ru {title}.",
            })
        return rows
