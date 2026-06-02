import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse
from typing import Dict, List, Optional

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info
from ..DI import DI


FANART = Addon().getAddonInfo("fanart")

BASE_URL = "https://www.reddit.com"
SEARCH_VIDEO_URL = f"{BASE_URL}/search/video"
SEARCH_LIVE_URL = f"{BASE_URL}/search/live"
SUBREDDIT_URL = f"{BASE_URL}/r"
SUBREDDIT_SORT_MENU = "thearchives_sort"

DIRECT_MEDIA_EXTS = (".m3u8", ".mp4", ".webm", ".mov", ".m4v")
IMAGE_MEDIA_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif")
REDDIT_MEDIA_HOSTS = ("v.redd.it", "reddit.com", "redd.it", "redditmedia.com")
YTDLP_HOSTS = (
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "twitch.tv",
    "clips.twitch.tv",
    "kick.com",
    "dailymotion.com",
    "rumble.com",
)

SEARCH_SORTS = {
    "new": "Newest",
    "relevance": "Relevant",
}
SUBREDDIT_SORTS = (
    ("new", "Newest"),
    ("hot", "Hot"),
    ("top", "Top"),
    ("rising", "Rising"),
)


def _clean_text(value):
    if value is None:
        return ""
    value = unescape(str(value))
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip()


def _clean_url(value):
    return unescape(str(value or "").replace("\\/", "/")).strip()


def _url_host(url):
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _is_reddit_media_url(url):
    host = _url_host(url)
    return any(host == item or host.endswith("." + item) for item in REDDIT_MEDIA_HOSTS)


def _is_direct_media_url(url):
    path = urlparse(url).path.lower()
    return path.endswith(DIRECT_MEDIA_EXTS)


def _is_image_media_url(url):
    path = urlparse(url).path.lower()
    return path.endswith(IMAGE_MEDIA_EXTS)


def _host_matches(host, choices):
    return any(host == item or host.endswith("." + item) for item in choices)


def _is_ytdlp_supported_external(url):
    host = _url_host(url)
    if not host or _host_matches(host, REDDIT_MEDIA_HOSTS):
        return False
    return _host_matches(host, YTDLP_HOSTS)


def _is_vreddit_url(url):
    return _url_host(url) == "v.redd.it"


def _is_reddit_post_url(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return _host_matches(host, ("reddit.com",)) and "/comments/" in parsed.path


def _vreddit_hls_url(url):
    parsed = urlparse(url)
    video_id = parsed.path.strip("/").split("/")[0]
    if not video_id:
        return ""
    return f"https://v.redd.it/{video_id}/HLSPlaylist.m3u8"


def _stream_type(url):
    path = url.split("|", 1)[0].lower()
    if ".m3u8" in path:
        return "hls"
    return "direct"


def _with_kodi_headers(url, user_agent, referer):
    if not url or "|" in url:
        return url
    headers = {
        "User-Agent": user_agent,
        "Referer": referer or BASE_URL,
    }
    return f"{url}|{urlencode(headers)}"


def _append_query(url, values):
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    for key, value in values.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = [str(value)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _duration_label(seconds):
    try:
        seconds = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _post_permalink(post):
    permalink = post.get("permalink") or ""
    if permalink.startswith("http"):
        return permalink
    if permalink:
        return BASE_URL + permalink
    return post.get("url") or BASE_URL


def _thumbnail(post):
    preview = post.get("preview") or {}
    images = preview.get("images") or []
    if images:
        source = images[0].get("source") or {}
        url = _clean_url(source.get("url"))
        if url.startswith("http"):
            return url

    media = post.get("secure_media") or post.get("media") or {}
    oembed = media.get("oembed") or {}
    url = _clean_url(oembed.get("thumbnail_url"))
    if url.startswith("http"):
        return url

    url = _clean_url(post.get("thumbnail"))
    if url.startswith("http"):
        return url
    return ""


def _reddit_video_from_post(post):
    for media_key in ("secure_media", "media"):
        media = post.get(media_key) or {}
        reddit_video = media.get("reddit_video") or {}
        if reddit_video:
            return reddit_video

    preview = post.get("preview") or {}
    reddit_video = preview.get("reddit_video_preview") or {}
    if reddit_video:
        return reddit_video

    for crosspost in post.get("crosspost_parent_list") or []:
        reddit_video = _reddit_video_from_post(crosspost)
        if reddit_video:
            return reddit_video

    return {}


def _media_from_post(post):
    reddit_video = _reddit_video_from_post(post)
    if reddit_video:
        hls_url = _clean_url(reddit_video.get("hls_url"))
        fallback_url = _clean_url(reddit_video.get("fallback_url"))
        stream_url = hls_url or fallback_url
        if stream_url:
            return {
                "url": stream_url,
                "stream_type": "hls" if hls_url else _stream_type(stream_url),
                "duration": _duration_label(reddit_video.get("duration")),
                "height": reddit_video.get("height"),
                "width": reddit_video.get("width"),
            }

    url = _clean_url(post.get("url_overridden_by_dest") or post.get("url"))
    if url and _is_direct_media_url(url):
        return {
            "url": url,
            "stream_type": _stream_type(url),
            "duration": "",
            "height": "",
            "width": "",
        }

    return None


def _media_from_rss_link(url):
    url = _clean_url(url)
    if not url:
        return None
    if _is_vreddit_url(url):
        hls_url = _vreddit_hls_url(url)
        if hls_url:
            return {
                "url": hls_url,
                "stream_type": "hls",
                "duration": "",
                "height": "",
                "width": "",
            }
    if _is_direct_media_url(url):
        return {
            "url": url,
            "stream_type": _stream_type(url),
            "duration": "",
            "height": "",
            "width": "",
        }
    return None


def _external_from_rss_link(url):
    url = _clean_url(url)
    if not url:
        return None
    return {
        "url": url,
        "host": _url_host(url) or "external",
    }


def _summary(post, media):
    parts = []
    subreddit = post.get("subreddit")
    if subreddit:
        parts.append(f"r/{subreddit}")
    author = post.get("author")
    if author:
        parts.append(f"u/{author}")
    score = post.get("score")
    if score is not None:
        parts.append(f"{score} points")
    comments = post.get("num_comments")
    if comments is not None:
        parts.append(f"{comments} comments")
    if media.get("duration"):
        parts.append(media["duration"])
    if media.get("height"):
        parts.append(f"{media['height']}p")

    text = _clean_text(post.get("selftext") or post.get("link_flair_text"))
    if text:
        parts.append(text[:180])
    return " | ".join(parts)


def _rss_summary(entry, media):
    parts = []
    subreddit = entry.get("subreddit")
    if subreddit:
        parts.append(subreddit)
    author = entry.get("author")
    if author:
        parts.append(author)
    if media.get("duration"):
        parts.append(media["duration"])
    if media.get("height"):
        parts.append(f"{media['height']}p")
    return " | ".join(parts)


def _rss_external_summary(entry, external):
    parts = []
    subreddit = entry.get("subreddit")
    if subreddit:
        parts.append(subreddit)
    author = entry.get("author")
    if author:
        parts.append(author)
    host = external.get("host")
    if host:
        parts.append(host)
    url = external.get("url")
    if url:
        parts.append(url)
    return " | ".join(parts)


def _search_query(query, live=False):
    query = _clean_text(query)
    lowered = query.lower()
    parts = []
    if query:
        parts.append(query)
    has_native_filter = "site:v.redd.it" in lowered or "url:v.redd.it" in lowered
    if live:
        if "live" not in lowered and "stream" not in lowered:
            parts.append("live stream")
        elif "stream" not in lowered:
            parts.append("stream")
    elif not has_native_filter and "video" not in lowered and "videos" not in lowered:
        parts.append("video")
    return " ".join(parts).strip()


def _message_item(title, link=BASE_URL, summary=""):
    return [{
        "type": "dir",
        "title": title,
        "link": link,
        "summary": summary,
    }]


def _decode_item(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(value)


def _split_kodi_url(url):
    if "|" not in url:
        return url, ""
    return url.split("|", 1)


def load_ytdlp():
    external_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "external"))
    if external_path not in sys.path:
        sys.path.insert(0, external_path)
    import yt_dlp
    return yt_dlp


def ytdlp_params(extra=None):
    params = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ignore_no_formats_error": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["all"],
                "skip": ["authcheck"],
            },
            "youtubetab": {
                "skip": ["authcheck"],
            },
        },
    }
    if extra:
        params.update(extra)
    return params


def _is_hls_stream(stream):
    protocol = stream.get("protocol") or ""
    url = stream.get("url") or ""
    return protocol.startswith("m3u8") or ".m3u8" in url.lower()


def _has_audio_and_video(stream):
    return (
        stream.get("url")
        and stream.get("vcodec") != "none"
        and stream.get("acodec") != "none"
    )


def _select_best_stream(info):
    formats = [stream for stream in info.get("formats", []) if _has_audio_and_video(stream)]
    progressive = [
        stream for stream in formats
        if not _is_hls_stream(stream) and stream.get("protocol") in (None, "http", "https")
    ]
    if progressive:
        return max(progressive, key=lambda stream: stream.get("height") or 0)
    hls = [stream for stream in formats if _is_hls_stream(stream)]
    if hls:
        return max(hls, key=lambda stream: stream.get("height") or 0)
    if info.get("url"):
        return info
    raise ValueError("yt-dlp did not return a playable stream URL")


def _with_headers(url, headers=None):
    if not headers:
        return url
    return f"{url}|{urlencode(headers)}"


def resolve_ytdlp_stream(url):
    yt_dlp = load_ytdlp()
    with yt_dlp.YoutubeDL(ytdlp_params()) as ydl:
        info = ydl.extract_info(url, download=False)
    if "entries" in info and info["entries"]:
        info = info["entries"][0]
    stream = _select_best_stream(info)
    headers = stream.get("http_headers") or info.get("http_headers") or {}
    stream_url = stream["url"]
    if not _is_hls_stream(stream):
        stream_url = _with_headers(stream_url, headers)
    return info, stream, stream_url, headers


def _xml_text(node, path, namespaces):
    found = node.find(path, namespaces)
    return found.text if found is not None and found.text else ""


def _xml_attr(node, path, attr, namespaces):
    found = node.find(path, namespaces)
    return found.attrib.get(attr, "") if found is not None else ""


def _links_from_html(html):
    html = unescape(html or "")
    return re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, flags=re.I | re.S)


def _rss_external_link(content_html):
    for href, label in _links_from_html(content_html):
        label = re.sub(r"<[^>]+>", "", unescape(label)).strip().lower()
        href = _clean_url(href)
        if label == "[link]" and href:
            return href
    return ""


def _post_from_comments_json(response):
    data = json.loads(response or "[]")
    listings = data if isinstance(data, list) else [data]
    for listing in listings:
        if not isinstance(listing, dict):
            continue
        listing_data = listing.get("data") or {}
        for child in listing_data.get("children") or []:
            post = child.get("data") if isinstance(child, dict) else None
            if isinstance(post, dict) and _media_from_post(post):
                return post
    return None


class Reddit(Plugin):
    name = "reddit"
    priority = 1060

    POPULAR_VIDEO_SUBREDDITS = [
        ("videos", "r/videos"),
        ("livestreamfail", "r/LivestreamFail"),
        ("sports", "r/sports"),
        ("publicfreakout", "r/PublicFreakout"),
        ("documentaries", "r/Documentaries"),
    ]

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
            "Accept": "application/json",
            "Referer": BASE_URL,
        }

    def get_list(self, url):
        if not str(url).startswith(BASE_URL):
            return None

        if url.rstrip("/") == BASE_URL:
            return json.dumps({"items": []})

        if self._is_subreddit_sort_menu_url(url):
            return json.dumps({"items": []})

        search_input = self._search_input_for(url) if self._is_search_url(url) else None
        api_url = self._api_url_for(url, search_input)
        if not api_url:
            return None

        response = self.session.get(api_url)
        status_code = getattr(response, "status_code", 200)
        text = response.text or ""
        if status_code != 200 or not text.lstrip().startswith(("{", "[")):
            rss_url = self._rss_url_for(url, search_input)
            if rss_url:
                response = self.session.get(rss_url)
        return response.text

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not str(url).startswith(BASE_URL):
            return None

        if url.rstrip("/") == BASE_URL:
            return self._root_items()

        if self._is_subreddit_sort_menu_url(url):
            return self._subreddit_sort_items(url)

        if (response or "").lstrip().startswith("<?xml") or "<feed" in (response or "")[:200]:
            return self._parse_rss_list(url, response)

        itemlist = []
        try:
            data = json.loads(response or "{}")
        except (TypeError, json.JSONDecodeError):
            return _message_item(
                "[COLOR grey]Reddit did not return usable JSON[/COLOR]",
                self.base_url,
                "Reddit may have blocked the request or returned an error page. Try again later.",
            )

        listing = data[0] if isinstance(data, list) and data else data
        if not isinstance(listing, dict):
            return _message_item(
                "[COLOR grey]Reddit response format was not recognized[/COLOR]",
                self.base_url,
            )
        listing_data = listing.get("data", {}) if isinstance(listing, dict) else {}
        children = listing_data.get("children", [])

        for child in children:
            post = child.get("data", {}) if isinstance(child, dict) else {}
            media = _media_from_post(post)
            if not media:
                continue
            itemlist.append(self._item_from_post(post, media))

        after = listing_data.get("after")
        if after:
            itemlist.append({
                "type": "dir",
                "title": "[COLOR deepskyblue]Next Page ->[/COLOR]",
                "link": _append_query(url, {"after": after}),
            })

        if not itemlist:
            itemlist.append({
                "type": "dir",
                "title": "[COLOR grey]No directly playable Reddit videos found[/COLOR]",
                "link": self.base_url,
            })

        return itemlist

    def _parse_rss_list(self, url, response):
        playable_items = []
        external_items = []
        namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "media": "http://search.yahoo.com/mrss/",
        }
        try:
            root = ET.fromstring(response)
        except ET.ParseError:
            return _message_item(
                "[COLOR grey]Reddit RSS response could not be parsed[/COLOR]",
                self.base_url,
            )

        for entry_node in root.findall("atom:entry", namespaces):
            content_html = _xml_text(entry_node, "atom:content", namespaces)
            external_url = _rss_external_link(content_html)
            if self._is_search_url(url) and _is_image_media_url(external_url):
                continue
            media = _media_from_rss_link(external_url)

            permalink = _xml_attr(entry_node, "atom:link", "href", namespaces) or self.base_url
            thumbnail = _xml_attr(entry_node, "media:thumbnail", "url", namespaces)
            entry = {
                "title": _clean_text(_xml_text(entry_node, "atom:title", namespaces) or "Untitled Reddit Video"),
                "author": _clean_text(_xml_text(entry_node, "atom:author/atom:name", namespaces)),
                "subreddit": _clean_text(_xml_attr(entry_node, "atom:category", "label", namespaces)),
                "permalink": permalink,
                "thumbnail": _clean_url(thumbnail),
            }
            if media:
                playable_items.append(self._item_from_rss_entry(entry, media))
            else:
                external = _external_from_rss_link(external_url)
                if external:
                    item = self._item_from_external_rss_entry(
                        entry,
                        external,
                        allow_reddit_post_resolve=True,
                    )
                    if item.get("type") == "item" and item.get("reddit_stream_type") != "reddit_post":
                        playable_items.append(item)
                    else:
                        external_items.append(item)

        itemlist = playable_items + external_items
        if not itemlist:
            itemlist.append({
                "type": "dir",
                "title": "[COLOR grey]No Reddit video posts found[/COLOR]",
                "link": self.base_url,
                "summary": "RSS loaded, but no link posts were available.",
            })
        return itemlist

    def play_video(self, item):
        try:
            data = _decode_item(item)
        except (TypeError, ValueError):
            return None

        if not data.get("reddit_stream_type"):
            return None

        stream_url = data.get("link")
        if not stream_url:
            return None

        title = data.get("title") or "Reddit"
        thumbnail = data.get("thumbnail") or ""
        stream_info = {}
        headers = {}
        if data.get("reddit_stream_type") == "reddit_post":
            try:
                post, media = self._resolve_reddit_post_media(data.get("reddit_external_url") or stream_url)
            except Exception as exc:
                xbmc.log(f"[TheArchives][Reddit] Reddit post resolver failed: {exc}", xbmc.LOGERROR)
                return True
            if not media:
                xbmc.log("[TheArchives][Reddit] Reddit post did not contain a playable native video", xbmc.LOGERROR)
                return True
            title = _clean_text(post.get("title")) or title
            thumbnail = _thumbnail(post) or thumbnail
            permalink = _post_permalink(post)
            stream_url = media["url"]
            if _is_reddit_media_url(stream_url):
                stream_url = _with_kodi_headers(stream_url, self.user_agent, permalink)
            data["reddit_stream_type"] = media["stream_type"]
            data["summary"] = _summary(post, media) or data.get("summary", "")

        if data.get("reddit_stream_type") == "ytdlp":
            try:
                info, stream_info, stream_url, headers = resolve_ytdlp_stream(
                    data.get("reddit_external_url") or stream_url
                )
            except Exception as exc:
                xbmc.log(f"[TheArchives][Reddit] yt-dlp resolver failed: {exc}", xbmc.LOGERROR)
                return True
            title = data.get("title") or info.get("title") or title
            thumbnail = data.get("thumbnail") or info.get("thumbnail") or thumbnail

        list_item = xbmcgui.ListItem(title, path=stream_url)
        set_video_info(list_item, {
            "title": title,
            "plot": data.get("summary", ""),
        })
        if thumbnail:
            list_item.setArt({
                "thumb": thumbnail,
                "icon": thumbnail,
                "poster": thumbnail,
                "fanart": thumbnail or FANART,
            })

        base_stream_url, stream_headers = _split_kodi_url(stream_url)
        if data.get("reddit_stream_type") == "hls" or ".m3u8" in base_stream_url.lower() or _is_hls_stream(stream_info):
            list_item.setProperty("inputstream", "inputstream.ffmpegdirect")
            list_item.setProperty("inputstream.ffmpegdirect.manifest_type", "hls")
            if stream_headers:
                list_item.setProperty("inputstream.ffmpegdirect.stream_headers", stream_headers)
            elif headers:
                list_item.setProperty("inputstream.ffmpegdirect.stream_headers", urlencode(headers))
            list_item.setMimeType("application/x-mpegURL")
        else:
            ext = base_stream_url.rsplit(".", 1)[-1].lower()
            if ext in ("mp4", "m4v", "webm", "mov"):
                list_item.setMimeType(f"video/{ext}")

        list_item.setProperty("IsPlayable", "true")
        xbmc.Player().play(stream_url, list_item)
        return True

    def _root_items(self):
        items = [
            {
                "type": "dir",
                "title": "[COLOR deepskyblue]Search Reddit Videos - Newest[/COLOR]",
                "link": _append_query(SEARCH_VIDEO_URL, {"sort": "new"}),
                "summary": "Search Reddit for directly playable hosted videos, newest first.",
            },
            {
                "type": "dir",
                "title": "[COLOR deepskyblue]Search Reddit Videos - Relevant[/COLOR]",
                "link": _append_query(SEARCH_VIDEO_URL, {"sort": "relevance"}),
                "summary": "Search Reddit for directly playable hosted videos by relevance.",
            },
            {
                "type": "dir",
                "title": "[COLOR deepskyblue]Search Reddit Live Streams - Newest[/COLOR]",
                "link": _append_query(SEARCH_LIVE_URL, {"sort": "new"}),
                "summary": "Search Reddit for live stream posts, newest first.",
            },
            {
                "type": "dir",
                "title": "[COLOR deepskyblue]Search Reddit Live Streams - Relevant[/COLOR]",
                "link": _append_query(SEARCH_LIVE_URL, {"sort": "relevance"}),
                "summary": "Search Reddit for live stream posts by relevance.",
            },
            {
                "type": "dir",
                "title": "[COLOR orange]-- Video Subreddits --[/COLOR]",
                "link": BASE_URL,
            },
        ]

        for subreddit, label in self.POPULAR_VIDEO_SUBREDDITS:
            items.append({
                "type": "dir",
                "title": label,
                "link": f"{SUBREDDIT_URL}/{subreddit}/{SUBREDDIT_SORT_MENU}",
                "summary": f"Choose sort order for {label}.",
            })
        return items

    def _is_search_url(self, url):
        return str(url).startswith(SEARCH_VIDEO_URL) or str(url).startswith(SEARCH_LIVE_URL)

    def _is_subreddit_sort_menu_url(self, url):
        parsed = urlparse(str(url))
        parts = [part for part in parsed.path.split("/") if part]
        return len(parts) == 3 and parts[0] == "r" and parts[2] == SUBREDDIT_SORT_MENU

    def _subreddit_sort_items(self, url):
        parsed = urlparse(str(url))
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            return _message_item("[COLOR grey]Subreddit sort options unavailable[/COLOR]", self.base_url)
        subreddit = parts[1]
        label = f"r/{subreddit}"
        items = []
        for index, (sort, sort_label) in enumerate(SUBREDDIT_SORTS):
            title = f"{label} - {sort_label}"
            if index == 0:
                title = f"[COLOR deepskyblue]{title}[/COLOR]"
            items.append({
                "type": "dir",
                "title": title,
                "link": f"{SUBREDDIT_URL}/{quote(subreddit)}/{sort}",
                "summary": f"Browse {label} sorted by {sort_label.lower()}.",
            })
        return items

    def _search_sort_for(self, url, is_live_search):
        parsed = urlparse(str(url))
        query = parse_qs(parsed.query)
        selected = ((query.get("sort") or [""])[0] or "").lower()
        if selected in SEARCH_SORTS:
            return selected
        return "new" if is_live_search else "relevance"

    def _search_input_for(self, url, search_input=None):
        if not self._is_search_url(url):
            return search_input
        if search_input is not None:
            return search_input

        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        search_input = (query.get("q") or [""])[0]
        if search_input:
            return search_input

        is_live_search = url.startswith(SEARCH_LIVE_URL)
        search_input = self.from_keyboard(
            header="Search Reddit Live Streams" if is_live_search else "Search Reddit Videos"
        )
        if not search_input:
            sys.exit()
        return search_input

    def _api_url_for(self, url, search_input=None):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        after = (query.get("after") or [""])[0]

        if url.startswith(SEARCH_VIDEO_URL) or url.startswith(SEARCH_LIVE_URL):
            is_live_search = url.startswith(SEARCH_LIVE_URL)
            search_query = self._search_input_for(url, search_input)
            search_query = _search_query(search_query, is_live_search)
            params = {
                "q": search_query,
                "sort": self._search_sort_for(url, is_live_search),
                "t": "all",
                "type": "link",
                "limit": "50",
                "raw_json": "1",
            }
            if after:
                params["after"] = after
            return f"{BASE_URL}/search.json?{urlencode(params)}"

        if "/comments/" in parsed.path:
            return url.rstrip("/") + ".json?raw_json=1"

        if url.startswith(SUBREDDIT_URL + "/"):
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) < 2:
                return None
            subreddit = quote(parts[1])
            sort = parts[2] if len(parts) > 2 else "hot"
            if sort not in ("hot", "new", "top", "rising"):
                sort = "hot"
            params = {
                "limit": "50",
                "raw_json": "1",
            }
            if after:
                params["after"] = after
            return f"{BASE_URL}/r/{subreddit}/{sort}.json?{urlencode(params)}"

        return None

    def _rss_url_for(self, url, search_input=None):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        if url.startswith(SEARCH_VIDEO_URL) or url.startswith(SEARCH_LIVE_URL):
            is_live_search = url.startswith(SEARCH_LIVE_URL)
            search_query = self._search_input_for(url, search_input)
            search_query = _search_query(search_query, is_live_search)
            params = {
                "q": search_query,
                "sort": self._search_sort_for(url, is_live_search),
                "type": "link",
                "limit": "50",
            }
            return f"{BASE_URL}/search/.rss?{urlencode(params)}"

        if url.startswith(SUBREDDIT_URL + "/"):
            if "/comments/" in parsed.path:
                return url.rstrip("/") + ".rss"
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) < 2:
                return None
            subreddit = quote(parts[1])
            sort = parts[2] if len(parts) > 2 else ""
            if sort not in ("hot", "new", "top", "rising"):
                sort = ""
            rss_path = f"/r/{subreddit}/{sort}/.rss" if sort else f"/r/{subreddit}/.rss"
            return f"{BASE_URL}{rss_path}?limit=50"

        return None

    def _resolve_reddit_post_media(self, url):
        api_url = self._api_url_for(url)
        if not api_url:
            return None, None
        response = self.session.get(api_url)
        status_code = getattr(response, "status_code", 200)
        text = response.text or ""
        if status_code != 200 or not text.lstrip().startswith(("{", "[")):
            return None, None
        post = _post_from_comments_json(text)
        if not post:
            return None, None
        media = _media_from_post(post)
        return post, media

    def _item_from_post(self, post, media):
        title = _clean_text(post.get("title") or "Untitled Reddit Video")
        permalink = _post_permalink(post)
        stream_url = media["url"]
        if _is_reddit_media_url(stream_url):
            stream_url = _with_kodi_headers(stream_url, self.user_agent, permalink)

        return {
            "type": "item",
            "title": f"[COLOR limegreen]Playable[/COLOR] {title}",
            "link": stream_url,
            "thumbnail": _thumbnail(post),
            "fanart": _thumbnail(post) or FANART,
            "summary": _summary(post, media),
            "is_playable": "true",
            "reddit_stream_type": media["stream_type"],
            "contextmenu": [{
                "label": "Open Reddit Post",
                "action": f"RunPlugin(plugin://plugin.video.thearchives/get_list/{permalink})",
            }],
        }

    def _item_from_rss_entry(self, entry, media):
        permalink = entry.get("permalink") or self.base_url
        stream_url = media["url"]
        if _is_reddit_media_url(stream_url):
            stream_url = _with_kodi_headers(stream_url, self.user_agent, permalink)
        thumbnail = entry.get("thumbnail", "")
        return {
            "type": "item",
            "title": f"[COLOR limegreen]Playable[/COLOR] {entry.get('title') or 'Untitled Reddit Video'}",
            "link": stream_url,
            "thumbnail": thumbnail,
            "fanart": thumbnail or FANART,
            "summary": _rss_summary(entry, media),
            "is_playable": "true",
            "reddit_stream_type": media["stream_type"],
            "contextmenu": [{
                "label": "Open Reddit Post",
                "action": f"RunPlugin(plugin://plugin.video.thearchives/get_list/{permalink})",
            }],
        }

    def _item_from_external_rss_entry(self, entry, external, allow_reddit_post_resolve=False):
        permalink = entry.get("permalink") or self.base_url
        thumbnail = entry.get("thumbnail", "")
        host = external.get("host") or "external"
        external_url = external.get("url", "")
        if allow_reddit_post_resolve and _is_reddit_post_url(external_url):
            return {
                "type": "item",
                "title": f"[COLOR limegreen]Reddit post[/COLOR] {entry.get('title') or 'Untitled Reddit Video'}",
                "link": external_url,
                "thumbnail": thumbnail,
                "fanart": thumbnail or FANART,
                "summary": _rss_external_summary(entry, external),
                "is_playable": "true",
                "reddit_stream_type": "reddit_post",
                "reddit_external_url": external_url,
                "contextmenu": [{
                    "label": "Open Reddit Post",
                    "action": f"RunPlugin(plugin://plugin.video.thearchives/get_list/{permalink})",
                }],
            }
        if _is_ytdlp_supported_external(external_url):
            return {
                "type": "item",
                "title": f"[COLOR deepskyblue]yt-dlp ({host})[/COLOR] {entry.get('title') or 'Untitled Reddit Video'}",
                "link": external_url,
                "thumbnail": thumbnail,
                "fanart": thumbnail or FANART,
                "summary": _rss_external_summary(entry, external),
                "is_playable": "true",
                "reddit_stream_type": "ytdlp",
                "reddit_external_url": external_url,
                "contextmenu": [{
                    "label": "Open Reddit Post",
                    "action": f"RunPlugin(plugin://plugin.video.thearchives/get_list/{permalink})",
                }],
            }
        return {
            "type": "dir",
            "title": f"[COLOR grey]Unsupported external ({host})[/COLOR] {entry.get('title') or 'Untitled Reddit Video'}",
            "link": permalink,
            "thumbnail": thumbnail,
            "fanart": thumbnail or FANART,
            "summary": _rss_external_summary(entry, external),
        }

    def from_keyboard(self, default_text="", header="Search Reddit"):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
