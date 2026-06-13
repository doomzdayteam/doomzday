
import xbmc, xbmcaddon, xbmcgui
from ..plugin import Plugin

workspace_api_key = "your airtable api key"
workspace_api_key = "keyikW1exArRfNAWj"

CACHE_TIME = 0

addon_fanart = xbmcaddon.Addon().getAddonInfo('fanart')
addon_icon = xbmcaddon.Addon().getAddonInfo('icon')

class airtable_parser(Plugin):
    name = "airtable parser" 
    priority = 100

    def process_item(self, item):
        if "airtable" in item :
            table_info = item["airtable"]
            thumbnail = item.get("thumbnail", addon_icon)
            fanart = item.get("fanart", addon_fanart)
            list_item = xbmcgui.ListItem(
                item.get("title", item.get("name", "")), offscreen=True
            )
            list_item.setArt({"thumb": thumbnail, "fanart": fanart})
            item["list_item"] = list_item
            item["is_dir"] = True
            
            
            if table_info.startswith("season") or table_info.startswith("show"): item["link"] = "airtable/jen/%s***%s" % (table_info, workspace_api_key)
            else: item["link"] = "airtable/jen/all|%s|%s|all***%s" % (table_info.split('|')[0], table_info.split('|')[-1], workspace_api_key)
                        
            return item





            
