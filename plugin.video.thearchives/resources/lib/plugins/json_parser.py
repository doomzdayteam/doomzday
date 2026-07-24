import json
import xbmc
import xbmcaddon
from ..plugin import Plugin


MAIN_MENU_SETTINGS = {
    "trakt": "menu.show.trakt",
    "mdblist": "menu.show.mdblist",
    "simkl": "menu.show.simkl",
    "punchplay": "menu.show.punchplay",
    "tmdb": "menu.show.tmdb",
    "custom debrid lists": "menu.show.custom_debrid_lists",
    "personal lists": "menu.show.personal_lists",
}

MAIN_MENU_LINK_SETTINGS = {
    "file://trakt.json": "menu.show.trakt",
    "file://mdblist.json": "menu.show.mdblist",
    "file://simkl.json": "menu.show.simkl",
    "file://punchplay.json": "menu.show.punchplay",
    "file://tmdb.json": "menu.show.tmdb",
    "custom_debrid_lists://root": "menu.show.custom_debrid_lists",
    "custom_personal_lists://root": "menu.show.personal_lists",
}


def _setting_enabled(setting_id):
    value = xbmcaddon.Addon().getSetting(setting_id)
    if value == "":
        return True
    return str(value).lower() != "false"


def _static_enabled(item):
    return str(item.get("enabled", "true")).lower() != "false"


def _is_main_menu_url(url):
    clean_url = str(url or "").replace("\\", "/").split("?", 1)[0].lower().rstrip("/")
    return clean_url == "file://main.json" or clean_url.endswith("/main.json")


def _main_menu_setting(item):
    title = str(item.get("title") or item.get("name") or "").strip().lower()
    link = str(item.get("link") or "").strip().lower()
    return MAIN_MENU_SETTINGS.get(title) or MAIN_MENU_LINK_SETTINGS.get(link)


def _menu_item_visible(item, is_main_menu):
    if not _static_enabled(item):
        return False
    if not is_main_menu:
        return True
    setting_id = _main_menu_setting(item)
    return True if not setting_id else _setting_enabled(setting_id)


class json_parser(Plugin):
    name = "json_parser"
    description = "add json format support"
    priority = 0

    def parse_list(self, url: str, response):
        if isinstance(response, bytes):
            response = response.decode("utf-8-sig")
        else:
            response = response.lstrip("\ufeff")
        stripped = response.lstrip()
        if url.endswith(".json") or (stripped.startswith("{") and '"items"' in stripped):
            try:
                items = json.loads(response)["items"]
                is_main_menu = _is_main_menu_url(url)
                return [i for i in items if _menu_item_visible(i, is_main_menu)]
            except json.decoder.JSONDecodeError:
                xbmc.log(f"invalid json: {response}", xbmc.LOGINFO)
