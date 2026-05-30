import json

from ..plugin import Plugin
from resources.lib.util.history_ui import decode_payload, get_store, storage_item


def _message_item(title, summary):
    return {
        "type": "plugin",
        "title": title,
        "summary": summary,
    }


class History(Plugin):
    name = "private history"
    priority = 250

    def get_list(self, url):
        if not url.startswith("history/"):
            return False

        kind = url.split("/", 1)[1]
        kind_map = {
            "favorites": ("favorite", "[COLOR gold][B]No Private Favorites Yet[/B][/COLOR]"),
            "in_progress": ("progress", "[COLOR khaki][B]No Private Progress Yet[/B][/COLOR]"),
            "watched": ("watched", "[COLOR lime][B]No Private Watched History Yet[/B][/COLOR]"),
        }
        if kind not in kind_map:
            return False

        store_kind, empty_title = kind_map[kind]
        items = get_store().list_items(store_kind)
        if not items:
            items = [_message_item(empty_title, "Items will appear here after you use the private history and favorites actions.")]
        return json.dumps({"items": items})

    def routes(self, plugin):
        @plugin.route("/history/toggle_favorite/<path:payload>")
        def toggle_favorite(payload):
            item = decode_payload(payload)
            enabled = get_store().toggle_favorite(item)
            _notify("Private Favorites", "Added" if enabled else "Removed")
            _refresh()

        @plugin.route("/history/mark_watched/<path:payload>")
        def mark_watched(payload):
            item = decode_payload(payload)
            get_store().mark_watched(item)
            _notify("Private History", "Marked watched")
            _refresh()

        @plugin.route("/history/mark_unwatched/<path:payload>")
        def mark_unwatched(payload):
            item = decode_payload(payload)
            get_store().mark_unwatched(item)
            _notify("Private History", "Marked unwatched")
            _refresh()

        @plugin.route("/history/clear_progress/<path:payload>")
        def clear_progress(payload):
            item = decode_payload(payload)
            get_store().clear_progress(item)
            _notify("Private Progress", "Cleared")
            _refresh()


class HistoryPlayer:
    def __init__(self, item):
        import xbmc

        class _Player(xbmc.Player):
            pass

        self.player = _Player()
        self.item = storage_item(item)
        self.store = get_store()

    def play(self, url, list_item):
        state = self.store.get_state(self.item)
        if state["resume_point"] > 0:
            try:
                list_item.setProperty("StartPercent", str(state["resume_point"]))
            except Exception:
                pass
        self.player.play(url, list_item)
        self._monitor()
        return True

    def _monitor(self):
        try:
            import xbmc

            xbmc.log("[TheArchives] HistoryPlayer._monitor started", xbmc.LOGINFO)
            waited = 0
            while waited < 30000 and not self.player.isPlaying():
                xbmc.sleep(250)
                waited += 250

            if not self.player.isPlaying():
                xbmc.log("[TheArchives] HistoryPlayer._monitor: playback never started", xbmc.LOGINFO)
                return

            xbmc.log("[TheArchives] HistoryPlayer._monitor: playback detected, monitoring", xbmc.LOGINFO)
            last_time = 0.0
            total_time = 0.0
            best_percent = 0.0
            while self.player.isPlaying():
                xbmc.sleep(1000)
                try:
                    total_time = float(self.player.getTotalTime())
                    last_time = float(self.player.getTime())
                except Exception:
                    continue
                if total_time <= 0:
                    continue
                best_percent = max(best_percent, round((last_time / total_time) * 100.0, 1))

            xbmc.log(f"[TheArchives] HistoryPlayer._monitor: playback ended, best_percent={best_percent}, total_time={total_time}, last_time={last_time}", xbmc.LOGINFO)
            if total_time <= 0:
                return
            if best_percent >= 90.0:
                self.store.mark_watched(self.item)
                xbmc.log("[TheArchives] HistoryPlayer._monitor: marked as watched", xbmc.LOGINFO)
            else:
                self.store.set_progress(self.item, last_time, total_time)
                xbmc.log(f"[TheArchives] HistoryPlayer._monitor: saved progress {best_percent}%", xbmc.LOGINFO)
        except Exception as e:
            try:
                import xbmc as _xbmc
                _xbmc.log(f"[TheArchives] HistoryPlayer._monitor error: {e}", _xbmc.LOGERROR)
            except Exception:
                pass
            return


def _notify(heading, message):
    try:
        import xbmcaddon
        import xbmcgui

        addon = xbmcaddon.Addon()
        xbmcgui.Dialog().notification(heading, message, addon.getAddonInfo("icon"), 2500, sound=False)
    except Exception:
        pass


def _refresh():
    try:
        import xbmc

        xbmc.executebuiltin("Container.Refresh")
    except Exception:
        pass
