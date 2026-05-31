from resources.lib.plugins.tmdb_plugin import TMDB_API
from ..DI import DI
from ..plugin import Plugin
import json, time, requests
try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *

class Trakt(Plugin):
    name = "trakt"
    def get_list(self, url):
        if url.startswith("trakt"):
            page_split = url.split("|")
            page = int(page_split[1]) if len(page_split) > 1 else 1
            api = Trakt_API()
            split = page_split[0].split("/")
            if split[1] == "list":
                list = api.get_list(split[2], page=page)
                return api.handle_list(list, page_link=page_split[0] + "|" + str(page + 1))
            if split[1] == "lists" and len(split) > 2 and split[2] == "search":
                query = xbmcgui.Dialog().input("Search Trakt Lists")
                if not query:
                    return json.dumps({"items": []})
                lists = api.search_lists(query, page=page)
                return json.dumps({"items": api.handle_lists_xml(lists, list_type="search")})
            if split[1] == "movies":
                movies = api.get_movies_chart(split[2], page=page)
                return api.handle_list(movies, page_link=page_split[0] + "|" + str(page + 1))
            elif split[1] == "shows":
                shows = api.get_shows_chart(split[2], page=page)
                return api.handle_list(shows, page_link=page_split[0] + "|" + str(page + 1))
            elif split[1] == "seasons":
                seasons = api.get_show(split[2].split("::")[0])
                return json.dumps({"items": api.handle_season_xml(seasons, split[2])})
            elif split[1] == "season":
                season = api.get_season(split[2].split("::")[0], split[3])
                return json.dumps({"items": api.handle_episodes_xml(split[2], season)})
            
            elif split[1] == "user":
                if split[2] == "self":
                    if not self.__check_auth():
                        return
                    user_id = ownAddon.getSetting("trakt.user_id")
                else:
                    user_id = split[2]
                if split[3] == "collection":
                    collection = api.get_collection(user_id, split[4])
                    return api.handle_list(collection, page_link=page_split[0] + "|" + str(page + 1))
                elif split[3] == "lists":
                    lists = api.get_lists(user_id)
                    return json.dumps({"items": api.handle_lists_xml(lists, list_type="my_lists")})
                elif split[3] == "liked_lists":
                    lists = api.get_liked_lists(page=page)
                    return json.dumps({"items": api.handle_lists_xml(lists, list_type="liked_lists")})
                elif split[3] == "list":
                    list = api.get_user_list(user_id, split[4], page=page)
                    return api.handle_list(list, page_link=page_split[0] + "|" + str(page + 1))
                elif split[3] == "watched":
                    watched = api.get_watched(user_id, split[4])
                    return api.handle_list(watched, pagination=False)
                elif split[3] == "watchlist":
                    watched = api.get_watchlist(user_id, split[4] if len(split) > 4 else "", page=page)
                    return api.handle_list(watched, pagination=False)
            elif split[1] == "recommendations":
                if self.__check_auth():
                    recommendations = api.get_recommendations(split[2], 25)
                    return api.handle_list(recommendations, page_link=page_split[0] + "|" + str(page + 1))
    
    def __check_auth(self):
        if ownAddon.getSetting("trakt.user_id") == "":
            if xbmcgui.Dialog().yesno("Trakt Authorization", "This action requires a Trakt account.\n\nWould you like to authorize a Trakt account?"):
                return self.__auth()
        else:
            return True

    def _clear_auth_settings(self):
        xbmcaddon.Addon().setSetting("trakt.access_token", "")
        xbmcaddon.Addon().setSetting("trakt.refresh_token", "")
        xbmcaddon.Addon().setSetting("trakt.user_id", "")
        xbmcaddon.Addon().setSetting("trakt.expires", "0")

    def __auth(self):
        api = Trakt_API()
        if not api.client_id or not api.client_secret:
            xbmcgui.Dialog().ok("Trakt Authorization", "The addon is missing its Trakt API credentials.\nPlease add the addon Client ID and Client Secret before authorizing a Trakt account.")
            return False
        try:
            device_code = api.device_code()
        except Exception as e:
            xbmc.log(str(e), xbmc.LOGERROR)
            self._clear_auth_settings()
            xbmcgui.Dialog().ok("Trakt Authorization Failed", str(e))
            return False
        progress_dialog = xbmcgui.DialogProgress()
        progress_dialog.create(
            "Trakt Authorization",
            f"Go to {device_code['verification_url']} in a browser and enter the following code:\n\n{device_code['user_code']}"
        )
        i = 0
        success = False
        while i < device_code["expires_in"]:
            if progress_dialog.iscanceled():
                break
            try:
                time.sleep(device_code["interval"])
                token_response = api.device_token(device_code["device_code"])
                if token_response.status_code == 200:
                    token = api._json_or_error(token_response, "reading the Trakt access token")
                    xbmcaddon.Addon().setSetting("trakt.access_token", token["access_token"])
                    xbmcaddon.Addon().setSetting("trakt.refresh_token", token["refresh_token"])
                    import time as _time
                    xbmcaddon.Addon().setSetting("trakt.expires", str(_time.time() + token.get("expires_in", 7776000)))
                    user = api.get_user_settings(token['access_token'])
                    ids = user.get("user", {}).get("ids", {})
                    user_id = ids.get("slug") or user.get("user", {}).get("username", "")
                    if not user_id:
                        raise Exception("Trakt did not return a username for this account.")
                    xbmcaddon.Addon().setSetting("trakt.user_id", user_id)
                    xbmcgui.Dialog().notification("Trakt", "Device authorization was successful!", xbmcgui.NOTIFICATION_INFO)
                    success = True
                    break
                elif token_response.status_code == 404:
                    self._clear_auth_settings()
                    xbmcgui.Dialog().ok("Trakt Authorization Failed", "The device token is invalid. Please try authorizing again.")
                    break
                elif token_response.status_code == 410:
                    self._clear_auth_settings()
                    xbmcgui.Dialog().ok("Trakt Authorization Failed", "This token has expired. Please try authorizing again.")
                    break
                elif token_response.status_code == 418:
                    self._clear_auth_settings()
                    xbmcgui.Dialog().ok("Trakt Authorization Failed", "The device token was denied.")
                    break
                i += device_code["interval"]
                progress_dialog.update(int((i / device_code["expires_in"]) * 100))
            except Exception as e:
                xbmc.log(str(e), xbmc.LOGERROR)
                self._clear_auth_settings()
                xbmcgui.Dialog().ok("Trakt Authorization Failed", str(e))
                break
        progress_dialog.close()
        return success

    def routes(self, plugin):
        @plugin.route(f"/{self.name}/authorize")
        def auth():
            self.__auth()

        @plugin.route(f"/{self.name}/clear")
        def clear():
            if xbmcgui.Dialog().yesno("Revoke Trakt Authorization", "Are you sure you want to revoke the Trakt authorization?"):
                self._clear_auth_settings()
                xbmcaddon.Addon().setSetting("watched_indicators", "0")

class Trakt_API:
    @property
    def app_headers(self):
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id
        }

    @property
    def headers(self):
        headers = self.app_headers.copy()
        access_token = ownAddon.getSetting("trakt.access_token") or ""
        if access_token != "":
            headers["Authorization"] = "Bearer "  + access_token
        return headers

    session = DI.session
    base_url = "https://api.trakt.tv"

    def __init__(self):
        self.client_id = get_trakt_api_client_id()
        self.client_secret = get_trakt_api_client_secret()

    def _json_or_error(self, response, action):
        try:
            return response.json()
        except Exception:
            body = (getattr(response, "text", "") or "").strip()
            if len(body) > 200:
                body = body[:200] + "..."
            raise Exception(
                "Trakt returned a non-JSON response while %s. HTTP %s. %s" %
                (action, getattr(response, "status_code", "unknown"), body)
            )

    def device_code(self):
        response = self.session.post(f"{self.base_url}/oauth/device/code", data=json.dumps({"client_id": self.client_id}), headers=self.app_headers)
        code = self._json_or_error(response, "starting device authorization")
        return code
    
    def device_token(self, code) -> requests.Response:
        response = self.session.post(f"{self.base_url}/oauth/device/token", data=json.dumps({"code": code, "client_id": self.client_id, "client_secret": self.client_secret}), headers=self.app_headers)
        return response
    
    def get_user_settings(self, access_token=None):
        headers = self.headers.copy()
        if access_token:
            headers["Authorization"] = "Bearer " + access_token
        response = self.session.get(f"{self.base_url}/users/settings", headers=headers)
        settings = self._json_or_error(response, "loading Trakt user settings")
        return settings
    
    def get_movies_chart(self, chart: str, period: str = "weekly", page: int = 1):
        response = self.session.get(f"{self.base_url}/movies/{chart}{'/' + period if chart in ['recommended', 'played', 'watched', 'collected'] else ''}?extended=full", headers=self.headers, params={"page": page, "limit": 25})
        chart_list = response.json()
        return chart_list
    
    def get_shows_chart(self, chart: str, period: str = "weekly", page: int = 1):
        response = self.session.get(f"{self.base_url}/shows/{chart}{'/' + period if chart in ['recommended', 'played', 'watched', 'collected'] else ''}?extended=full", headers=self.headers, params={"page": page, "limit": 25})
        chart_list = response.json()
        return chart_list
    
    def get_collection(self, user_id: str, type: str, page: int = 1):
        response = self.session.get(f"{self.base_url}/users/{user_id}/collection/{type}?extended=full", headers=self.headers, params={"page": page, "limit": 25})
        collection = response.json()
        return collection
    
    def get_likes(self, user_id: str, type: str, page: int = 1):
        response = self.session.get(f"{self.base_url}/users/{user_id}/collection/{type}?extended=full", headers=self.headers, params={"page": page, "limit": 25})
        collection = response.json()
        return collection
    
    def get_watched(self, user_id: str, type: str):
        response = self.session.get(f"{self.base_url}/users/{user_id}/watched/{type}?extended=full", headers=self.headers)
        watched = response.json()
        return watched
    
    def get_watchlist(self, user_id: str, type: str = "", page: int = 1):
        response = self.session.get(f"{self.base_url}/users/{user_id}/watchlist{'/' + type if type != '' else ''}?extended=full", headers=self.headers, params={"page": page, "limit": 25})
        watchlist = response.json()
        return watchlist

    def get_recommendations(self, type: str, limit: int = 10):
        response = self.session.get(f"{self.base_url}/recommendations/{type}?extended=full&limit={limit}", headers=self.headers)
        recommendations = response.json()
        return recommendations

    def get_lists(self, user_id: str):
        response = self.session.get(f"{self.base_url}/users/{user_id}/lists?extended=full", headers=self.headers)
        trakt_lists = response.json()
        return trakt_lists


    def get_liked_lists(self, page: int = 1):
        response = self.session.get(f"{self.base_url}/users/likes/lists", headers=self.headers, params={"page": page, "limit": 25})
        trakt_lists = response.json()
        return trakt_lists

    def search_lists(self, query: str, page: int = 1):
        response = self.session.get(f"{self.base_url}/search/list", headers=self.headers, params={"query": query, "page": page, "limit": 25})
        trakt_lists = response.json()
        return trakt_lists
    def get_list(self, list_id, page: int = 1):
        response = self.session.get(f"{self.base_url}/lists/{list_id}/items?extended=full", headers=self.headers, params={"page": page, "limit": 25})
        trakt_list = response.json()
        return trakt_list
    
    def get_user_list(self, user_id, list_id, page: int = 1):
        response = self.session.get(f"{self.base_url}/users/{user_id}/lists/{list_id}/items?extended=full", headers=self.headers, params={"page": page, "limit": 25})
        trakt_list = response.json()
        return trakt_list

    def get_show(self, show_id: int):
        response = self.session.get(f"{self.base_url}/shows/{show_id}/seasons?extended=full", headers=self.headers)    
        trakt_show = response.json()     
        return trakt_show

    def get_season(self, show_id: int, season: int):
        response = self.session.get(f"{self.base_url}/shows/{show_id}/seasons/{season}?extended=full", headers=self.headers)
        trakt_season = response.json()        
        return trakt_season

    def process_items(self, items):
        items = [self.handle_item(item) for item in items]
        return items

    def handle_item(self, item):
        if "movie" in item:
            return self.handle_movie_xml(item["movie"])
        elif "show" in item:
            return self.handle_show_xml(item["show"])
        elif "airs" in item or "first_aired" in item:
            return self.handle_show_xml(item)
        else:
            return self.handle_movie_xml(item)

    def handle_movie_xml(self, movie):
        tmdb = TMDB_API()
        r = tmdb.get(f"movie/{movie['ids']['tmdb']}", full_meta=ownAddon.getSettingBool("full_meta"))
        infolabels = tmdb.get_infolabels(r, media_type="movie")
        cast = tmdb.get_cast(r)
        poster_path = tmdb.image_url + r["poster_path"] if r.get("poster_path") else ""
        backdrop_path = tmdb.image_url + r["backdrop_path"] if r.get("backdrop_path") else ""
        return {
            "title": movie["title"],
            "year": movie["year"],
            "content": "movie",
            "summary": movie["overview"],
            "tmdb_id": movie["ids"]["tmdb"],
            "imdb_id": movie["ids"]["imdb"],
            "infolabels": infolabels,
            "thumbnail": poster_path,
            "fanart": backdrop_path,
            "cast": cast,
            "type": "item",
            "link": "search"
        }

    def handle_show_xml(self, show):
        tmdb = TMDB_API()
        r = tmdb.get(f"tv/{show['ids']['tmdb']}", full_meta=ownAddon.getSettingBool("full_meta"))
        infolabels = tmdb.get_infolabels(r, media_type="tvshow")
        cast = tmdb.get_cast(r)
        poster_path = tmdb.image_url + r["poster_path"] if r.get("poster_path") else ""
        backdrop_path = tmdb.image_url + r["backdrop_path"] if r.get("backdrop_path") else ""
        return {
            "title": show["title"],
            "content": "tv",
            "link": f"trakt/seasons/{show['ids']['trakt']}::{show['ids']['tmdb']}::{show['title']}",
            "summary": show["overview"],
            "tmdb_id": show["ids"]["tmdb"],
            "imdb_id": show["ids"]["imdb"],
            "infolabels": infolabels,
            "thumbnail": poster_path,
            "fanart": backdrop_path,
            "cast": cast,
            "type": "dir"
        }

    def handle_season_xml(self, show, show_id):
        jen_list = []
        tmdb = TMDB_API()
        for season in show:
            r = tmdb.get(f"tv/{show_id.split('::')[1]}/season/{season['number']}", full_meta=ownAddon.getSettingBool("full_meta"))
            infolabels = tmdb.get_infolabels(r, media_type="tvshow")
            cast = tmdb.get_cast(r)
            poster_path = tmdb.image_url + r["poster_path"] if r.get("poster_path") else ""
            jen_list.append({
                "title": season["title"],
                "summary": season["overview"] or "N/A",
                "link": f"trakt/season/{show_id}/{season['number']}",
                "type": "dir",
                "infolabels": infolabels,
                "cast": cast,
                "thumbnail": poster_path,
            })
        return jen_list

    def handle_episodes_xml(self, show, season):
        tmdb = TMDB_API()
        jen_list = []
        for episode in season:
            r = tmdb.get(f"tv/{show.split('::')[1]}/season/{episode['season']}/episode/{episode['number']}", full_meta=ownAddon.getSettingBool("full_meta"))
            infolabels = tmdb.get_infolabels(r, media_type="tvshow")
            cast = tmdb.get_cast(r)
            still_path = tmdb.image_url + r["still_path"] if r.get("still_path") else ""
            
            jen_list.append({
                "title": episode["title"],
                "summary": episode['overview'] if episode["overview"] else "N/A",
                "content": "episode",
                "tmdb_id": episode["ids"]["tmdb"],
                "imdb_id": episode["ids"]["imdb"],
                "season": episode['season'],
                "episode": episode['number'],
                "premiered": (episode["first_aired"] if episode["first_aired"] else "2000-01-01").split("-")[0],
                "tv_show_title": show.split("::")[2],
                "infolabels": infolabels,
                "cast": cast,
                "thumbnail": still_path,
                "type": "item",
                "link": "search"
            })
        return jen_list
    
    def handle_lists_xml(self, lists, list_type="my_lists"):
        jen_list = []
        for item in lists or []:
            list_info = item.get("list", item) if isinstance(item, dict) else {}
            if not list_info:
                continue
            item_count = list_info.get("item_count", 0) or 0
            if item_count == 0:
                continue
            user = list_info.get("user", {}).get("ids", {}).get("slug") or list_info.get("username") or "Trakt"
            ids = list_info.get("ids", {})
            slug = ids.get("slug") or ids.get("trakt")
            if not slug:
                continue
            name = list_info.get("name") or "Trakt List"
            description = list_info.get("description") or ""
            if list_type in ("liked_lists", "search"):
                title = f"{name} | [I]{user} (x{item_count})[/I]"
            else:
                title = f"{name} [I](x{item_count})[/I]"
            summary_parts = []
            if description:
                summary_parts.append(description)
            summary_parts.append(f"[B]Author:[/B] {user}")
            jen_list.append({
                "title": title,
                "summary": "[CR][CR]".join(summary_parts),
                "type": "dir",
                "link": f"trakt/user/{user}/list/{slug}"
            })
        return jen_list

    def handle_list(self, items, pagination: bool = True, page_link: str = ""):
        items = self.process_items(items)
        if pagination:
            items.insert(0, {"type": "dir", "title": "Next Page", "link": page_link})
        return json.dumps({"items": items})
