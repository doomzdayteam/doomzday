import json
import re
import sys
from html import unescape
from urllib.parse import quote, unquote
from typing import Dict, List, Optional
from uuid import uuid4

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from ..vod_cache import VOD_CACHE, vod_cache_key
from resources.lib.infotagger.helpers import set_video_info


FANART = Addon().getAddonInfo("fanart")

BASE_URL = "https://therokuchannel.roku.com"
CONTENT_API = f"{BASE_URL}/api/v2/content/roku-trc"
HOME_API = f"{BASE_URL}/api/v2/homescreen/v2/home?limit=50"
FREE_PAGE_API = f"{BASE_URL}/api/v2/homescreen/pages/free-movies-and-tv/rendered?limit=50"
SEARCH_API = f"{BASE_URL}/api/v1/search"
CSRF_API = f"{BASE_URL}/api/v1/csrf"
PLAYBACK_API = f"{BASE_URL}/api/v3/playback"
DETAIL_EXPAND = (
    "expand=seasons,seasons.episodes,seasons.episodes.viewOptions,"
    "episodes,episodes.viewOptions,viewOptions"
)

PAGE_IDS = [
    ("free-movies-and-tv", "Free Movies & TV"),
    ("roku-originals", "Roku Originals"),
    ("kids-and-family", "Kids & Family"),
]

DRM_KEY_MARKERS = ("#EXT-X-KEY", "METHOD=SAMPLE-AES", "KEYFORMAT")


def _duration_str(seconds):
    if not seconds:
        return ""
    try:
        total = int(float(seconds))
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    except (ValueError, TypeError):
        return ""


def _strip_html(text):
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", unescape(str(text))).strip()[:700]


def _dictish(value):
    return value if isinstance(value, dict) else {}


def _listish(value):
    return value if isinstance(value, list) else []


def _response_text(response):
    text = getattr(response, "text", None)
    if text is not None:
        return text
    content = getattr(response, "content", b"")
    if isinstance(content, bytes):
        return content.decode("utf-8", "replace")
    return str(content or "")


def _playlist_has_drm(text):
    upper = str(text or "").upper()
    return any(marker in upper for marker in DRM_KEY_MARKERS)


def _kodi_header_query(user_agent, referer=BASE_URL + "/"):
    return (
        f"User-Agent={quote(user_agent, safe='')}"
        f"&Referer={quote(referer, safe='')}"
        f"&Origin={quote(BASE_URL, safe='')}"
    )


def _widevine_license_key(license_url, user_agent="Mozilla/5.0"):
    headers = "Content-Type=application/octet-stream"
    headers += f"&{_kodi_header_query(user_agent)}"
    return f"{license_url}|{headers}|R{{SSM}}|"


def _dash_video_from_view_option(option):
    media = _dictish(option.get("media"))
    for video in _listish(media.get("videos")):
        if isinstance(video, dict) and str(video.get("videoType", "")).upper() == "DASH":
            return video
    return {}


def _dash_playback_payload(item, option):
    video = _dash_video_from_view_option(option)
    item_id = _content_id(item)
    payload = {
        "rokuId": item_id,
        "playId": option.get("playId", ""),
        "mediaFormat": "mpeg-dash",
        "drmType": "widevine",
        "id": item_id,
        "quality": video.get("quality", "fhd"),
        "providerId": option.get("providerId", ""),
    }
    if option.get("adsContentId"):
        payload["adPolicyId"] = option["adsContentId"]
    return payload


def _first_child_playlist_url(master_url, playlist_text):
    if "#EXT-X-STREAM-INF" not in str(playlist_text or ""):
        return ""
    for line in str(playlist_text or "").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            from urllib.parse import urljoin
            return urljoin(master_url, line)
    return ""


def _content_id(item):
    meta = _dictish(item.get("meta"))
    return str(meta.get("id") or meta.get("sid") or item.get("id") or "")


def _description(item):
    desc = item.get("description", "")
    if desc:
        return _strip_html(desc)
    descriptions = _dictish(item.get("descriptions"))
    for key in ("100", "80", "60", "40"):
        entry = _dictish(descriptions.get(key))
        if entry.get("text"):
            return _strip_html(entry["text"])
    for entry in descriptions.values():
        if isinstance(entry, dict) and entry.get("text"):
            return _strip_html(entry["text"])
    return ""


def _rating(item):
    ratings = _listish(item.get("parentalRatings"))
    for rating in ratings:
        if isinstance(rating, dict) and rating.get("code"):
            return str(rating["code"])
    return str(item.get("contentRatingClass") or "")


def _best_image(item, fallback=""):
    image_map = _dictish(item.get("imageMap"))
    for key in ("grid", "detailPoster", "detailBackground", "background"):
        image = image_map.get(key)
        if isinstance(image, dict) and image.get("path"):
            return image["path"]
        if isinstance(image, str) and image.startswith("http"):
            return image

    images = _listish(item.get("images"))
    preferred_types = ("Poster", "Keyart", "Background")
    for image_type in preferred_types:
        for image in images:
            if isinstance(image, dict) and image.get("type") == image_type and image.get("path"):
                return image["path"]
    for image in images:
        if isinstance(image, dict) and image.get("path"):
            return image["path"]
    return fallback


def _collection_contents(data):
    items = []
    for collection in _listish(data.get("collections")):
        for entry in _listish(collection.get("view")):
            content = _dictish(entry.get("content"))
            if content:
                items.append(content)
    return items


def _named_collection_contents(data, title):
    wanted = str(title or "").strip().lower()
    items = []
    for collection in _listish(data.get("collections")):
        collection_title = str(collection.get("title") or "").strip().lower()
        if collection_title != wanted:
            continue
        for entry in _listish(collection.get("view")):
            content = _dictish(entry.get("content"))
            if content:
                items.append(content)
    return items


def _is_free_view_option(option):
    if not isinstance(option, dict) or not option.get("hasMedia", True):
        return False
    provider_id = str(option.get("providerId", "")).lower()
    price = str(option.get("priceDisplay", "")).lower()
    license_name = str(option.get("license", "")).lower()
    return (
        provider_id == "rokuavod"
        or price == "free"
        or license_name == "free"
    )


def _hls_url_from_view_option(option):
    media = _dictish(option.get("media"))
    for video in _listish(media.get("videos")):
        if not isinstance(video, dict):
            continue
        if str(video.get("videoType", "")).upper() == "HLS" and video.get("url"):
            return video["url"]
    for video in _listish(media.get("videos")):
        if isinstance(video, dict) and ".m3u8" in str(video.get("url", "")):
            return video["url"]
    return ""


def _best_view_option(item):
    options = _listish(item.get("viewOptions"))
    for option in options:
        if _is_free_view_option(option) and _hls_url_from_view_option(option):
            return option
    for option in options:
        if _hls_url_from_view_option(option):
            return option
    return {}


def _playback_option_groups(item):
    options = [
        option for option in _listish(item.get("viewOptions"))
        if _is_free_view_option(option)
        and (_dash_video_from_view_option(option) or _hls_url_from_view_option(option))
    ]
    if not options:
        options = [
            option for option in _listish(item.get("viewOptions"))
            if _dash_video_from_view_option(option) or _hls_url_from_view_option(option)
        ]
    dash_options = [option for option in options if _dash_video_from_view_option(option)]
    hls_options = [option for option in options if _hls_url_from_view_option(option)]
    return dash_options, hls_options


def _clean_title(title):
    return re.sub(r"\[/?COLOR[^\]]*\]", "", str(title or "The Roku Channel")).strip()


def _with_kodi_headers(url, user_agent, referer=BASE_URL):
    return (
        f"{url}|{_kodi_header_query(user_agent, referer)}"
    )


def _page_id_from_url(url, prefix):
    return unquote(url.replace(prefix, "", 1).split("?", 1)[0].strip("/"))


class RokuChannel(Plugin):
    

    name = "roku_channel"
    priority = 1050

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
            "Referer": BASE_URL + "/",
            "Accept": "application/json, text/html",
        }
        self._device_id = str(uuid4())
        self.search_url = f"{self.base_url}/search"
        self.vod_search_url = f"{self.base_url}/vod/search"
        self.home_url = f"{self.base_url}/home"
        self.live_url = f"{self.base_url}/section/live-tv"
        self.tv_url = f"{self.base_url}/section/tv-shows"
        self.page_url = f"{self.base_url}/page"
        self.details_url = f"{self.base_url}/details"

    def _headers(self, referer=BASE_URL + "/", accept="application/json"):
        return {
            "User-Agent": self.user_agent,
            "Referer": referer,
            "Origin": BASE_URL,
            "Accept": accept,
        }

    def _headers_with_csrf(self):
        headers = self._headers()
        token = self._csrf_token()
        if token:
            headers["csrf-token"] = token
        return headers

    def _cached_vod_response(self, key, kind, fetcher):
        return VOD_CACHE.get_or_set_response(self.name, key, kind, fetcher)

    def _vod_menu_cache_kind(self, url):
        if url in (self.search_url, self.vod_search_url):
            return "search"
        if url in (self.home_url, self.tv_url):
            return "catalog"
        if url.startswith(self.page_url + "/") or url.startswith(self.details_url + "/"):
            return "catalog"
        return ""

    def _csrf_token(self):
        try:
            resp = self.session.get(BASE_URL + "/", headers=self._headers(accept="text/html"))
            match = re.search(r"csrf:\s*[\"']([^\"']+)", resp.text)
            if match:
                return match.group(1)
        except Exception:
            pass
        try:
            resp = self.session.get(CSRF_API, headers=self._headers())
            data = resp.json()
            return data.get("csrf") or data.get("csfr") or ""
        except Exception:
            return ""

    def get_list(self, url):
        if url == self.base_url:
            return json.dumps({"root": True})

        if url == self.home_url:
            try:
                return self._cached_vod_response(
                    vod_cache_key("home", HOME_API),
                    "catalog",
                    lambda: self.session.get(HOME_API, headers=self._headers()).text,
                )
            except Exception:
                return None

        if url in (self.live_url, self.tv_url):
            collection_title = "Live TV" if url == self.live_url else "Recently Added TV"
            try:
                if url == self.tv_url:
                    raw_page = self._cached_vod_response(
                        vod_cache_key("tv", FREE_PAGE_API),
                        "catalog",
                        lambda: self.session.get(FREE_PAGE_API, headers=self._headers()).text,
                    )
                    data = json.loads(raw_page or "{}")
                else:
                    data = self.session.get(FREE_PAGE_API, headers=self._headers()).json()
                return json.dumps({
                    "_collection_title": collection_title,
                    "_page": data,
                })
            except Exception:
                return None

        if url.startswith(self.page_url + "/"):
            page_id = _page_id_from_url(url, self.page_url)
            api_url = f"{BASE_URL}/api/v2/homescreen/pages/{quote(page_id, safe='')}/rendered?limit=50"
            try:
                return self._cached_vod_response(
                    vod_cache_key("page", page_id, api_url),
                    "catalog",
                    lambda: self.session.get(api_url, headers=self._headers()).text,
                )
            except Exception:
                return None

        if url.startswith(self.details_url + "/"):
            content_id = _page_id_from_url(url, self.details_url)
            try:
                api_url = f"{CONTENT_API}/{content_id}?{DETAIL_EXPAND}"
                return self._cached_vod_response(
                    vod_cache_key("details", content_id, api_url),
                    "catalog",
                    lambda: self.session.get(api_url, headers=self._headers()).text,
                )
            except Exception:
                return None

        if url in (self.search_url, self.vod_search_url):
            query = self.from_keyboard()
            if not query:
                sys.exit()
            headers = self._headers()
            token = self._csrf_token()
            if token:
                headers["csrf-token"] = token
            try:
                raw_results = self._cached_vod_response(
                    vod_cache_key("search", query),
                    "search",
                    lambda: self.session.post(
                        SEARCH_API,
                        headers=headers,
                        json={"query": query},
                    ).text,
                )
                return json.dumps({"_query": query, "_results": json.loads(raw_results or "{}")})
            except Exception:
                return json.dumps({"_query": query, "_results": {"view": []}})

        return None

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not url.startswith(self.base_url):
            return None

        cache_kind = self._vod_menu_cache_kind(url)
        if cache_kind:
            return VOD_CACHE.get_or_set_menu(
                self.name,
                vod_cache_key("menu", url, response),
                cache_kind,
                lambda: self._parse_list_uncached(url, response),
            )
        return self._parse_list_uncached(url, response)

    def _parse_list_uncached(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not url.startswith(self.base_url):
            return None

        itemlist = []

        if url == self.base_url:
            itemlist.append({
                "type": "item",
                "title": "[COLOR khaki]Requires Widevine[/COLOR]",
                "link": (
                    "message/Roku Channel playback uses Widevine DRM. "
                    "Use the InputStream Helper link below to install or configure Widevine."
                ),
                "summary": "Roku Channel live TV and TV episodes require Widevine DRM support.",
            })
            itemlist.append({
                "type": "item",
                "title": "[COLOR lawngreen]Click to Install Widevine / InputStream Helper[/COLOR]",
                "link": "inputstream_helper",
                "summary": "Install or configure InputStream Adaptive and Widevine for Roku playback",
            })
            itemlist.append({
                "type": "dir",
                "title": "[COLOR deepskyblue]Search The Roku Channel[/COLOR]",
                "link": self.search_url,
            })
            itemlist.append({
                "type": "dir",
                "title": "[COLOR orange]-- Home --[/COLOR]",
                "link": self.home_url,
            })
            itemlist.append({
                "type": "dir",
                "title": "[COLOR orange]-- Live TV --[/COLOR]",
                "link": self.live_url,
            })
            itemlist.append({
                "type": "dir",
                "title": "[COLOR orange]-- TV Shows --[/COLOR]",
                "link": self.tv_url,
            })
            for page_id, label in PAGE_IDS:
                itemlist.append({
                    "type": "dir",
                    "title": f"[COLOR cyan]>[/COLOR] {label}",
                    "link": f"{self.page_url}/{quote(page_id)}",
                })
            return itemlist

        try:
            data = json.loads(response or "{}")
        except (json.JSONDecodeError, TypeError):
            data = {}

        if url in (self.search_url, self.vod_search_url):
            data = _dictish(data.get("_results"))

        collection_title = data.get("_collection_title", "")
        if collection_title:
            data = _dictish(data.get("_page"))

        if (
            url == self.home_url
            or url in (self.live_url, self.tv_url)
            or url.startswith(self.page_url + "/")
            or url in (self.search_url, self.vod_search_url)
        ):
            self._add_page_items(
                itemlist,
                data,
                collection_title=collection_title,
                include_live=(url != self.vod_search_url),
            )
            if not itemlist:
                itemlist.append({
                    "type": "dir",
                    "title": "[COLOR grey]No Roku Channel content found[/COLOR]",
                    "link": self.base_url,
                })
            return itemlist

        if url.startswith(self.details_url + "/"):
            self._add_detail_items(itemlist, data)
            if not itemlist:
                itemlist.append({
                    "type": "dir",
                    "title": "[COLOR grey]Content not available[/COLOR]",
                    "link": self.base_url,
                })
            return itemlist

        return itemlist

    def _add_page_items(self, itemlist, data, collection_title="", include_live=True):
        if collection_title:
            for content in _named_collection_contents(data, collection_title):
                self._add_content_item(itemlist, content, include_live=include_live)
            return

        for collection in _listish(data.get("collections")):
            label = _dictish(collection.get("meta")).get("title") or collection.get("title")
            view = _listish(collection.get("view"))
            if label and view:
                itemlist.append({
                    "type": "dir",
                    "title": f"[COLOR orange]-- {label} --[/COLOR]",
                    "link": self.base_url,
                })
            for entry in view:
                self._add_content_item(itemlist, _dictish(entry.get("content")), include_live=include_live)

        for entry in _listish(data.get("view")):
            self._add_content_item(itemlist, _dictish(entry.get("content")), include_live=include_live)

    def _add_detail_items(self, itemlist, item):
        item_type = str(item.get("type", "")).lower()
        if item_type == "series":
            seasons = _listish(item.get("seasons"))
            for season in seasons:
                season_number = season.get("seasonNumber", "")
                episodes = _listish(season.get("episodes"))
                if episodes:
                    itemlist.append({
                        "type": "dir",
                        "title": f"[COLOR orange]-- Season {season_number or '?'} --[/COLOR]",
                        "link": self.base_url,
                        "thumbnail": _best_image(season, _best_image(item)),
                        "summary": _description(season) or _description(item),
                    })
                for episode in episodes:
                    self._add_content_item(itemlist, episode, series_thumb=_best_image(item))
            if not itemlist:
                for episode in _listish(item.get("episodes")):
                    self._add_content_item(itemlist, episode, series_thumb=_best_image(item))
            return

        self._add_content_item(itemlist, item, force_playable=True)

    def _add_content_item(self, itemlist, item, series_thumb="", force_playable=False, include_live=True):
        if not isinstance(item, dict):
            return
        content_id = _content_id(item)
        title = item.get("title", "")
        if not content_id or not title:
            return

        item_type = str(item.get("type", _dictish(item.get("meta")).get("mediaType", ""))).lower()
        if not include_live and item_type in ("channel", "linear", "live"):
            return
        thumb = _best_image(item, series_thumb)
        summary = _description(item)
        year = item.get("releaseYear") or item.get("startYear") or ""
        rating = _rating(item)
        duration = _duration_str(item.get("runTimeSeconds"))
        info = " | ".join(str(part) for part in (year, rating, duration) if part)

        if item_type == "series" and not force_playable:
            display = f"[COLOR deepskyblue]TV[/COLOR] {title}"
            if info:
                display += f" [COLOR grey]({info})[/COLOR]"
            itemlist.append({
                "type": "dir",
                "title": display,
                "link": f"{self.details_url}/{content_id}",
                "thumbnail": thumb,
                "summary": summary,
            })
            return

        display = f"[COLOR red]>[/COLOR] {title}"
        if item_type == "episode":
            season = item.get("seasonNumber", "")
            episode = item.get("episodeNumber", "")
            prefix = f"S{season}E{episode} " if season and episode else ""
            display = f"[COLOR limegreen]>[/COLOR] {prefix}{title}"
        if info:
            display += f" [COLOR grey]({info})[/COLOR]"

        itemlist.append({
            "type": "item",
            "title": display,
            "link": f"{self.details_url}/{content_id}",
            "thumbnail": thumb,
            "summary": summary,
            "is_playable": "true",
        })

    def _resolve_playback_link(self, link):
        if link.startswith(self.details_url + "/"):
            content_id = _page_id_from_url(link, self.details_url)
            resp = self.session.get(
                f"{CONTENT_API}/{content_id}?{DETAIL_EXPAND}",
                headers=self._headers(),
            )
            item = resp.json()
            dash_options, hls_options = _playback_option_groups(item)
            if not dash_options and not hls_options:
                return {}, item, "Free stream not available"

            for option in dash_options:
                widevine = self._widevine_playback(option, item)
                if widevine:
                    return widevine, item, ""

            for option in hls_options:
                hls_url = _hls_url_from_view_option(option)
                clear_url = self._validated_hls_url(hls_url)
                if clear_url:
                    return {"url": clear_url, "type": "hls"}, item, ""

            return {}, item, "DRM stream requires Widevine/inputstream.adaptive"
        return {"url": link, "type": "hls"}, {}, ""

    def _widevine_playback(self, option, item):
        if not _dash_video_from_view_option(option):
            return {}
        try:
            resp = self.session.post(
                PLAYBACK_API,
                headers=self._headers_with_csrf(),
                json=_dash_playback_payload(item, option),
                timeout=10,
            )
            data = resp.json()
        except Exception:
            return {}

        url = data.get("url", "")
        license_url = _dictish(_dictish(data.get("drm")).get("widevine")).get("licenseServer", "")
        if not url or not license_url:
            videos = _listish(_dictish(data.get("playbackMedia")).get("videos"))
            for video in videos:
                url = url or video.get("url", "")
                drm_params = _dictish(video.get("drmParams"))
                license_url = license_url or drm_params.get("licenseServerURL", "")
                if url and license_url:
                    break
        if not url or not license_url:
            return {}
        return {
            "url": url,
            "type": "widevine",
            "license_key": _widevine_license_key(license_url, self.user_agent),
        }

    def _validated_hls_url(self, hls_url):
        if not hls_url:
            return ""

        master_url = hls_url
        master_text = ""

        try:
            resp = self.session.get(
                hls_url,
                headers=self._headers(),
                allow_redirects=False,
                timeout=10,
            )
            status_code = int(getattr(resp, "status_code", 200) or 200)
            location = getattr(resp, "headers", {}).get("Location", "")
            if 300 <= status_code < 400 and location:
                master_url = location
            else:
                master_text = _response_text(resp)
                if not master_text.lstrip().startswith("#EXTM3U"):
                    return ""
        except Exception:
            return ""

        try:
            if not master_text:
                resp = self.session.get(master_url, headers=self._headers(), timeout=10)
                master_text = _response_text(resp)
            if not master_text.lstrip().startswith("#EXTM3U"):
                return ""
            if _playlist_has_drm(master_text):
                return ""
            child_url = _first_child_playlist_url(master_url, master_text)
            if child_url:
                resp = self.session.get(child_url, headers=self._headers(), timeout=10)
                if _playlist_has_drm(_response_text(resp)):
                    return ""
        except Exception:
            return ""

        return master_url

    def play_video(self, item: str) -> Optional[bool]:
        data = {}
        link = item
        try:
            if isinstance(item, bytes):
                item = item.decode("utf-8")
            data = json.loads(item)
            link = data.get("link", "")
        except (json.JSONDecodeError, TypeError, AttributeError):
            link = item.decode("utf-8") if isinstance(item, bytes) else item

        if not isinstance(link, str) or (
            "therokuchannel.roku.com" not in link
            and "sr.roku.com" not in link
            and "delivery.roku.com" not in link
        ):
            return None

        try:
            playback, detail, failure = self._resolve_playback_link(link)
        except Exception:
            xbmcgui.Dialog().notification(
                "The Roku Channel",
                "Failed to resolve stream",
                xbmcgui.NOTIFICATION_WARNING,
                3000,
            )
            return True

        if not playback.get("url"):
            xbmcgui.Dialog().notification(
                "The Roku Channel",
                failure or "Free stream not available",
                xbmcgui.NOTIFICATION_WARNING,
                3000,
            )
            return True

        title = _clean_title(data.get("title") or detail.get("title") or "The Roku Channel")
        thumb = data.get("thumbnail") or _best_image(detail)
        summary = data.get("summary") or _description(detail)
        play_url = playback["url"]
        if playback.get("type") == "hls":
            play_url = _with_kodi_headers(play_url, self.user_agent, BASE_URL)

        liz = xbmcgui.ListItem(title, path=play_url)
        liz.setProperty("IsPlayable", "true")
        if thumb:
            liz.setArt({
                "thumb": thumb,
                "icon": thumb,
                "poster": thumb,
                "fanart": FANART,
            })

        set_video_info(liz, {"title": title, "plot": summary})
        if playback.get("type") == "widevine":
            if not self._ensure_widevine_inputstream():
                xbmcgui.Dialog().notification(
                    "The Roku Channel",
                    "inputstream.adaptive/Widevine is not available",
                    xbmcgui.NOTIFICATION_WARNING,
                    3000,
                )
                return True
            self._configure_widevine_item(liz, playback["license_key"])
        else:
            liz.setMimeType("application/vnd.apple.mpegurl")
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass

        xbmc.Player().play(play_url, liz)
        return True

    def _ensure_widevine_inputstream(self):
        try:
            import inputstreamhelper
            helper = inputstreamhelper.Helper("mpd", drm="com.widevine.alpha")
            return helper.check_inputstream()
        except Exception:
            return True

    def _configure_widevine_item(self, liz, license_key):
        liz.setMimeType("application/dash+xml")
        liz.setProperty("inputstream", "inputstream.adaptive")
        liz.setProperty("inputstream.adaptive.manifest_type", "mpd")
        liz.setProperty("inputstream.adaptive.stream_headers", _kodi_header_query(self.user_agent))
        liz.setProperty("inputstream.adaptive.license_type", "com.widevine.alpha")
        liz.setProperty("inputstream.adaptive.license_key", license_key)

    def from_keyboard(self, default_text="", header="Search The Roku Channel"):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
