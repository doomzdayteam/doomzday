from ..plugin import Plugin
import xbmc, xbmcgui, xbmcaddon
import json
import resolveurl

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
            liz.setInfo("video", item["infolabels"])
        else:
            liz.setInfo("video", {"title": title, "plot": summary})
        liz.setArt({"thumb": thumbnail, "icon": thumbnail, "poster": thumbnail})
        if resolveurl.HostedMediaFile(link).valid_url():
            url = resolveurl.HostedMediaFile(link).resolve()
            return xbmc.Player().play(url,liz)
        return xbmc.Player().play(link,liz)