import base64
from datetime import date
import json


def _log_info(message):
    try:
        import xbmc

        xbmc.log("[TheArchives] %s" % message, xbmc.LOGINFO)
    except Exception:
        pass


def setting_enabled(setting_id):
    try:
        import xbmcaddon

        return str(xbmcaddon.Addon().getSetting(setting_id) or "").lower() == "true"
    except Exception:
        return False


def should_autoplay_source(item):
    item = item or {}
    if item.get("_debrid_autoplay_once"):
        _log_info("Source autoplay content=%s enabled=true forced=true" % str(item.get("content") or "").lower())
        return True
    content = str(item.get("content") or "").lower()
    if content == "movie":
        enabled = setting_enabled("debrid.autoplay.movies")
    elif content == "episode":
        enabled = setting_enabled("debrid.autoplay.episodes")
    else:
        enabled = False
    _log_info("Source autoplay content=%s enabled=%s" % (content or "unknown", str(enabled).lower()))
    return enabled


def _is_aired(episode, today):
    value = episode.get("air_date")
    if not value:
        return False
    try:
        return date.fromisoformat(str(value)) <= today
    except (TypeError, ValueError):
        return False


def next_episode_item(item, api=None, today=None):
    item = dict(item or {})
    if str(item.get("content") or "").lower() != "episode":
        return None
    try:
        current_season = int(item.get("season") or 0)
        current_episode = int(item.get("episode") or 0)
    except (TypeError, ValueError):
        return None
    if current_season <= 0 or current_episode <= 0:
        return None

    if api is None:
        from resources.lib.plugins.tmdb_plugin import tmdb_api

        api = tmdb_api
    show_id = item.get("tv_show_tmdb_id")
    if not show_id:
        imdb_id = item.get("imdb_id") or item.get("imdb")
        show_id = api.tmdb_from_imdb(imdb_id) if imdb_id else None
    if not show_id:
        return None

    show = api.get("tv/%s" % show_id, paginated=False) or {}
    try:
        last_season = int(show.get("number_of_seasons") or current_season)
    except (TypeError, ValueError):
        last_season = current_season
    today = today or date.today()

    for season_number in range(current_season, last_season + 1):
        if season_number <= 0:
            continue
        season_data = api.get("tv/%s/season/%s" % (show_id, season_number), paginated=False) or {}
        episodes = sorted(
            season_data.get("episodes") or [],
            key=lambda value: int(value.get("episode_number") or 0),
        )
        for candidate in episodes:
            episode_number = int(candidate.get("episode_number") or 0)
            if season_number == current_season and episode_number <= current_episode:
                continue
            if not _is_aired(candidate, today):
                continue
            still_path = candidate.get("still_path")
            artwork = None
            if still_path:
                artwork = "%s/%s" % (str(api.image_url).rstrip("/"), str(still_path).lstrip("/"))
            first_air_date = str(show.get("first_air_date") or "")
            year = item.get("year") or (first_air_date.split("-", 1)[0] if first_air_date else 0)
            return {
                "content": "episode",
                "type": "item",
                "title": "%s. %s" % (episode_number, candidate.get("name") or "Episode %s" % episode_number),
                "link": "search",
                "thumbnail": artwork,
                "fanart": artwork,
                "summary": candidate.get("overview") or "",
                "tmdb_id": candidate.get("id"),
                "tv_show_tmdb_id": show_id,
                "imdb_id": item.get("imdb_id") or item.get("imdb"),
                "tv_show_title": item.get("tv_show_title") or item.get("showtitle") or "",
                "year": year,
                "season": season_number,
                "episode": episode_number,
                "premiered": candidate.get("air_date") or "",
                "_debrid_autoplay_once": True,
            }
    return None


def launch_next_episode(item):
    if not setting_enabled("debrid.autoplay.next_episode"):
        _log_info("Next episode autoplay enabled=false")
        return False
    try:
        next_item = next_episode_item(item)
        if not next_item:
            _log_info("Next episode autoplay outcome=no-next-item")
            return False
        import xbmc
        import xbmcaddon

        payload = base64.urlsafe_b64encode(json.dumps(next_item).encode("utf-8")).decode("ascii")
        addon_id = xbmcaddon.Addon().getAddonInfo("id") or "plugin.video.thearchives"
        xbmc.executebuiltin("RunPlugin(plugin://%s/play_video/%s)" % (addon_id, payload))
        _log_info(
            "Next episode autoplay outcome=launched season=%s episode=%s" %
            (next_item.get("season"), next_item.get("episode"))
        )
        return True
    except Exception as exc:
        try:
            import xbmc

            xbmc.log("[TheArchives] Next debrid episode error: %s" % exc, xbmc.LOGERROR)
        except Exception:
            pass
        return False
