from resources.lib.plugins.summary import Summary
from ..plugin import Plugin
import xbmcgui
import base64
import json

import urllib.parse
try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *

import xbmcaddon
addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')
default_fanart = xbmcaddon.Addon(addon_id).getAddonInfo('fanart')
    
class default_process_item(Plugin):
    name = "default process item"
    priority = 0

    def process_item(self, item):
        do_log(f'{self.name} - Item = \n {str(item)} ' )  
        is_dir = False
        tag = item["type"]
        link = item.get("link", "")
        summary = item.get("summary")
        context = item.get("contextmenu")
        if summary:
            del item["summary"]
        if context:
            del item["contextmenu"]
        if link:
            if tag == "dir":
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
            link_item = base64.urlsafe_b64encode(bytes(json.dumps(item), 'utf-8')).decode("utf-8")
            
            if str(link).lower() == 'settings' :
                link = f"settings/{link}"        
            
            elif str(link).lower().startswith("message/") :   
                link = f"show_message/{link}" 
                               
            else :     
                link = f"play_video/{link_item}"
                        
        # thumbnail = item.get("thumbnail", "")
        # fanart = item.get("fanart", "")
                        
        thumbnail = item.get("thumbnail", default_icon)
        fanart = item.get("fanart", default_fanart)
        list_item = xbmcgui.ListItem(
            item.get("title", item.get("name", "")), offscreen=True
        )
        list_item.setArt({"thumb": thumbnail, "fanart": fanart})
        item["list_item"] = list_item
        item["link"] = link
        item["is_dir"] = is_dir
        if summary:
            item["summary"] = summary
        if context:
            item["contextmenu"] = context
        return item
