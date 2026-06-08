from ..plugin import Plugin
from xbmcplugin import addDirectoryItems, endOfDirectory, setContent, setPluginCategory
from ..DI import DI
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
import re
import sys

route_plugin = DI.plugin

KODI_FORMAT_RE = re.compile(r"\[/?(?:B|I|COLOR[^\]]*)\]", re.IGNORECASE)


def clean_label(label):
    return KODI_FORMAT_RE.sub("", str(label or "")).strip()


def current_folder_label():
    if len(sys.argv) < 3:
        return ""
    query = urlsplit(sys.argv[2]).query or str(sys.argv[2]).lstrip("?")
    values = parse_qs(query, keep_blank_values=True).get("folder_label", [])
    return clean_label(values[0]) if values else ""


def add_folder_label(url, label):
    label = clean_label(label)
    if not label:
        return url
    parsed = urlsplit(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["folder_label"] = [label]
    return urlunsplit(parsed._replace(query=urlencode(query, doseq=True)))


def infer_content_category(jen_list):
    content = {str(item.get("content", "")).lower() for item in jen_list if item.get("content")}
    if "episode" in content:
        return "episodes"
    if content & {"tv", "tvshow", "season"}:
        return "tvshows"
    if content & {"movie", "movies"}:
        return "movies"
    if content == {"video"}:
        return "videos"
    return "videos"


class display(Plugin):
    name = "display"

    def display_list(self, jen_list):
        display_list = []
        for item in jen_list:
            item_url = route_plugin.url_for_path(item["link"])
            if item.get("is_dir"):
                item_url = add_folder_label(item_url, item.get("title") or item["list_item"].getLabel())
            display_list.append((item_url, item["list_item"], item["is_dir"]))
        addDirectoryItems(route_plugin.handle, display_list, len(display_list))
        category = infer_content_category(jen_list)
        folder_label = current_folder_label()
        if folder_label:
            setPluginCategory(route_plugin.handle, folder_label)
        setContent(int(sys.argv[1]),  category) 
        endOfDirectory(route_plugin.handle)
        return True
