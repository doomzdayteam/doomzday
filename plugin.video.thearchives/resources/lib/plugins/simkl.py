import json
from urllib.parse import quote, unquote

from ..DI import DI
from ..plugin import Plugin

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *


DEFAULT_BASE_URL = "https://api.simkl.com"
DEFAULT_CDN_URL = "https://data.simkl.in"
PIN_PATH = "/oauth/pin"
TEST_PATH = "/sync/activities"
API_TIMEOUT = 20
PAGE_LIMIT = 25
ALL_RATINGS = "1,2,3,4,5,6,7,8,9,10"


class SimklAPIError(Exception):
    def __init__(self, status_code, message, payload=None):
        self.status_code = status_code
        self.payload = payload or {}
        Exception.__init__(self, message or "Unknown Simkl API error")


def _setting(setting_id, default=""):
    value = xbmcaddon.Addon().getSetting(setting_id)
    return value if value not in (None, "") else default


def _set_setting(setting_id, value):
    xbmcaddon.Addon().setSetting(setting_id, "" if value is None else str(value))


def _split_state(url):
    parts = str(url or "").split("|")
    state = {"page": 1}
    for part in parts[1:]:
        if part.startswith("page:"):
            try:
                state["page"] = max(1, int(part[5:]))
            except (TypeError, ValueError):
                state["page"] = 1
    return parts[0], state


def _next_page_item(base_link, page):
    return {
        "type": "dir",
        "title": "Next Page",
        "link": "%s|page:%s" % (base_link, page),
        "thumbnail": "resources/media/playlists.png",
        "summary": "Load the next Simkl page",
    }


def _pagination_has_next(response, page, item_count=0):
    headers = getattr(response, "headers", {}) or {}
    try:
        page_count = int(headers.get("X-Pagination-Page-Count") or headers.get("x-pagination-page-count") or 0)
        if page_count:
            return int(page) < page_count
    except (TypeError, ValueError):
        pass
    try:
        limit = int(headers.get("X-Pagination-Limit") or headers.get("x-pagination-limit") or PAGE_LIMIT)
    except (TypeError, ValueError):
        limit = PAGE_LIMIT
    return bool(item_count and item_count >= limit)


def _first_value(source, *keys):
    if not isinstance(source, dict):
        return ""
    for key in keys:
        value = source.get(key)
        if value not in (None, "", []):
            return value
    return ""


def _image_url(value, kind="poster"):
    if not value:
        return ""
    value = str(value)
    if value.startswith(("http://", "https://", "special://")):
        return value
    if kind == "fanart":
        return "https://simkl.net/fanart/%s_0.jpg" % value
    return "https://wsrv.nl/?url=https://simkl.in/posters/%s_m.webp&q=90" % value


def _ids(media):
    ids = media.get("ids") if isinstance(media.get("ids"), dict) else {}
    return {
        "simkl": ids.get("simkl") or ids.get("simkl_id") or _first_value(media, "id", "simkl", "simkl_id"),
        "tmdb": ids.get("tmdb") or ids.get("tmdb_id") or _first_value(media, "tmdb", "tmdb_id"),
        "imdb": ids.get("imdb") or ids.get("imdb_id") or _first_value(media, "imdb", "imdb_id"),
        "tvdb": ids.get("tvdb") or ids.get("tvdb_id") or _first_value(media, "tvdb", "tvdb_id"),
        "mal": ids.get("mal") or ids.get("mal_id") or _first_value(media, "mal", "mal_id"),
    }


def _media_from_item(item, bucket=""):
    if not isinstance(item, dict):
        return None, ""
    for key in ("movie", "show", "anime"):
        if isinstance(item.get(key), dict):
            return item[key], key
    endpoint_type = str(item.get("endpoint_type") or "").lower()
    if endpoint_type in ("movies", "movie"):
        return item, "movie"
    if endpoint_type in ("tv", "shows", "show"):
        return item, "show"
    if endpoint_type == "anime":
        return item, "anime"
    bucket = str(bucket or "").lower()
    if bucket in ("movies", "movie"):
        return item, "movie"
    if bucket in ("shows", "tv", "show"):
        return item, "show"
    if bucket == "anime":
        return item, "anime"
    url = str(item.get("url") or "").lower()
    if "/anime/" in url:
        return item, "anime"
    if "/tv/" in url:
        return item, "show"
    if "/movie" in url:
        return item, "movie"
    return item, ""


def _rating_text(item, media):
    user_rating = _first_value(item, "user_rating", "rating")
    if user_rating:
        return "[B]Your Rating:[/B] %s" % user_rating
    ratings = media.get("ratings") if isinstance(media.get("ratings"), dict) else {}
    simkl = ratings.get("simkl") if isinstance(ratings.get("simkl"), dict) else {}
    rating = simkl.get("rating") if isinstance(simkl, dict) else ""
    if rating:
        return "[B]Simkl Rating:[/B] %s" % rating
    return ""


def _summary(item, media):
    parts = []
    description = _first_value(media, "description", "overview", "summary")
    if description:
        parts.append(str(description))
    status = _first_value(item, "status", "list", "watchlist_status") or _first_value(media, "status")
    if status:
        parts.append("[B]Status:[/B] %s" % status)
    watched_at = _first_value(item, "last_watched_at", "watched_at")
    if watched_at:
        parts.append("[B]Last Watched:[/B] %s" % watched_at)
    rated_at = _first_value(item, "user_rated_at", "rated_at")
    if rated_at:
        parts.append("[B]Rated:[/B] %s" % rated_at)
    rating = _rating_text(item, media)
    if rating:
        parts.append(rating)
    return "[CR][CR]".join(parts) if parts else "Simkl item"


def _title(media):
    title = _first_value(media, "title", "title_en", "title_romaji", "name")
    year = _first_value(media, "year", "release_year")
    if title and year:
        return "%s (%s)" % (title, year)
    return title or "Simkl Item"


def _media_item(item, bucket=""):
    media, media_type = _media_from_item(item, bucket)
    if not media:
        return None
    ids = _ids(media)
    poster = _image_url(_first_value(media, "poster", "image", "thumbnail"))
    fanart = _image_url(_first_value(media, "fanart", "backdrop"), kind="fanart")
    if media_type in ("show", "anime"):
        link = "tmdb/tv/%s" % ids["tmdb"] if ids["tmdb"] else "search"
        item_type = "dir" if ids["tmdb"] else "item"
        content = "tv"
    else:
        link = "search"
        item_type = "item"
        content = "movie"
    return {
        "type": item_type,
        "title": _title(media),
        "content": content,
        "link": link,
        "summary": _summary(item, media),
        "year": _first_value(media, "year", "release_year") or "",
        "tmdb_id": ids["tmdb"],
        "imdb_id": ids["imdb"],
        "tvdb_id": ids["tvdb"],
        "thumbnail": poster,
        "fanart": fanart,
    }


def _payload_items(payload, media_filter=""):
    items = []
    if isinstance(payload, list):
        for item in payload:
            converted = _media_item(item, media_filter)
            if converted:
                items.append(converted)
        return items
    if not isinstance(payload, dict):
        return items
    for bucket in ("movies", "shows", "tv", "anime", "items", "results"):
        bucket_items = payload.get(bucket)
        if not isinstance(bucket_items, list):
            continue
        for item in bucket_items:
            converted = _media_item(item, bucket)
            if converted:
                items.append(converted)
    return items


def build_simkl_qr_image_url(pin, size=800):
    try:
        from resources.lib.util.tmdb_qr import build_qr_image_url
    except ImportError:
        from ..util.tmdb_qr import build_qr_image_url
    verification_url = pin.get("verification_url") or pin.get("verification_uri") or "https://simkl.com/pin"
    return build_qr_image_url(verification_url, size=size)


def _poll_simkl_auth(dialog, api, pin):
    interval = int(pin.get("interval") or 5)
    expires_in = int(pin.get("expires_in") or 600)
    elapsed = 0
    user_code = pin.get("user_code") or pin.get("code") or ""
    while not dialog.cancelled and elapsed < expires_in and dialog.response is None:
        xbmc.sleep(interval * 1000)
        elapsed += interval
        try:
            token = api.pin_token(user_code)
            if token:
                dialog.response = token
                dialog.close()
                return
        except SimklAPIError as e:
            pending_value = str(e.payload.get("result") or e.payload.get("error") or "").lower()
            if pending_value in ("ko", "pending", "authorization_pending", "slow_down"):
                continue
            dialog.error = e
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


def _show_simkl_qr_auth_window(api, pin):
    import threading

    class SimklQRAuthDialog(xbmcgui.WindowXMLDialog):
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92

        def __init__(self, *args, **kwargs):
            xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
            self.cancelled = False
            self.response = None
            self.error = None

        def onAction(self, action):
            if action.getId() in (self.ACTION_PREVIOUS_MENU, self.ACTION_NAV_BACK):
                self.cancelled = True
                self.close()

    verification_url = pin.get("verification_url") or pin.get("verification_uri") or "https://simkl.com/pin"
    dialog = SimklQRAuthDialog("simkl_auth_qr.xml", PATH, "Default", "1080i")
    dialog.setProperty("simkl.title", "Simkl Account Authorization")
    dialog.setProperty("simkl.qr_url", build_simkl_qr_image_url(pin, size=800))
    dialog.setProperty("simkl.auth_url", verification_url)
    dialog.setProperty("simkl.user_code", pin.get("user_code") or pin.get("code") or "")
    worker = threading.Thread(target=_poll_simkl_auth, args=(dialog, api, pin))
    worker.daemon = True
    worker.start()
    dialog.doModal()
    dialog.cancelled = True
    worker.join(0.1)
    if dialog.error:
        raise dialog.error
    return dialog.response


class Simkl(Plugin):
    name = "simkl"

    def get_list(self, url):
        if not str(url or "").startswith("simkl"):
            return False
        base_url, state = _split_state(url)
        parts = base_url.split("/")
        if len(parts) < 2:
            return json.dumps({"items": []})
        api = SimklAPI()
        section = parts[1]
        try:
            if section == "user" and len(parts) > 2 and parts[2] == "profile":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.profile_items()})
            if section == "library" and len(parts) > 3:
                if not self.__check_auth():
                    return json.dumps({"items": []})
                media_type, status = parts[2], parts[3]
                return api.handle_media_page(api.library_items(media_type, status), None, base_url, media_type)
            if section == "ratings" and len(parts) > 2:
                if not self.__check_auth():
                    return json.dumps({"items": []})
                media_type = parts[2]
                return api.handle_media_page(api.user_ratings(media_type), None, base_url, media_type)
            if section == "search" and len(parts) > 2:
                search_type = parts[2]
                query = unquote(parts[3]) if len(parts) > 3 else xbmcgui.Dialog().input("Search Simkl")
                if not query:
                    return json.dumps({"items": []})
                search_base = "simkl/search/%s/%s" % (search_type, quote(query, safe=""))
                payload, response = api.search(search_type, query, state.get("page", 1))
                return api.handle_media_page(payload, response, search_base, search_type, state.get("page", 1))
            if section == "trending" and len(parts) > 2:
                media_type = parts[2]
                return api.handle_media_page(api.trending(media_type), None, base_url, media_type)
            if section == "best" and len(parts) > 3:
                media_type, filter_name = parts[2], parts[3]
                return api.handle_media_page(api.best(media_type, filter_name), None, base_url, media_type)
            if section == "genres" and len(parts) > 3:
                media_type, sort = parts[2], parts[3]
                payload, response = api.genres(media_type, sort, state.get("page", 1))
                return api.handle_media_page(payload, response, base_url, media_type, state.get("page", 1))
            if section == "changes":
                return json.dumps({"items": api.changes_items(api.changes())})
        except Exception as e:
            xbmc.log("[TheArchives][Simkl] Menu load failed: %s" % e, xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Simkl Error", str(e))
        return json.dumps({"items": []})

    def __check_auth(self):
        if _setting("simkl.access_token"):
            return True
        if xbmcgui.Dialog().yesno(
            "Simkl Authorization",
            "This action requires a Simkl account.\n\nWould you like to authorize Simkl now?",
        ):
            return self._auth()
        return False

    def _clear_auth_settings(self):
        for setting_id in ("simkl.access_token", "simkl.user_code"):
            _set_setting(setting_id, "")

    def _auth(self):
        api = SimklAPI()
        if not api.client_id:
            xbmcgui.Dialog().ok(
                "Simkl Authorization",
                "The addon is missing its Simkl API credentials.\nPlease add SIMKL_CLIENT_ID to dev_api.py before authorizing.",
            )
            return False
        try:
            pin = api.pin_code()
            _set_setting("simkl.user_code", pin.get("user_code") or pin.get("code") or "")
            token = _show_simkl_qr_auth_window(api, pin)
            if not token:
                xbmcgui.Dialog().ok(
                    "Simkl Authorization",
                    "Simkl authorization timed out or was cancelled.",
                )
                return False
            api.store_token(token)
            xbmcgui.Dialog().notification(
                "Simkl",
                "PIN authorization was successful!",
                xbmcgui.NOTIFICATION_INFO,
            )
            return True
        except Exception as e:
            xbmc.log("[TheArchives][Simkl] Authorization failed: %s" % e, xbmc.LOGERROR)
            self._clear_auth_settings()
            xbmcgui.Dialog().ok("Simkl Authorization Failed", str(e))
            return False

    def _test_connection(self):
        api = SimklAPI()
        if not api.access_token:
            xbmcgui.Dialog().ok("Simkl", "Simkl is not authorized.")
            return False
        try:
            api.test_connection()
            xbmcgui.Dialog().ok("Simkl", "Simkl authorization is working.")
            return True
        except Exception as e:
            xbmc.log("[TheArchives][Simkl] Connection test failed: %s" % e, xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Simkl Connection Failed", str(e))
            return False

    def routes(self, plugin):
        @plugin.route("/simkl/authorize")
        def auth():
            self._auth()

        @plugin.route("/simkl/clear")
        def clear():
            if xbmcgui.Dialog().yesno(
                "Revoke Simkl Authorization",
                "Are you sure you want to revoke the Simkl authorization?",
            ):
                self._clear_auth_settings()
                xbmcgui.Dialog().notification("Simkl", "Authorization revoked", xbmcgui.NOTIFICATION_INFO)

        @plugin.route("/simkl/test")
        def test():
            self._test_connection()


class SimklAPI:
    session = DI.session

    def __init__(self):
        self.base_url = (_setting("simkl.backend_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.cdn_url = DEFAULT_CDN_URL
        self.client_id = get_simkl_api_client_id()
        self.client_secret = get_simkl_api_client_secret()
        self.access_token = _setting("simkl.access_token")
        self.app_name = "the-archives-kodi"
        self.app_version = xbmcaddon.Addon().getAddonInfo("version") or "1.0"

    def _app_params(self, params=None):
        merged = dict(params or {})
        if self.client_id:
            merged.setdefault("client_id", self.client_id)
        merged.setdefault("app-name", self.app_name)
        merged.setdefault("app-version", self.app_version)
        return merged

    def _headers(self, auth=True):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "%s/%s" % (self.app_name, self.app_version),
        }
        if self.client_id:
            headers["simkl-api-key"] = self.client_id
        if auth and self.access_token:
            headers["Authorization"] = "Bearer " + self.access_token
        return headers

    def _json_or_error(self, response, action):
        try:
            payload = response.json() if response.text else {}
        except Exception:
            payload = {}
        if 200 <= response.status_code < 300:
            if isinstance(payload, dict) and payload.get("access_token"):
                return payload
            if action != "polling PIN authorization":
                return payload
        message = ""
        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("error") or payload.get("result") or ""
        if not message:
            body = (getattr(response, "text", "") or "").strip()
            message = "Simkl returned HTTP %s while %s. %s" % (
                response.status_code,
                action,
                body[:200],
            )
        raise SimklAPIError(response.status_code, message, payload)

    def _request_response(self, method, path, params=None, payload=None, auth=True, action="calling Simkl", base_url=None):
        response = self.session.request(
            method,
            (base_url or self.base_url) + path,
            params=self._app_params(params),
            data=json.dumps(payload) if payload is not None else None,
            headers=self._headers(auth=auth),
            timeout=API_TIMEOUT,
        )
        return self._json_or_error(response, action), response

    def _request(self, method, path, params=None, payload=None, auth=True, action="calling Simkl", base_url=None):
        payload, _response = self._request_response(
            method,
            path,
            params=params,
            payload=payload,
            auth=auth,
            action=action,
            base_url=base_url,
        )
        return payload

    def pin_code(self):
        return self._request(
            "GET",
            PIN_PATH,
            auth=False,
            action="starting PIN authorization",
        )

    def pin_token(self, user_code):
        return self._request(
            "GET",
            "%s/%s" % (PIN_PATH, user_code),
            auth=False,
            action="polling PIN authorization",
        )

    def store_token(self, token):
        access_token = token.get("access_token", "")
        if not access_token:
            raise SimklAPIError(0, "Simkl did not return an access token.", token)
        self.access_token = access_token
        _set_setting("simkl.access_token", self.access_token)

    def test_connection(self):
        return self._request("GET", TEST_PATH, auth=True, action="testing authorization")

    def user_settings(self):
        return self._request("POST", "/users/settings", auth=True, action="loading Simkl user settings")

    def activities(self):
        return self._request("GET", "/sync/activities", auth=True, action="loading Simkl sync activity")

    def library_items(self, media_type, status):
        if media_type not in ("movies", "shows", "anime", "all"):
            raise SimklAPIError(0, "Simkl library type must be movies, shows, anime, or all.")
        if status not in ("watching", "plantowatch", "hold", "completed", "dropped", "all"):
            raise SimklAPIError(0, "Simkl status is invalid.")
        return self._request(
            "GET",
            "/sync/all-items/%s/%s" % (media_type, status),
            params={"extended": "full", "next_watch_info": "yes", "language": "en"},
            auth=True,
            action="loading Simkl %s %s" % (media_type, status),
        )

    def user_ratings(self, media_type):
        if media_type not in ("movies", "shows", "anime"):
            raise SimklAPIError(0, "Simkl rating type must be movies, shows, or anime.")
        return self._request(
            "GET",
            "/sync/ratings/%s/%s" % (media_type, ALL_RATINGS),
            params={"extended": "full", "language": "en"},
            auth=True,
            action="loading Simkl ratings",
        )

    def search(self, search_type, query, page=1):
        if search_type not in ("movie", "tv", "anime"):
            raise SimklAPIError(0, "Simkl search type must be movie, tv, or anime.")
        return self._request_response(
            "GET",
            "/search/%s" % search_type,
            params={"q": query, "extended": "full", "page": int(page or 1), "limit": PAGE_LIMIT},
            auth=False,
            action="searching Simkl",
        )

    def trending(self, media_type):
        if media_type not in ("movies", "tv", "anime"):
            raise SimklAPIError(0, "Simkl trending type must be movies, tv, or anime.")
        return self._request(
            "GET",
            "/discover/trending/%s/today_100.json" % media_type,
            auth=False,
            action="loading Simkl trending",
            base_url=self.cdn_url,
        )

    def best(self, media_type, filter_name):
        if filter_name not in ("all", "year", "month", "voted", "watched"):
            filter_name = "all"
        if media_type not in ("tv", "anime"):
            raise SimklAPIError(0, "Simkl best type must be tv or anime.")
        return self._request(
            "GET",
            "/%s/best/%s" % (media_type, filter_name),
            auth=False,
            action="loading Simkl best %s" % media_type,
        )

    def genres(self, media_type, sort, page=1):
        if sort not in ("popular-this-week", "popular-this-month", "popular-all-time", "rank", "release-date", "voted", "watched"):
            sort = "popular-this-month"
        if media_type != "movies":
            raise SimklAPIError(0, "Only Simkl movie discovery is wired for this menu.")
        return self._request_response(
            "GET",
            "/movies/genres/all/movies/all/all/%s" % sort,
            params={"page": int(page or 1), "limit": PAGE_LIMIT},
            auth=False,
            action="loading Simkl movie discovery",
        )

    def changes(self):
        return self._request("GET", "/changes", params={"type": "movies,shows,anime"}, auth=False, action="loading Simkl catalog changes")

    def profile_items(self):
        profile = self.user_settings()
        activities = self.activities()
        account = profile.get("account") if isinstance(profile.get("account"), dict) else {}
        user = profile.get("user") if isinstance(profile.get("user"), dict) else {}
        identity = account or user or profile
        username = _first_value(identity, "name", "username", "user_name") or "Simkl"
        account_id = _first_value(identity, "id", "user_id")
        plan = _first_value(identity, "type", "plan") or "Unknown"
        details = [
            "[B]Username:[/B] %s" % username,
            "[B]Account Type:[/B] %s" % plan,
        ]
        if account_id:
            details.append("[B]Account ID:[/B] %s" % account_id)
        all_activity = _first_value(activities, "all")
        if all_activity:
            details.append("[B]Last Sync Activity:[/B] %s" % all_activity)
        return [{
            "type": "item",
            "title": "Simkl Account: %s" % username,
            "link": "message/%s" % quote("[CR]".join(details), safe=""),
            "thumbnail": _image_url(_first_value(identity, "avatar")) or "resources/media/settings.png",
            "summary": "[CR]".join(details),
        }]

    def changes_items(self, payload):
        items = []
        if not isinstance(payload, dict):
            return items
        for bucket, title in (("movies", "Updated Movies"), ("shows", "Updated TV Shows"), ("anime", "Updated Anime")):
            ids = payload.get(bucket)
            if not isinstance(ids, list) or not ids:
                continue
            preview = ", ".join([str(value) for value in ids[:20]])
            items.append({
                "type": "item",
                "title": "%s [I](x%s)[/I]" % (title, len(ids)),
                "link": "message/%s" % quote(preview, safe=""),
                "thumbnail": "resources/media/playlists.png",
                "summary": "Simkl IDs updated recently:[CR]%s" % preview,
            })
        return items

    def handle_media_page(self, payload, response=None, base_link="", media_filter="", page=1):
        items = _payload_items(payload, media_filter)
        if response is not None and _pagination_has_next(response, int(page or 1), len(items)):
            items.insert(0, _next_page_item(base_link, int(page or 1) + 1))
        return json.dumps({"items": items})
