import json
import os
import re
import urllib.request
import xbmc
import xbmcaddon
import xbmcvfs

from ..DI import DI
from ..plugin import Plugin


ADDON = xbmcaddon.Addon()
PATH = ADDON.getAddonInfo("path")
SLOT_COUNT = 5
HTTP_HEADERS = {
    "User-Agent": "TheArchives/1.0",
    "Accept": "application/json, application/xml, text/xml, text/plain, */*",
}


def _fetch_http_text(url):
    try:
        response = DI.session.get(url, headers=HTTP_HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except Exception as requests_error:
        try:
            request = urllib.request.Request(url, headers=HTTP_HEADERS)
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.read().decode("utf-8", "replace")
        except Exception as urllib_error:
            xbmc.log(
                f"TheArchives custom personal list HTTP error: requests={requests_error}; urllib={urllib_error}",
                xbmc.LOGERROR,
            )
            return ""


def _setting(setting_id):
    return (ADDON.getSetting(setting_id) or "").strip()


def _setting_bool(setting_id):
    return str(ADDON.getSetting(setting_id) or "").lower() == "true"


def _translate_path(path):
    if path.startswith("special://") and hasattr(xbmcvfs, "translatePath"):
        return xbmcvfs.translatePath(path)
    return path


def _local_file_path(path):
    if path.startswith("file://"):
        path = path.replace("file://", "", 1)
    path = re.sub(r"^/([A-Za-z]:[\\/])", r"\1", path)
    path = _translate_path(path)
    if os.path.isabs(path) or path.startswith("\\\\"):
        return path
    return os.path.join(PATH, "xml", path)


class custom_personal_lists(Plugin):
    name = "custom personal lists"
    priority = 0

    def get_list(self, url):
        if url in ("custom_personal_lists://root", "custom_personal_lists:/root"):
            return json.dumps({"items": self._root_items()})

        if url.startswith(("custom_personal_lists://slot/", "custom_personal_lists:/slot/")):
            slot = url.rsplit("/", 1)[-1]
            return self._slot_payload(slot)

    def _root_items(self):
        items = []
        for slot in range(1, SLOT_COUNT + 1):
            source = self._slot_source(slot)
            if not _setting_bool(f"custom.personal.{slot}.enabled") or not source:
                continue
            title = _setting(f"custom.personal.{slot}.name") or f"Personal List {slot}"
            items.append({
                "type": "dir",
                "title": title,
                "link": f"custom_personal_lists://slot/{slot}",
                "thumbnail": "resources/media/playlists.png",
                "summary": "User supplied XML/JSON personal list for non-debrid plugin routes",
            })
        if items:
            return items
        return [{
            "type": "item",
            "title": "[COLOR grey]No personal lists configured[/COLOR]",
            "link": "message/Enable a personal list in Settings > Personal Lists.",
            "thumbnail": "resources/media/settings.png",
        }]

    def _slot_payload(self, slot):
        try:
            slot_number = int(slot)
        except (TypeError, ValueError):
            return json.dumps({"items": []})
        if slot_number < 1 or slot_number > SLOT_COUNT:
            return json.dumps({"items": []})
        if not _setting_bool(f"custom.personal.{slot_number}.enabled"):
            return json.dumps({"items": []})

        source = self._slot_source(slot_number)
        if not source:
            return json.dumps({"items": []})

        if source.lower().startswith(("http://", "https://")):
            return _fetch_http_text(source) or json.dumps({"items": []})

        try:
            input_file = xbmcvfs.File(_local_file_path(source))
            return input_file.read()
        except Exception as error:
            xbmc.log(f"TheArchives custom personal list file error: {error}", xbmc.LOGERROR)
            return json.dumps({"items": []})

    def _slot_source(self, slot):
        return _setting(f"custom.personal.{slot}.url") or _setting(f"custom.personal.{slot}.file")
