import xbmc
import xbmcaddon
import xbmcgui
import json
from ..plugin import Plugin
from .tmdb_plugin import tmdb_api, TMDB
from ..DI import DI
from resources.lib.infotagger.helpers import set_video_info, set_video_cast


class Meta(Plugin):
    name = "meta"
    description = "Process Item Metadata"
    priority = 201

    def get_metadata(self, item):
        liz = item.get("list_item")
        if liz is None:
            liz = xbmcgui.ListItem(item.get("title", "Unknown Title"))
        # Collect all context menu entries to apply at the end
        all_context = []
        if "contextmenu" in item:
            contextmenu = item.get("contextmenu")
            for c in contextmenu:
                all_context.append((c.get("label", ""), c.get("action", "")))
        if "summary" in item:
            summary = item["summary"]
            set_video_info(item["list_item"],
                {"plot": summary, "plotoutline": summary}
            )
        if xbmcaddon.Addon().getSettingBool("full_meta"):
            if "infolabels" in item:
                set_video_info(liz, item["infolabels"])
                set_video_cast(liz, item.get("cast", ""))
        else:
            xbmcaddon.Addon().setSetting("item_meta", "false")
        if not xbmcaddon.Addon().getSettingBool("item_meta"):
            # Re-apply context menu to ensure it sticks after any setInfo calls
            if all_context:
                liz.addContextMenuItems(all_context)
            return item
        content = item.get("content")
        if content is None:
            if all_context:
                liz.addContextMenuItems(all_context)
            return item
        if content == "tvshow":
            content = "tv"
        if "tmdb_id" in item:
            _id = item["tmdb_id"]
        elif "tmdb" in item:
            _id = item["tmdb"]
        elif "imdb" in item:
            _id = tmdb_api.tmdb_from_imdb(item["imdb"])
        elif "imdb_id" in item:
            _id = tmdb_api.tmdb_from_imdb(item["imdb_id"])
            if _id is None:
                if all_context:
                    liz.addContextMenuItems(all_context)
                return item

        try:
            from_cache = False
            new_item = None
            tmdb = TMDB()
            url = f"tmdb/{content}/{_id}"
            if (
                xbmcaddon.Addon().getSettingBool("use_cache")
                and not "tmdb/search" in url
            ):
                new_item = DI.db.get(url)
                if new_item:
                    new_item = json.loads(new_item[0])
                    from_cache = True
            if from_cache is False:
                new_item = json.loads(tmdb.get_list(url))
            if new_item is None:
                if all_context:
                    liz.addContextMenuItems(all_context)
                return item
            link = item.get("link")
            if link and from_cache is False:
                link = self.process_links(link.replace("play_video/", ""))
            thumbnail = new_item.get("thumbnail")
            liz.setArt(
                {
                    "icon": thumbnail,
                    "thumb": thumbnail,
                    "poster": thumbnail,
                    "fanart": new_item.get("fanart"),
                }
            )
            set_video_info(liz, new_item["infolabels"])
            set_video_cast(liz, new_item.get("cast", ""))
            new_item["link"] = f"play_video/{link}"
            new_item["is_dir"] = item["is_dir"]
            if (
                xbmcaddon.Addon().getSettingBool("use_cache")
                and not "tmdb/search" in url
            ):
                DI.db.set(url, json.dumps(new_item))
            # Carry over private history data from original item
            if item.get("contextmenu"):
                new_item["contextmenu"] = item["contextmenu"]
            if item.get("_private_history_state"):
                new_item["_private_history_state"] = item["_private_history_state"]
            new_item["list_item"] = liz
            # Apply private history watched/progress state to new ListItem
            if new_item.get("_private_history_state"):
                try:
                    from resources.lib.util import history_ui
                    history_ui.apply_listitem_state(liz, new_item)
                except Exception:
                    pass
            # Re-apply all context menu items to the ListItem after all setInfo calls
            if all_context:
                liz.addContextMenuItems(all_context)
            return new_item

        except Exception as e:
            xbmc.log(f"Error Processing Meta: {e}", xbmc.LOGINFO)
            if all_context:
                liz.addContextMenuItems(all_context)
            return item

    def process_links(self, link):
        import base64

        link_decoded = json.loads(base64.urlsafe_b64decode(link))
        item_link = link_decoded.get("link")
        if type(item_link) == list:
            if "search" not in item_link:
                item_link.append("search(Search Using The Archives Scrapers)")
        elif item_link and item_link != "search":
            item_link = [item_link, "search(Search Using The Archives Scrapers)"]
        elif item_link is None:
            item_link = "search"
        link_decoded["link"] = item_link
        return base64.urlsafe_b64encode(
            bytes(json.dumps(link_decoded), "utf-8")
        ).decode("utf-8")
