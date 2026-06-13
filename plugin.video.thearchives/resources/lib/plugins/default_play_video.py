from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info
import xbmc, xbmcgui, xbmcaddon
import json

addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')


class default_play_video(Plugin):
    name = "default video playback"
    priority = 0

    def _is_debrid_item(self, item):
        return bool(
            item.get("debrid_cached")
            or item.get("debrid_uncached")
            or item.get("debrid_service")
            or item.get("cached_service_id")
        )

    def _is_easynews_item(self, item):
        values = (
            item.get("provider"),
            item.get("origin"),
            item.get("source"),
            item.get("debrid_service"),
        )
        return any("easynews" in str(value or "").lower() for value in values)

    def _uses_history(self, item):
        return self._is_debrid_item(item) or self._is_easynews_item(item)
    
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
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass
        if self._uses_history(item):
            try:
                from resources.lib.plugins.history import HistoryPlayer
                return HistoryPlayer(item).play(link, liz)
            except Exception as e:
                xbmc.log(f"[TheArchives] HistoryPlayer error: {e}", xbmc.LOGERROR)
        return xbmc.Player().play(link, liz)
