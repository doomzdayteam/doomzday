import xbmc
import xbmcaddon
import json
import time
from ..DI import DI
from ..plugin import Plugin

class cached_list(Plugin):
    name = "Cached List"
    priority = 1000

    def get_list(self, url):
        if not xbmcaddon.Addon().getSettingBool("use_cache"):
            return
        cache_timer =  float(xbmcaddon.Addon().getSetting("time_cache") or 0)
        cached = DI.db.get(url)
        if not cached:
            return
        response, created = cached
        
        try:
            if (created + json.loads(response).get("cache_time", cache_timer)*60) < time.time():
                return
        except json.decoder.JSONDecodeError as e:
            xbmc.log(f'Json Error: {e}', xbmc.LOGINFO)
            if (created + cache_timer*60) < time.time():
                return 
        return response
