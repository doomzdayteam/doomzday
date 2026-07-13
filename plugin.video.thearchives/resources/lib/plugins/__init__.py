import importlib
import os
import sys
from urllib.parse import unquote_plus, urlsplit


CORE_MODULES = [
    "local",
    "json_parser",
    "xml_parser",
    "xml_convert",
    "default_process_item",
    "display",
    "guidedata",
    "summary",
]

ROUTE_MODULES = {
    "airtable/": ["airtable"],
    "apache directory/directory/": ["apache_dir"],
    "history/": ["history"],
    "microjen_scrapers/play/": ["microjen_scrapers"],
    "nginx dir/": ["nginx_dir"],
    "run_plug/": ["plug"],
    "trakt/": ["trakt", "tmdb_plugin"],
    "punchplay/": ["punchplay"],
    "ytdlp/": ["youtube"],
}

URL_MODULE_RULES = [
    ("password//", ["password"]),
    ("m3u", ["m3u_parser"]),
    ("custom_debrid_lists:", ["custom_debrid_lists"]),
    ("history/", ["history"]),
    ("tmdb", ["tmdb_plugin", "get_meta"]),
    ("trakt", ["trakt", "tmdb_plugin", "get_meta"]),
    ("youtube-live://", ["youtube_live"]),
    ("plugin.video.youtube", ["youtube"]),
    ("youtube.com", ["youtubesearch", "youtube"]),
    ("youtu.be", ["youtube"]),
    ("freelistenonline.com", ["flo"]),
    ("worldradiomap.com", ["worldradiomap"]),
    ("audiophile.fm", ["audiophilefm"]),
    ("archive.org", ["archive_org"]),
    ("reddit.com", ["reddit"]),
    ("documentaryarea.com", ["documentary_area"]),
    ("filmon.com", ["filmon"]),
    ("supercartoons.net", ["supercartoons"]),
    ("footreplays.com", ["footreplays"]),
    ("watchwrestling.ae", ["watchwrestling"]),
    ("rugby24.net", ["rugby24"]),
    ("ok.ru", ["ok_ru"]),
    ("pluto.tv", ["pluto_tv"]),
    ("play.xumo.com", ["xumo_play"]),
    ("therokuchannel.roku.com", ["roku_channel"]),
    ("tubitv.com", ["tubi_tv"]),
    ("comettv.com", ["comet_tv"]),
    ("plex.tv", ["plex_tv"]),
    ("samsungtvplus.com", ["samsung_tv_plus"]),
    ("lgchannels.com", ["lg_channels"]),
    ("publiciptv.com", ["public_iptv"]),
    ("famelack.com", ["famelack_tv"]),
]

PLAYBACK_MODULES = [
    "default_play_video",
    "pre_play",
    "ffmp_player",
    "m_player_archives",
    "microjen_scrapers",
    "youtube",
    "history",
    "audiophilefm",
    "archive_org",
    "comet_tv",
    "documentary_area",
    "famelack_tv",
    "filmon",
    "flo",
    "footreplays",
    "watchwrestling",
    "rugby24",
    "lg_channels",
    "ok_ru",
    "plex_tv",
    "pluto_tv",
    "public_iptv",
    "reddit",
    "roku_channel",
    "samsung_tv_plus",
    "supercartoons",
    "tubi_tv",
    "worldradiomap",
    "xumo_play",
    "youtubesearch",
    "youtube_live",
]

loaded_modules = set()


def _available_modules():
    files = os.listdir(os.path.dirname(__file__))
    return {
        filename[:-3]
        for filename in files
        if not filename.startswith("__") and filename.endswith(".py")
    }


def _current_route():
    if sys.argv:
        route = unquote_plus(urlsplit(str(sys.argv[0] or "")).path or "").strip()
        if route and route != "/":
            return route
    if len(sys.argv) > 2:
        return unquote_plus(str(sys.argv[2] or "")).strip()
    return ""


def _current_get_list_url(route):
    route = route.lstrip("/")
    if route.startswith("get_list/"):
        return route.split("/", 1)[1]
    marker = "/get_list/"
    if marker in route:
        return route.split(marker, 1)[1]
    return ""


def _append_unique(target, names):
    for name in names:
        if name not in target:
            target.append(name)


def _modules_for_url(url):
    url_l = str(url or "").lower()
    selected = []
    for marker, module_names in URL_MODULE_RULES:
        if marker in url_l:
            _append_unique(selected, module_names)
    if url_l.startswith("http"):
        _append_unique(selected, ["http"])
    return selected


def _select_modules(route=None):
    route = _current_route() if route is None else route
    route_l = route.lstrip("/").lower()
    get_list_url = _current_get_list_url(route).lower()
    selected = list(CORE_MODULES)

    if route_l.startswith("play_video/") or "/play_video/" in route_l:
        _append_unique(selected, PLAYBACK_MODULES)

    for route_prefix, module_names in ROUTE_MODULES.items():
        if route_l.startswith(route_prefix):
            _append_unique(selected, module_names)

    if get_list_url:
        _append_unique(selected, _modules_for_url(get_list_url))

    return [name for name in selected if name in _available_modules()]


def _load_modules(module_names):
    available = _available_modules()
    loaded = []
    for module_name in module_names:
        if module_name in loaded_modules or module_name not in available:
            continue
        globals()[module_name] = importlib.import_module(f"{__name__}.{module_name}")
        loaded_modules.add(module_name)
        if module_name not in __all__:
            __all__.append(module_name)
        loaded.append(module_name)
    return loaded


def load_for_hook(function_name, *args):
    selected = []
    if function_name in ("get_list", "parse_list") and args:
        _append_unique(selected, _modules_for_url(args[0]))
    elif function_name == "get_metadata" and args:
        item = args[0] if isinstance(args[0], dict) else {}
        if item.get("content") and (
            item.get("tmdb_id") or item.get("tmdb") or item.get("imdb") or item.get("imdb_id")
        ):
            _append_unique(selected, ["tmdb_plugin", "get_meta"])
    elif function_name in ("play_video", "pre_play"):
        _append_unique(selected, PLAYBACK_MODULES)
    return _load_modules(selected)


__all__ = []
_load_modules(_select_modules())
