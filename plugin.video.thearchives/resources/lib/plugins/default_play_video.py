from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info
import xbmc, xbmcgui, xbmcaddon
import json

addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')


class default_play_video(Plugin):
    name = "default video playback"
    priority = 0
    
    def play_video(self, item):
        item = json.loads(item)
        link = item.get("link", "")
        if link == "":
            return False
        title = item["title"]
        thumbnail = item.get("thumbnail", default_icon)
        summary = item.get("summary", "")
        liz = xbmcgui.ListItem(title)
        if item.get("infolabels"):
            set_video_info(liz, item["infolabels"])
        else:
            set_video_info(liz, {"title": title, "plot": summary})
        liz.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail})
        return self._play_with_history(link, liz, item)

    def _play_with_history(self, url, liz, item):
        try:
            from resources.lib.plugins.history import HistoryPlayer

            return HistoryPlayer(item).play(url, liz)
        except Exception as e:
            xbmc.log(f"[TheArchives] HistoryPlayer error: {e}", xbmc.LOGERROR)
            import traceback
            xbmc.log(f"[TheArchives] HistoryPlayer traceback: {traceback.format_exc()}", xbmc.LOGERROR)
            return xbmc.Player().play(url, liz)
