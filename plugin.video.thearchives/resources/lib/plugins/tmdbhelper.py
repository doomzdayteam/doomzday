import json

import xbmc

from ..plugin import Plugin


class tmdbhelper(Plugin):
    name = "play with tmdbhelper"
    priority = 100

    def play_video(self, item):
        item = json.loads(item)
        tmdb_id = item.get("tmdb_id")
        if tmdb_id:
            content = item.get("content")
            if content == "movie":
                xbmc.executebuiltin(
                    f"RunPlugin(plugin://plugin.video.themoviedb.helper?info=play&amp;tmdb_id={tmdb_id}&amp;type=movie)"
                )
                return True
            elif content == "episode":
                episode = item.get("episode")
                season = item.get("season")
                if episode and season:
                    xbmc.executebuiltin(
                        f"RunPlugin(plugin://plugin.video.themoviedb.helper?info=play&amp;tmdb_id={tmdb_id}&amp;type=episode&amp;season={season}&amp;episode={episode})"
                    )
                    return True
