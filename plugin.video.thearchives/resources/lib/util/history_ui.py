import json

from resources.lib.util.history_store import HistoryStore, decode_item, encode_item


_STORE = None


def get_store():
    global _STORE
    if _STORE is None:
        _STORE = HistoryStore()
    return _STORE


def storage_item(item):
    clean = {}
    for key, value in item.items():
        if key in ("contextmenu", "is_dir", "list_item"):
            continue
        try:
            json.dumps(value)
        except TypeError:
            continue
        clean[key] = value
    return clean


def _addon_id():
    try:
        import xbmcaddon

        return xbmcaddon.Addon().getAddonInfo("id")
    except Exception:
        return "plugin.video.thearchives"


def _run_action(action, item):
    return "RunPlugin(plugin://%s/history/%s/%s)" % (_addon_id(), action, encode_item(item))


def decorate_item(item, source_item=None):
    source = storage_item(source_item or item)
    state = get_store().get_state(source)
    context = item.get("contextmenu") or []
    if not isinstance(context, list):
        context = []

    if state["favorite"]:
        context.append({"label": "[B]Remove from Private Favorites[/B]", "action": _run_action("toggle_favorite", source)})
    else:
        context.append({"label": "[B]Add to Private Favorites[/B]", "action": _run_action("toggle_favorite", source)})

    if state["watched"]:
        context.append({"label": "[B]Mark Private Unwatched[/B]", "action": _run_action("mark_unwatched", source)})
    else:
        context.append({"label": "[B]Mark Private Watched[/B]", "action": _run_action("mark_watched", source)})

    if state["resume_point"] > 0:
        context.append({"label": "[B]Clear Private Progress[/B]", "action": _run_action("clear_progress", source)})

    item["contextmenu"] = context
    item["_private_history_state"] = state

    prefix = ""
    if state["favorite"]:
        prefix += "[COLOR gold][B][F][/B][/COLOR] "
    if state["watched"]:
        prefix += "[COLOR lime][B][W][/B][/COLOR] "
    elif state["resume_point"] > 0:
        prefix += "[COLOR khaki][B][%d%%][/B][/COLOR] " % int(round(state["resume_point"]))
    if prefix and not str(item.get("title", "")).startswith("[COLOR"):
        item["title"] = prefix + item.get("title", item.get("name", ""))
    elif prefix:
        item["title"] = prefix + item.get("title", item.get("name", ""))
    return item


def apply_listitem_state(list_item, item):
    state = item.get("_private_history_state") or get_store().get_state(storage_item(item))
    if state["watched"]:
        labels = dict(item.get("infolabels") or {})
        labels["playcount"] = 1
        labels.setdefault("title", item.get("title", item.get("name", "")))
        try:
            from resources.lib.infotagger.helpers import set_video_info
            set_video_info(list_item, labels)
        except Exception:
            pass
    if state["resume_point"] > 0:
        try:
            list_item.setProperty("WatchedProgress", str(int(round(state["resume_point"]))))
            list_item.setProperty("ResumeTime", str(state["curr_time"]))
            list_item.setProperty("TotalTime", str(state["total_time"]))
        except Exception:
            pass


def decode_payload(payload):
    return decode_item(payload)
