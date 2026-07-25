from resources.lib.plugins.tmdb_plugin import TMDB_API
from ..DI import DI
from ..plugin import Plugin
from resources.lib.plugins.tmdb_plugin import _color_future_title
import json, time, requests
from urllib.parse import quote
try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *

API_TIMEOUT = 12
PAGE_LIMIT = 25


def _popup_item(title, summary, thumbnail="resources/media/settings.png"):
    return {
        "type": "item",
        "title": title,
        "link": "message/%s" % quote(str(summary or ""), safe=""),
        "thumbnail": thumbnail,
        "summary": summary,
    }


def _context_summary(prefix_parts, base_summary):
    parts = [part for part in prefix_parts if part]
    if base_summary:
        parts.append(base_summary)
    return "[CR][CR]".join(parts) if parts else base_summary


class TraktAPIError(Exception):
    def __init__(self, message, status_code=None):
        super(TraktAPIError, self).__init__(message)
        self.status_code = status_code

def build_trakt_qr_image_url(device_code, size=800):
    try:
        from resources.lib.util.tmdb_qr import build_qr_image_url
    except ImportError:
        from ..util.tmdb_qr import build_qr_image_url
    verification_url = device_code.get("verification_url") or device_code.get("verification_uri") or "https://trakt.tv/activate"
    return build_qr_image_url(verification_url, size=size)

def _poll_trakt_auth(dialog, api, device_code):
    interval = int(device_code.get("interval") or 5)
    expires_in = int(device_code.get("expires_in") or 600)
    elapsed = 0
    while not dialog.cancelled and elapsed < expires_in and dialog.response is None:
        xbmc.sleep(interval * 1000)
        elapsed += interval
        try:
            token_response = api.device_token(device_code["device_code"])
            if token_response.status_code in (200, 404, 410, 418):
                dialog.response = token_response
                dialog.close()
                return
        except Exception as e:
            dialog.error = e
            dialog.close()
            return
    dialog.cancelled = True
    try:
        dialog.close()
    except:
        pass

def _show_trakt_qr_auth_window(api, device_code):
    import threading

    class TraktQRAuthDialog(xbmcgui.WindowXMLDialog):
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92

        def __init__(self, *args, **kwargs):
            super(TraktQRAuthDialog, self).__init__(*args, **kwargs)
            self.cancelled = False
            self.response = None
            self.error = None

        def onAction(self, action):
            if action.getId() in (self.ACTION_PREVIOUS_MENU, self.ACTION_NAV_BACK):
                self.cancelled = True
                self.close()

    verification_url = device_code.get("verification_url") or device_code.get("verification_uri") or "https://trakt.tv/activate"
    dialog = TraktQRAuthDialog("trakt_auth_qr.xml", PATH, "Default", "1080i")
    dialog.setProperty("trakt.title", "Trakt Account Authorization")
    dialog.setProperty("trakt.qr_url", build_trakt_qr_image_url(device_code, size=800))
    dialog.setProperty("trakt.auth_url", verification_url)
    dialog.setProperty("trakt.user_code", device_code.get("user_code", ""))
    worker = threading.Thread(target=_poll_trakt_auth, args=(dialog, api, device_code))
    worker.daemon = True
    worker.start()
    dialog.doModal()
    dialog.cancelled = True
    worker.join(0.1)
    if dialog.error:
        raise dialog.error
    return dialog.response

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
                use_auth = False
                if split[2] == "self":
                    if not self.__check_auth():
                        return
                    user_id = ownAddon.getSetting("trakt.user_id")
                    use_auth = True
                else:
                    user_id = split[2]
                if split[3] == "profile":
                    return json.dumps({"items": api.profile_items(user_id, use_auth=use_auth)})
                if split[3] == "stats":
                    return json.dumps({"items": api.stats_items(user_id, use_auth=use_auth)})
                if split[3] == "collection":
                    collection, has_next = api.get_collection(user_id, split[4], page=page)
                    return api.handle_list(collection, pagination=has_next, page_link=page_split[0] + "|" + str(page + 1))
                elif split[3] == "lists":
                    lists = api.get_lists(user_id, use_auth=use_auth)
                    return json.dumps({"items": api.handle_lists_xml(lists, list_type="my_lists")})
                elif split[3] == "liked_lists":
                    lists = api.get_liked_lists(page=page)
                    return json.dumps({"items": api.handle_lists_xml(lists, list_type="liked_lists")})
                elif split[3] == "list":
                    list = api.get_user_list(user_id, split[4], page=page, use_auth=split[2] == "self")
                    return api.handle_list(list, page_link=page_split[0] + "|" + str(page + 1))
                elif split[3] == "watched":
                    watched, has_next = api.get_watched(user_id, split[4], page=page)
                    return api.handle_list(watched, pagination=has_next, page_link=page_split[0] + "|" + str(page + 1))
                elif split[3] == "history":
                    history, has_next = api.get_history(user_id, split[4] if len(split) > 4 else "", page=page)
                    return api.handle_list(history, pagination=has_next, page_link=page_split[0] + "|" + str(page + 1))
                elif split[3] == "watchlist":
                    watched, has_next = api.get_watchlist(user_id, split[4] if len(split) > 4 else "", page=page)
                    return api.handle_list(watched, pagination=has_next, page_link=page_split[0] + "|" + str(page + 1))
                elif split[3] == "favorites":
                    favorites, has_next = api.get_favorites(user_id, split[4] if len(split) > 4 else "", page=page)
                    return api.handle_list(favorites, pagination=has_next, page_link=page_split[0] + "|" + str(page + 1))
                elif split[3] == "ratings":
                    ratings, has_next = api.get_ratings(user_id, split[4] if len(split) > 4 else "", page=page)
                    return api.handle_list(ratings, pagination=has_next, page_link=page_split[0] + "|" + str(page + 1))
            elif split[1] == "recommendations":
                if self.__check_auth():
                    recommendations = api.get_recommendations(split[2], 25)
                    return api.handle_list(recommendations, page_link=page_split[0] + "|" + str(page + 1))
    
    def __check_auth(self):
        user_id = ownAddon.getSetting("trakt.user_id")
        access_token = ownAddon.getSetting("trakt.access_token")
        if user_id == "" or access_token == "":
            if user_id != "" or access_token != "":
                self._clear_auth_settings()
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
        success = False
        try:
            token_response = _show_trakt_qr_auth_window(api, device_code)
            if not token_response:
                xbmcgui.Dialog().ok("Trakt Authorization", "Trakt authorization timed out or was cancelled.")
                return False
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
            elif token_response.status_code == 404:
                self._clear_auth_settings()
                xbmcgui.Dialog().ok("Trakt Authorization Failed", "The device token is invalid. Please try authorizing again.")
            elif token_response.status_code == 410:
                self._clear_auth_settings()
                xbmcgui.Dialog().ok("Trakt Authorization Failed", "This token has expired. Please try authorizing again.")
            elif token_response.status_code == 418:
                self._clear_auth_settings()
                xbmcgui.Dialog().ok("Trakt Authorization Failed", "The device token was denied.")
            else:
                self._clear_auth_settings()
                xbmcgui.Dialog().ok("Trakt Authorization Failed", "Trakt returned HTTP %s while authorizing." % token_response.status_code)
        except Exception as e:
            xbmc.log(str(e), xbmc.LOGERROR)
            self._clear_auth_settings()
            xbmcgui.Dialog().ok("Trakt Authorization Failed", str(e))
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

    def _get(self, url, **kwargs):
        kwargs.setdefault("timeout", API_TIMEOUT)
        return self.session.get(url, **kwargs)

    def _post(self, url, **kwargs):
        kwargs.setdefault("timeout", API_TIMEOUT)
        return self.session.post(url, **kwargs)

    def _json_or_error(self, response, action):
        status_code = getattr(response, "status_code", None)
        body = (getattr(response, "text", "") or "").strip()
        if len(body) > 200:
            body = body[:200] + "..."
        payload = None
        parsed_json = False
        try:
            payload = response.json()
            parsed_json = True
        except Exception:
            pass
        if status_code and status_code >= 400:
            detail = ""
            if isinstance(payload, dict):
                detail = payload.get("error") or payload.get("message") or payload.get("description") or ""
            if not detail:
                detail = body
            if status_code == 401:
                message = "Trakt authorization failed while %s. Re-authorize Trakt in addon settings." % action
            elif status_code == 429:
                message = "Trakt rate limited the addon while %s. Try again in a little bit." % action
            else:
                message = "Trakt returned HTTP %s while %s." % (status_code, action)
            if detail:
                message += "\n\n%s" % detail
            raise TraktAPIError(message, status_code)
        if parsed_json:
            return payload
        raise TraktAPIError(
            "Trakt returned a non-JSON response while %s. HTTP %s. %s" %
            (action, status_code or "unknown", body)
        )

    def _json_or_empty(self, response, action, clear_auth=False):
        try:
            return self._json_or_error(response, action)
        except TraktAPIError as e:
            if clear_auth:
                self._clear_auth_if_unauthorized(e)
            xbmc.log(str(e), xbmc.LOGERROR)
            try:
                xbmcgui.Dialog().ok("Trakt Error", str(e))
            except Exception:
                pass
            return []

    def _json_or_dict(self, response, action, clear_auth=False):
        try:
            return self._json_or_error(response, action)
        except TraktAPIError as e:
            if clear_auth:
                self._clear_auth_if_unauthorized(e)
            xbmc.log(str(e), xbmc.LOGERROR)
            try:
                xbmcgui.Dialog().ok("Trakt Error", str(e))
            except Exception:
                pass
            return {}

    def _paged_json(self, response, action, page, limit, clear_auth=False):
        try:
            items = self._json_or_error(response, action)
        except TraktAPIError as e:
            if clear_auth:
                self._clear_auth_if_unauthorized(e)
            xbmc.log(str(e), xbmc.LOGERROR)
            try:
                xbmcgui.Dialog().ok("Trakt Error", str(e))
            except Exception:
                pass
            return [], False
        try:
            page_count = int(response.headers.get("X-Pagination-Page-Count", ""))
            has_next = page < page_count
        except (AttributeError, TypeError, ValueError):
            has_next = isinstance(items, list) and len(items) >= limit
        return items, has_next

    def _clear_auth_if_unauthorized(self, error):
        if getattr(error, "status_code", None) != 401:
            return
        xbmcaddon.Addon().setSetting("trakt.access_token", "")
        xbmcaddon.Addon().setSetting("trakt.refresh_token", "")
        xbmcaddon.Addon().setSetting("trakt.user_id", "")
        xbmcaddon.Addon().setSetting("trakt.expires", "0")

    def device_code(self):
        response = self._post(f"{self.base_url}/oauth/device/code", data=json.dumps({"client_id": self.client_id}), headers=self.app_headers)
        code = self._json_or_error(response, "starting device authorization")
        return code
    
    def device_token(self, code) -> requests.Response:
        response = self._post(f"{self.base_url}/oauth/device/token", data=json.dumps({"code": code, "client_id": self.client_id, "client_secret": self.client_secret}), headers=self.app_headers)
        return response
    
    def get_user_settings(self, access_token=None):
        headers = self.headers.copy()
        if access_token:
            headers["Authorization"] = "Bearer " + access_token
        response = self._get(f"{self.base_url}/users/settings", headers=headers)
        settings = self._json_or_error(response, "loading Trakt user settings")
        return settings
    
    def get_movies_chart(self, chart: str, period: str = "weekly", page: int = 1):
        response = self._get(f"{self.base_url}/movies/{chart}{'/' + period if chart in ['recommended', 'played', 'watched', 'collected', 'favorited'] else ''}?extended=full", headers=self.app_headers, params={"page": page, "limit": 25})
        chart_list = self._json_or_empty(response, "loading Trakt movies chart")
        return chart_list
    
    def get_shows_chart(self, chart: str, period: str = "weekly", page: int = 1):
        response = self._get(f"{self.base_url}/shows/{chart}{'/' + period if chart in ['recommended', 'played', 'watched', 'collected', 'favorited'] else ''}?extended=full", headers=self.app_headers, params={"page": page, "limit": 25})
        chart_list = self._json_or_empty(response, "loading Trakt shows chart")
        return chart_list
    
    def get_collection(self, user_id: str, type: str, page: int = 1):
        limit = 25
        response = self._get(f"{self.base_url}/users/{user_id}/collection/{type}?extended=full", headers=self.headers, params={"page": page, "limit": limit})
        return self._paged_json(response, "loading Trakt collection", page, limit, clear_auth=True)
    
    def get_likes(self, user_id: str, type: str, page: int = 1):
        response = self._get(f"{self.base_url}/users/{user_id}/collection/{type}?extended=full", headers=self.headers, params={"page": page, "limit": 25})
        collection = self._json_or_empty(response, "loading Trakt likes", clear_auth=True)
        return collection
    
    def get_watched(self, user_id: str, type: str, page: int = 1):
        limit = 25
        response = self._get(f"{self.base_url}/users/{user_id}/watched/{type}", headers=self.headers, params={"page": page, "limit": limit})
        return self._paged_json(response, "loading Trakt watched history", page, limit, clear_auth=True)

    def get_history(self, user_id: str, type: str = "", page: int = 1):
        limit = PAGE_LIMIT
        path = f"{self.base_url}/users/{user_id}/history"
        if type:
            path += "/" + type
        response = self._get(path, headers=self.headers, params={"page": page, "limit": limit, "extended": "full"})
        return self._paged_json(response, "loading Trakt history", page, limit, clear_auth=True)
    
    def get_watchlist(self, user_id: str, type: str = "", page: int = 1):
        limit = 25
        response = self._get(f"{self.base_url}/users/{user_id}/watchlist{'/' + type if type != '' else ''}?extended=full", headers=self.headers, params={"page": page, "limit": limit})
        return self._paged_json(response, "loading Trakt watchlist", page, limit, clear_auth=True)

    def get_favorites(self, user_id: str, type: str = "", page: int = 1):
        limit = PAGE_LIMIT
        media_type = type if type in ("movies", "shows") else ""
        path = f"{self.base_url}/users/{user_id}/favorites"
        if media_type:
            path += f"/{media_type}/rank/asc"
        response = self._get(path, headers=self.headers, params={"page": page, "limit": limit, "extended": "full"})
        return self._paged_json(response, "loading Trakt favorites", page, limit, clear_auth=True)

    def get_ratings(self, user_id: str, type: str = "", page: int = 1):
        limit = PAGE_LIMIT
        media_type = type if type in ("movies", "shows", "episodes") else ""
        path = f"{self.base_url}/users/{user_id}/ratings"
        if media_type:
            path += "/" + media_type
        response = self._get(path, headers=self.headers, params={"page": page, "limit": limit, "extended": "full"})
        return self._paged_json(response, "loading Trakt ratings", page, limit, clear_auth=True)

    def get_recommendations(self, type: str, limit: int = 10):
        response = self._get(f"{self.base_url}/recommendations/{type}?extended=full&limit={limit}", headers=self.headers)
        recommendations = self._json_or_empty(response, "loading Trakt recommendations", clear_auth=True)
        return recommendations

    def get_lists(self, user_id: str, use_auth: bool = False):
        headers = self.headers if use_auth else self.app_headers
        response = self._get(f"{self.base_url}/users/{user_id}/lists?extended=full", headers=headers)
        trakt_lists = self._json_or_empty(response, "loading Trakt lists", clear_auth=use_auth)
        return trakt_lists

    def get_user_profile(self, user_id: str, use_auth: bool = False):
        headers = self.headers if use_auth else self.app_headers
        response = self._get(f"{self.base_url}/users/{user_id}", headers=headers, params={"extended": "full"})
        return self._json_or_dict(response, "loading Trakt user profile", clear_auth=use_auth)

    def get_user_stats(self, user_id: str, use_auth: bool = False):
        headers = self.headers if use_auth else self.app_headers
        response = self._get(f"{self.base_url}/users/{user_id}/stats", headers=headers)
        return self._json_or_dict(response, "loading Trakt user stats", clear_auth=use_auth)


    def get_liked_lists(self, page: int = 1):
        response = self._get(f"{self.base_url}/users/likes/lists", headers=self.headers, params={"page": page, "limit": 25})
        trakt_lists = self._json_or_empty(response, "loading liked Trakt lists", clear_auth=True)
        return trakt_lists

    def search_lists(self, query: str, page: int = 1):
        response = self._get(f"{self.base_url}/search/list", headers=self.app_headers, params={"query": query, "page": page, "limit": 25})
        trakt_lists = self._json_or_empty(response, "searching Trakt lists")
        return trakt_lists
    def get_list(self, list_id, page: int = 1):
        response = self._get(f"{self.base_url}/lists/{list_id}/items?extended=full", headers=self.app_headers, params={"page": page, "limit": 25})
        trakt_list = self._json_or_empty(response, "loading Trakt list items")
        return trakt_list
    
    def get_user_list(self, user_id, list_id, page: int = 1, use_auth: bool = False):
        headers = self.headers if use_auth else self.app_headers
        response = self._get(f"{self.base_url}/users/{user_id}/lists/{list_id}/items?extended=full", headers=headers, params={"page": page, "limit": 25})
        trakt_list = self._json_or_empty(response, "loading Trakt user list items", clear_auth=use_auth)
        return trakt_list

    def get_show(self, show_id: int):
        response = self._get(f"{self.base_url}/shows/{show_id}/seasons?extended=full", headers=self.app_headers)    
        trakt_show = self._json_or_empty(response, "loading Trakt show seasons")     
        return trakt_show

    def get_season(self, show_id: int, season: int):
        response = self._get(f"{self.base_url}/shows/{show_id}/seasons/{season}?extended=full", headers=self.app_headers)
        trakt_season = self._json_or_empty(response, "loading Trakt season episodes")        
        return trakt_season

    def process_items(self, items):
        items = [self.handle_item(item) for item in items]
        return items

    def handle_item(self, item):
        context = []
        if isinstance(item, dict):
            if item.get("rating") not in (None, ""):
                context.append("[B]Your Rating:[/B] %s" % item.get("rating"))
            if item.get("rated_at"):
                context.append("[B]Rated:[/B] %s" % item.get("rated_at"))
            if item.get("watched_at"):
                context.append("[B]Watched:[/B] %s" % item.get("watched_at"))
        if "movie" in item:
            result = self.handle_movie_xml(item["movie"])
            result["summary"] = _context_summary(context, result.get("summary"))
            return result
        elif "show" in item:
            if "episode" in item:
                result = self.handle_episode_xml(item.get("show") or {}, item.get("episode") or {})
            else:
                result = self.handle_show_xml(item["show"])
            result["summary"] = _context_summary(context, result.get("summary"))
            return result
        elif "episode" in item:
            result = self.handle_episode_xml({}, item.get("episode") or {})
            result["summary"] = _context_summary(context, result.get("summary"))
            return result
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
            "title": _color_future_title(movie["title"], r.get("release_date")),
            "year": movie["year"],
            "content": "movie",
            "summary": movie.get("overview") or r.get("overview") or "N/A",
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
        show_imdb = show.get("ids", {}).get("imdb") or ""
        return {
            "title": _color_future_title(show["title"], r.get("first_air_date")),
            "content": "tv",
            "link": f"trakt/seasons/{show['ids']['trakt']}::{show['ids']['tmdb']}::{show['title']}::{show.get('year') or ''}::{show_imdb}",
            "summary": show.get("overview") or r.get("overview") or "N/A",
            "tmdb_id": show["ids"]["tmdb"],
            "imdb_id": show["ids"]["imdb"],
            "infolabels": infolabels,
            "thumbnail": poster_path,
            "fanart": backdrop_path,
            "cast": cast,
            "type": "dir"
        }

    def handle_episode_xml(self, show, episode):
        tmdb = TMDB_API()
        show_ids = show.get("ids", {}) if isinstance(show, dict) else {}
        episode_ids = episode.get("ids", {}) if isinstance(episode, dict) else {}
        show_tmdb = show_ids.get("tmdb") or ""
        show_title = show.get("title") or ""
        show_year = show.get("year") or ""
        show_imdb = show_ids.get("imdb") or ""
        season = episode.get("season") or episode.get("season_number") or 0
        number = episode.get("number") or episode.get("episode") or episode.get("episode_number") or 0
        episode_title = episode.get("title") or "Episode"
        premiered = (episode.get("first_aired") or "").split("T")[0] or ""
        r = {}
        if show_tmdb and season and number:
            try:
                r = tmdb.get(f"tv/{show_tmdb}/season/{season}/episode/{number}", full_meta=ownAddon.getSettingBool("full_meta"))
            except Exception:
                r = {}
        still_path = tmdb.image_url + r["still_path"] if r.get("still_path") else ""
        label = episode_title
        if show_title and season and number:
            try:
                label = "%s S%02dE%02d - %s" % (show_title, int(season), int(number), episode_title)
            except (TypeError, ValueError):
                label = "%s S%sE%s - %s" % (show_title, season, number, episode_title)
        jen_item = {
            "title": _color_future_title(label, r.get("air_date") or premiered),
            "summary": episode.get("overview") or r.get("overview") or "N/A",
            "content": "episode",
            "tmdb_id": episode_ids.get("tmdb") or r.get("id") or "",
            "tv_show_tmdb_id": show_tmdb,
            "imdb_id": show_imdb,
            "episode_imdb_id": episode_ids.get("imdb") or "",
            "season": season,
            "episode": number,
            "premiered": premiered,
            "year": int(show_year) if str(show_year).isdigit() else 0,
            "tv_show_title": show_title,
            "thumbnail": still_path,
            "type": "item",
            "link": "search",
        }
        if ownAddon.getSettingBool("full_meta") and isinstance(r, dict) and r:
            jen_item["infolabels"] = tmdb.get_infolabels(r, media_type="episode")
            jen_item["cast"] = tmdb.get_cast(r, media_type="episode")
        return jen_item

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
        show_parts = show.split("::")
        show_tmdb = show_parts[1] if len(show_parts) > 1 else ""
        show_title = show_parts[2] if len(show_parts) > 2 else ""
        show_year = show_parts[3] if len(show_parts) > 3 else ""
        show_imdb = show_parts[4] if len(show_parts) > 4 else ""
        if not show_imdb and show_tmdb:
            try:
                show_imdb = (tmdb.get(f"tv/{show_tmdb}/external_ids") or {}).get("imdb_id") or ""
            except Exception:
                show_imdb = ""
        for episode in season:
            r = tmdb.get(f"tv/{show_tmdb}/season/{episode['season']}/episode/{episode['number']}", full_meta=ownAddon.getSettingBool("full_meta"))
            infolabels = tmdb.get_infolabels(r, media_type="tvshow")
            cast = tmdb.get_cast(r)
            still_path = tmdb.image_url + r["still_path"] if r.get("still_path") else ""
            first_aired = episode.get("first_aired") or ""
            premiered = first_aired.split("T")[0] if first_aired else "2000-01-01"
            year = show_year or premiered.split("-")[0]
            episode_imdb = episode.get("ids", {}).get("imdb") or ""
            
            jen_list.append({
                "title": _color_future_title(
                    episode["title"], r.get("air_date") or premiered
                ),
                "summary": episode['overview'] if episode["overview"] else "N/A",
                "content": "episode",
                "tmdb_id": episode["ids"]["tmdb"],
                "tv_show_tmdb_id": show_tmdb,
                "imdb_id": show_imdb or episode_imdb,
                "episode_imdb_id": episode_imdb,
                "season": episode['season'],
                "episode": episode['number'],
                "premiered": premiered,
                "year": int(year) if str(year).isdigit() else 0,
                "tv_show_title": show_title,
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

    def profile_items(self, user_id, use_auth: bool = False):
        profile = self.get_user_profile(user_id, use_auth=use_auth)
        username = profile.get("username") or profile.get("name") or user_id
        ids = profile.get("ids", {}) if isinstance(profile.get("ids"), dict) else {}
        details = [
            "[B]Username:[/B] %s" % username,
            "[B]User ID:[/B] %s" % (ids.get("slug") or user_id),
        ]
        if profile.get("name"):
            details.append("[B]Name:[/B] %s" % profile.get("name"))
        if profile.get("joined_at"):
            details.append("[B]Joined:[/B] %s" % profile.get("joined_at"))
        if profile.get("vip"):
            details.append("[B]VIP:[/B] Yes")
        return [_popup_item("Trakt Account: %s" % username, "[CR]".join(details))]

    def stats_items(self, user_id, use_auth: bool = False):
        stats = self.get_user_stats(user_id, use_auth=use_auth)
        lines = []
        for section in ("movies", "shows", "episodes", "network", "ratings"):
            data = stats.get(section)
            if not isinstance(data, dict):
                continue
            values = []
            for key in ("watched", "collected", "ratings", "comments", "plays", "minutes"):
                if data.get(key) not in (None, ""):
                    values.append("%s: %s" % (key, data.get(key)))
            if values:
                lines.append("[B]%s:[/B] %s" % (section.title(), ", ".join(values)))
        return [_popup_item("Trakt Stats", "[CR]".join(lines) if lines else json.dumps(stats, sort_keys=True)[:1500])]
