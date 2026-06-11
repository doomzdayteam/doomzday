from resources.lib.plugins.summary import Summary
from ..plugin import Plugin
import xbmcgui
import base64
import json

import urllib.parse
try:
    from resources.lib.util.common import *
    from resources.lib.util import history_ui
except ImportError:
    from .resources.lib.util.common import *
    history_ui = None

import xbmcaddon
addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')
default_fanart = xbmcaddon.Addon(addon_id).getAddonInfo('fanart')


def _tracks_private_history_dir(item):
    content = str(item.get("content", "")).lower()
    if content in ("tv", "tvshow", "season", "episode", "movie", "video"):
        return True

    link = str(item.get("link", "")).lower()
    return link.startswith(("tmdb/tv/", "trakt/seasons/", "trakt/season/"))


def _browse_media_context(item):
    content = str(item.get("content", "")).lower()
    tmdb_id = item.get("tmdb_id") or item.get("tmdb")
    media_type = None
    if content == "movie":
        media_type = "movie"
    elif content in ("tv", "tvshow"):
        media_type = "tv"
    elif content == "season":
        media_type = "tv"
        link = str(item.get("link", ""))
        parts = link.split("/")
        if len(parts) >= 3 and parts[0] == "tmdb" and parts[1] == "tv":
            tmdb_id = parts[2]

    if not media_type or not tmdb_id:
        return []

    base = f"plugin://{addon_id}/get_list/tmdb/{media_type}/{tmdb_id}"
    cast_base = f"plugin://{addon_id}/get_list/tmdb/cast/{media_type}/{tmdb_id}"
    return [
        {"label": "Browse Recommended", "action": f"Container.Update({base}/recommendations)"},
        {"label": "Browse Related", "action": f"Container.Update({base}/similar)"},
        {"label": "Browse More Like This", "action": f"Container.Update({base}/similar)"},
        {"label": "Browse Cast", "action": f"Container.Update({cast_base})"},
    ]


def _append_contextmenu(item, entries):
    if not entries:
        return
    contextmenu = item.get("contextmenu") or []
    if not isinstance(contextmenu, list):
        contextmenu = []
    existing_labels = {entry.get("label") for entry in contextmenu if isinstance(entry, dict)}
    for entry in entries:
        if entry.get("label") not in existing_labels:
            contextmenu.append(entry)
            existing_labels.add(entry.get("label"))
    item["contextmenu"] = contextmenu
    
class default_process_item(Plugin):
    name = "default process item"
    priority = 0

    def process_item(self, item):
        do_log(f'{self.name} - Item = \n {str(item)} ' )  
        is_dir = False
        tag = item["type"]
        link = item.get("link", "")
        track_private = False
        include_watch_actions = False
        private_source_item = None
        summary = item.get("summary")
        context = item.get("contextmenu")
        if context:
            del item["contextmenu"]
        if link:
            if tag == "dir":
                if link.endswith('.xml'):
                    link = link+'l'
                if link.endswith(".m3u") or link.endswith(".m3u8"):
                    link = f"m3u|{link}"
                link = f"/get_list/{link}"
                is_dir = True
                
            if tag == "plugin":   
                plug_item = urllib.parse.quote_plus(str(link))  
                if 'youtube' in plug_item:
                    link = f"/get_list/{link}"
                    is_dir = True
                else :
                    link = f"/run_plug/{plug_item}"                 
                    is_dir = False
            if tag == "script":
                script_item = urllib.parse.quote_plus(str(link))
                link = f"/run_script/{script_item}"
                is_dir = False 
        if tag == "item":
            playback_item = dict(item)
            if history_ui:
                playback_item = history_ui.storage_item(playback_item)
            link_item = base64.urlsafe_b64encode(bytes(json.dumps(playback_item), 'utf-8')).decode("utf-8")
            
            if str(link).lower() == 'settings' :
                link = "settings" 
            
            elif str(link).lower() == "clear_cache":
                link = "clear_cache"

            elif str(link).lower() == "inputstream_helper":
                link = "inputstream_helper"
                
            elif str(link).lower().startswith("message/") :   
                link = f"show_message/{link}"
                               
            else :     
                link = f"play_video/{link_item}"
                track_private = True
                include_watch_actions = True
                private_source_item = playback_item
        elif tag == "dir":
            track_private = True
            include_watch_actions = _tracks_private_history_dir(item)
            private_source_item = dict(item)
        elif tag in ("plugin", "script"):
            track_private = True
            private_source_item = dict(item)
        if history_ui and track_private:
            try:
                item = history_ui.decorate_item(item, private_source_item, include_watch_actions=include_watch_actions)
            except Exception as e:
                do_log(f'{self.name} - decorate_item error: {e}')
        _append_contextmenu(item, _browse_media_context(item))
                        
                        
        thumbnail = resolve_addon_art_path(item.get("thumbnail", default_icon))
        icon = resolve_addon_art_path(item.get("icon", thumbnail))
        poster = resolve_addon_art_path(item.get("poster", thumbnail))
        fanart = resolve_addon_art_path(item.get("fanart", default_fanart))
        landscape = resolve_addon_art_path(item.get("landscape", fanart))
        banner = resolve_addon_art_path(item.get("banner", landscape))
        clearlogo = resolve_addon_art_path(item.get("clearlogo", icon))
        list_item = xbmcgui.ListItem(
            item.get("title", item.get("name", "")), offscreen=True
        )
        list_item.setArt({
            "thumb": thumbnail,
            "icon": icon,
            "poster": poster,
            "fanart": fanart,
            "landscape": landscape,
            "banner": banner,
            "clearlogo": clearlogo,
        })
        item["list_item"] = list_item
        item["link"] = link
        item["is_dir"] = is_dir
        if history_ui and tag == "item" and item.get("_private_history_state"):
            history_ui.apply_listitem_state(list_item, item)
        if summary:
            item["summary"] = summary
        
        if context:
            existing = item.get("contextmenu") or []
            item["contextmenu"] = existing + context
        
        if item.get("contextmenu"):
            try:
                menu = []
                for c in item["contextmenu"]:
                    menu.append((c.get("label", ""), c.get("action", "")))
                if menu:
                    list_item.addContextMenuItems(menu)
            except Exception as e:
                do_log(f'{self.name} - context menu error: {e}')
       
        return item
