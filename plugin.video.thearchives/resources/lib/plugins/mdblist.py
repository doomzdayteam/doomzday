import json
from urllib.parse import quote, unquote

from ..DI import DI
from ..plugin import Plugin

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *


DEFAULT_BASE_URL = "https://api.mdblist.com"
API_TIMEOUT = 20
PAGE_LIMIT = 25
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"


class MDBListAPIError(Exception):
    def __init__(self, status_code, message, payload=None):
        self.status_code = status_code
        self.payload = payload or {}
        Exception.__init__(self, message or "Unknown MDBList API error")


def _setting(setting_id, default=""):
    value = xbmcaddon.Addon().getSetting(setting_id)
    return value if value not in (None, "") else default


def _set_setting(setting_id, value):
    xbmcaddon.Addon().setSetting(setting_id, "" if value is None else str(value))


def _get_user_value(payload, *keys):
    if not isinstance(payload, dict):
        return ""
    user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
    for key in keys:
        value = payload.get(key)
        if value in (None, ""):
            value = user.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _split_state(url):
    parts = str(url or "").split("|")
    state = {"cursor": "", "offset": 0}
    for part in parts[1:]:
        if part.startswith("cursor:"):
            state["cursor"] = unquote(part[7:])
        elif part.startswith("offset:"):
            try:
                state["offset"] = int(part[7:])
            except (TypeError, ValueError):
                state["offset"] = 0
    return parts[0], state


def _next_cursor(payload, response):
    if isinstance(payload, dict):
        pagination = payload.get("pagination") if isinstance(payload.get("pagination"), dict) else {}
        cursor = pagination.get("next_cursor") or payload.get("next_cursor")
        if cursor:
            return str(cursor)
    headers = getattr(response, "headers", {}) or {}
    return headers.get("X-Next-Cursor") or headers.get("x-next-cursor") or ""


def _has_more(response):
    headers = getattr(response, "headers", {}) or {}
    value = headers.get("X-Has-More") or headers.get("x-has-more") or ""
    return str(value).lower() in ("1", "true", "yes")


def _next_page_item(base_link, cursor):
    return {
        "type": "dir",
        "title": "Next Page",
        "link": "%s|cursor:%s" % (base_link, quote(str(cursor), safe="")),
        "thumbnail": "resources/media/playlists.png",
        "summary": "Load the next MDBList page",
    }


def _next_offset_item(base_link, offset):
    return {
        "type": "dir",
        "title": "Next Page",
        "link": "%s|offset:%s" % (base_link, offset),
        "thumbnail": "resources/media/playlists.png",
        "summary": "Load the next MDBList page",
    }


def _image_url(value):
    if not value:
        return ""
    value = str(value)
    if value.startswith(("http://", "https://", "special://")):
        return value
    if value.startswith("/"):
        return TMDB_IMAGE_URL + value
    return value


def _first_value(source, *keys):
    if not isinstance(source, dict):
        return ""
    for key in keys:
        value = source.get(key)
        if value not in (None, "", []):
            return value
    return ""


def _ids(media):
    ids = media.get("ids") if isinstance(media.get("ids"), dict) else {}
    return {
        "tmdb": _first_value(media, "tmdb_id", "tmdb") or ids.get("tmdb") or "",
        "imdb": _first_value(media, "imdb_id", "imdb") or ids.get("imdb") or "",
        "trakt": _first_value(media, "trakt_id", "trakt") or ids.get("trakt") or "",
        "tvdb": _first_value(media, "tvdb_id", "tvdb") or ids.get("tvdb") or "",
        "mdblist": _first_value(media, "mdblist_id", "mdblist") or ids.get("mdblist") or "",
    }


def _media_type_from_item(item, bucket=""):
    media_type = str(_first_value(item, "mediatype", "media_type", "type") or "").lower()
    if media_type in ("movie", "show", "episode", "season"):
        return media_type
    bucket = str(bucket or "").lower()
    if bucket.startswith("movie"):
        return "movie"
    if bucket.startswith("show"):
        return "show"
    if bucket.startswith("episode"):
        return "episode"
    if bucket.startswith("season"):
        return "season"
    return ""


def _media_from_item(item, bucket=""):
    if not isinstance(item, dict):
        return None, ""
    for key in ("movie", "show", "episode", "season"):
        if isinstance(item.get(key), dict):
            return item[key], key
    return item, _media_type_from_item(item, bucket)


def _rating_text(item, media):
    rating = _first_value(item, "rating", "user_rating")
    if not rating:
        rating = _first_value(media, "rating", "score", "score_average")
    if not rating:
        return ""
    return "[B]Rating:[/B] %s" % rating


def _summary(item, media):
    parts = []
    description = _first_value(media, "description", "overview", "plot", "summary")
    if description:
        parts.append(str(description))
    watched_at = _first_value(item, "watched_at", "last_watched_at")
    if watched_at:
        parts.append("[B]Watched:[/B] %s" % watched_at)
    rated_at = _first_value(item, "rated_at")
    if rated_at:
        parts.append("[B]Rated:[/B] %s" % rated_at)
    rating = _rating_text(item, media)
    if rating:
        parts.append(rating)
    return "[CR][CR]".join(parts) if parts else "MDBList item"


def _title(media):
    title = _first_value(media, "title", "name")
    year = _first_value(media, "year", "release_year")
    if not year:
        release_date = _first_value(media, "release_date", "released", "first_air_date")
        year = str(release_date)[:4] if release_date else ""
    if title and year:
        return "%s (%s)" % (title, year)
    return title or "MDBList Item"


def _episode_item(item, media):
    show = item.get("show") if isinstance(item.get("show"), dict) else {}
    show_title = _first_value(show, "title", "name") or _first_value(item, "show_title", "tv_show_title")
    season = _first_value(media, "season", "season_number") or _first_value(item, "season", "season_number")
    episode = _first_value(media, "episode", "episode_number", "number") or _first_value(item, "episode", "episode_number")
    ep_title = _first_value(media, "title", "name") or "Episode"
    label = ep_title
    if show_title and season and episode:
        label = "%s S%02dE%02d - %s" % (show_title, int(season), int(episode), ep_title)
    ids = _ids(media)
    show_ids = _ids(show)
    return {
        "type": "item",
        "title": label,
        "content": "episode",
        "link": "search",
        "summary": _summary(item, media),
        "season": int(season) if str(season).isdigit() else 0,
        "episode": int(episode) if str(episode).isdigit() else 0,
        "tmdb_id": ids["tmdb"],
        "tv_show_tmdb_id": show_ids["tmdb"],
        "imdb_id": show_ids["imdb"] or ids["imdb"],
        "episode_imdb_id": ids["imdb"],
        "tv_show_title": show_title,
        "thumbnail": _image_url(_first_value(media, "poster", "poster_path", "image", "thumbnail", "still_path")),
    }


def _media_item(item, bucket=""):
    media, media_type = _media_from_item(item, bucket)
    if not media:
        return None
    if media_type == "episode":
        return _episode_item(item, media)
    ids = _ids(media)
    poster = _image_url(_first_value(media, "poster", "poster_path", "image", "thumbnail"))
    fanart = _image_url(_first_value(media, "backdrop", "backdrop_path", "fanart"))
    if media_type == "show":
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
        "thumbnail": poster,
        "fanart": fanart,
    }


def _payload_items(payload, media_filter=""):
    items = []
    if isinstance(payload, list):
        for item in payload:
            converted = _media_item(item)
            if converted and (not media_filter or converted.get("content") in (media_filter, "tv" if media_filter == "show" else media_filter)):
                items.append(converted)
        return items
    if not isinstance(payload, dict):
        return items
    for bucket in ("movies", "shows", "seasons", "episodes", "items", "results"):
        bucket_items = payload.get(bucket)
        if not isinstance(bucket_items, list):
            continue
        for item in bucket_items:
            converted = _media_item(item, bucket)
            if not converted:
                continue
            if media_filter == "movie" and converted.get("content") != "movie":
                continue
            if media_filter == "show" and converted.get("content") not in ("tv", "tvshow"):
                continue
            items.append(converted)
    return items


class MDBList(Plugin):
    name = "mdblist"

    def get_list(self, url):
        if not str(url or "").startswith("mdblist"):
            return False
        base_url, state = _split_state(url)
        parts = base_url.split("/")
        if len(parts) < 2:
            return json.dumps({"items": []})
        if not self.__check_auth():
            return json.dumps({"items": []})
        api = MDBListAPI()
        section = parts[1]
        try:
            if section == "user" and len(parts) > 2 and parts[2] == "profile":
                return json.dumps({"items": api.profile_items(api.user())})
            if section == "user" and len(parts) > 2 and parts[2] == "lists":
                return json.dumps({"items": api.handle_lists(api.user_lists())})
            if section == "lists" and len(parts) > 2 and parts[2] == "liked":
                payload, response = api.liked_lists(state.get("offset", 0))
                return api.handle_list_directory_page(payload, response, base_url, state.get("offset", 0))
            if section == "lists" and len(parts) > 2 and parts[2] == "search":
                query = unquote(parts[3]) if len(parts) > 3 else xbmcgui.Dialog().input("Search MDBList Lists")
                if not query:
                    return json.dumps({"items": []})
                payload, response = api.search_lists(query, state.get("offset", 0))
                search_base = "mdblist/lists/search/%s" % quote(query, safe="")
                return api.handle_list_directory_page(payload, response, search_base, state.get("offset", 0))
            if section == "list" and len(parts) > 2:
                media_type = parts[3] if len(parts) > 3 else ""
                payload, response = api.list_items(unquote(parts[2]), media_type, state.get("cursor", ""))
                return api.handle_media_page(payload, response, base_url, media_type)
            if section == "watchlist":
                media_type = parts[2] if len(parts) > 2 and parts[2] != "all" else ""
                payload, response = api.watchlist(media_type, state.get("cursor", ""))
                return api.handle_media_page(payload, response, base_url, media_type)
            if section == "collection":
                media_type = parts[2] if len(parts) > 2 else ""
                payload, response = api.sync_collection(media_type, state.get("cursor", ""))
                return api.handle_media_page(payload, response, base_url, media_type)
            if section == "watched":
                media_type = parts[2] if len(parts) > 2 else ""
                payload, response = api.sync_watched(media_type, state.get("cursor", ""))
                return api.handle_media_page(payload, response, base_url, media_type)
            if section == "ratings":
                media_type = parts[2] if len(parts) > 2 else ""
                payload, response = api.sync_ratings(state.get("cursor", ""))
                return api.handle_media_page(payload, response, base_url, media_type)
            if section == "recommendations" and len(parts) > 2:
                recommendation = parts[2]
                media_type = parts[3] if len(parts) > 3 else ""
                payload, response = api.recommendations(recommendation, media_type, state.get("cursor", ""))
                return api.handle_media_page(payload, response, base_url, media_type)
            if section == "catalog" and len(parts) > 2:
                media_type = parts[2]
                sort = parts[3] if len(parts) > 3 else "score"
                payload, response = api.catalog(media_type, sort, state.get("cursor", ""))
                return api.handle_media_page(payload, response, base_url, media_type)
            if section == "updates" and len(parts) > 2:
                media_type = parts[2]
                payload, response = api.updates(media_type, state.get("cursor", ""))
                return api.handle_media_page(payload, response, base_url, media_type)
        except Exception as e:
            xbmc.log("[TheArchives][MDBList] Menu load failed: %s" % e, xbmc.LOGERROR)
            xbmcgui.Dialog().ok("MDBList Error", str(e))
        return json.dumps({"items": []})

    def __check_auth(self):
        if _setting("mdblist.api_key"):
            return True
        if xbmcgui.Dialog().yesno(
            "MDBList Authorization",
            "This action requires an MDBList API key.\n\nWould you like to authorize MDBList now?",
        ):
            return self._authorize()
        return False

    def _clear_auth_settings(self):
        for setting_id in (
            "mdblist.api_key",
            "mdblist.user_id",
            "mdblist.username",
            "mdblist.plan",
        ):
            _set_setting(setting_id, "")

    def _store_identity(self, api_key, profile):
        _set_setting("mdblist.api_key", api_key)
        _set_setting("mdblist.user_id", _get_user_value(profile, "user_id", "id", "uuid"))
        _set_setting(
            "mdblist.username",
            _get_user_value(profile, "username", "user_name", "name", "slug"),
        )
        _set_setting("mdblist.plan", _get_user_value(profile, "plan", "patron_status", "reward_tier"))

    def _account_label(self):
        return (
            _setting("mdblist.username")
            or _setting("mdblist.user_id")
            or "authorized account"
        )

    def _read_api_key(self):
        dialog = xbmcgui.Dialog()
        try:
            api_key = dialog.input(
                "MDBList API Key",
                defaultt=_setting("mdblist.api_key"),
                type=getattr(xbmcgui, "INPUT_ALPHANUM", 0),
                option=getattr(xbmcgui, "ALPHANUM_HIDE_INPUT", 0),
            )
        except TypeError:
            api_key = dialog.input("MDBList API Key", _setting("mdblist.api_key"))
        return (api_key or "").strip()

    def _authorize(self):
        api_key = self._read_api_key()
        if not api_key:
            return False
        api = MDBListAPI(api_key=api_key)
        try:
            profile = api.user()
            self._store_identity(api_key, profile)
            xbmcgui.Dialog().ok(
                "MDBList",
                "MDBList authorization is working.\nConnected as %s." % self._account_label(),
            )
            return True
        except Exception as e:
            xbmc.log("[TheArchives][MDBList] Authorization failed: %s" % e, xbmc.LOGERROR)
            xbmcgui.Dialog().ok("MDBList Authorization Failed", str(e))
            return False

    def _test_connection(self):
        api = MDBListAPI()
        if not api.api_key:
            xbmcgui.Dialog().ok("MDBList", "MDBList is not authorized.")
            return False
        try:
            profile = api.user()
            self._store_identity(api.api_key, profile)
            xbmcgui.Dialog().ok(
                "MDBList",
                "MDBList authorization is working.\nConnected as %s." % self._account_label(),
            )
            return True
        except Exception as e:
            xbmc.log("[TheArchives][MDBList] Connection test failed: %s" % e, xbmc.LOGERROR)
            xbmcgui.Dialog().ok("MDBList Connection Failed", str(e))
            return False

    def routes(self, plugin):
        @plugin.route("/mdblist/authorize")
        def auth():
            self._authorize()

        @plugin.route("/mdblist/clear")
        def clear():
            if xbmcgui.Dialog().yesno(
                "Revoke MDBList Authorization",
                "Are you sure you want to revoke the MDBList authorization?",
            ):
                self._clear_auth_settings()
                xbmcgui.Dialog().notification("MDBList", "Authorization revoked", xbmcgui.NOTIFICATION_INFO)

        @plugin.route("/mdblist/test")
        def test():
            self._test_connection()


class MDBListAPI:
    session = DI.session

    def __init__(self, api_key=None):
        self.base_url = (_setting("mdblist.backend_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = (api_key or _setting("mdblist.api_key") or "").strip()

    def _headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "plugin.video.thearchives MDBList",
        }

    def _json_or_error(self, response, action):
        try:
            payload = response.json() if response.text else {}
        except Exception:
            payload = {}
        if 200 <= response.status_code < 300:
            return payload
        message = ""
        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("error") or ""
        if not message:
            body = (getattr(response, "text", "") or "").strip()
            message = "MDBList returned HTTP %s while %s. %s" % (
                response.status_code,
                action,
                body[:200],
            )
        raise MDBListAPIError(response.status_code, message, payload)

    def _request_response(self, method, path, params=None, action="calling MDBList"):
        merged_params = dict(params or {})
        if self.api_key:
            merged_params["apikey"] = self.api_key
        response = self.session.request(
            method,
            self.base_url + path,
            params=merged_params,
            headers=self._headers(),
            timeout=API_TIMEOUT,
        )
        return self._json_or_error(response, action), response

    def _request(self, method, path, params=None, action="calling MDBList"):
        payload, _response = self._request_response(method, path, params=params, action=action)
        return payload

    def _paged_params(self, cursor="", media_type="", extra=None):
        params = {
            "limit": PAGE_LIMIT,
            "append_to_response": "poster,description,ratings,genres",
            "unified": "true",
        }
        if cursor:
            params["cursor"] = cursor
        if media_type in ("movie", "show", "season", "episode"):
            params["mediatype"] = media_type
        if extra:
            params.update(extra)
        return params

    def user(self):
        if not self.api_key:
            raise MDBListAPIError(0, "MDBList API key is missing.")
        return self._request("GET", "/user", action="checking MDBList authorization")

    def user_lists(self):
        return self._request(
            "GET",
            "/lists/user",
            params={"sort": "ranked", "unified": "true", "append_to_response": "poster"},
            action="loading MDBList user lists",
        )

    def liked_lists(self, offset=0):
        return self._request_response(
            "GET",
            "/lists/liked",
            params={"limit": PAGE_LIMIT, "offset": offset},
            action="loading liked MDBList lists",
        )

    def search_lists(self, query, offset=0):
        return self._request_response(
            "GET",
            "/lists/search",
            params={"query": query, "limit": PAGE_LIMIT, "offset": offset},
            action="searching MDBList lists",
        )

    def list_items(self, list_id, media_type="", cursor=""):
        return self._request_response(
            "GET",
            "/lists/%s/items" % list_id,
            params=self._paged_params(cursor, media_type),
            action="loading MDBList list items",
        )

    def watchlist(self, media_type="", cursor=""):
        path = "/watchlist/items/%s" % media_type if media_type in ("movie", "show") else "/watchlist/items"
        return self._request_response(
            "GET",
            path,
            params=self._paged_params(cursor),
            action="loading MDBList watchlist",
        )

    def sync_collection(self, media_type="", cursor=""):
        return self._request_response(
            "GET",
            "/sync/collection",
            params=self._paged_params(cursor, media_type, {"sort": "sort_title", "order": "asc"}),
            action="loading MDBList collection",
        )

    def sync_watched(self, media_type="", cursor=""):
        return self._request_response(
            "GET",
            "/sync/watched",
            params=self._paged_params(cursor, media_type),
            action="loading MDBList watched history",
        )

    def sync_ratings(self, cursor=""):
        return self._request_response(
            "GET",
            "/sync/ratings",
            params=self._paged_params(cursor),
            action="loading MDBList ratings",
        )

    def recommendations(self, section, media_type="", cursor=""):
        return self._request_response(
            "GET",
            "/lists/recommended/%s/items" % section,
            params=self._paged_params(cursor, media_type),
            action="loading MDBList recommendations",
        )

    def catalog(self, media_type, sort="score", cursor=""):
        if media_type not in ("movie", "show"):
            raise MDBListAPIError(0, "MDBList catalog media type must be movie or show.")
        params = {"limit": PAGE_LIMIT, "sort": sort, "sort_order": "desc"}
        if cursor:
            params["cursor"] = cursor
        return self._request_response(
            "GET",
            "/catalog/%s" % media_type,
            params=params,
            action="loading MDBList catalog",
        )

    def updates(self, media_type, cursor=""):
        if media_type not in ("movie", "show"):
            raise MDBListAPIError(0, "MDBList updates media type must be movie or show.")
        params = {"limit": PAGE_LIMIT}
        if cursor:
            params["cursor"] = cursor
        path = "/movies/updates" if media_type == "movie" else "/shows/updates"
        return self._request_response("GET", path, params=params, action="loading MDBList updates")

    def profile_items(self, profile):
        username = _get_user_value(profile, "username", "name") or "MDBList"
        plan = _get_user_value(profile, "plan", "patron_status") or "Unknown"
        limit = _get_user_value(profile, "rate_limit", "api_requests") or "Unknown"
        remaining = _get_user_value(profile, "rate_limit_remaining")
        used = _get_user_value(profile, "api_requests_count")
        details = [
            "[B]Username:[/B] %s" % username,
            "[B]Plan:[/B] %s" % plan,
            "[B]API Limit:[/B] %s" % limit,
        ]
        if remaining:
            details.append("[B]Remaining:[/B] %s" % remaining)
        if used:
            details.append("[B]Used:[/B] %s" % used)
        return [{
            "type": "item",
            "title": "MDBList Account: %s" % username,
            "link": "message/%s" % quote("[CR]".join(details), safe=""),
            "thumbnail": _image_url(profile.get("avatar_url")) or "resources/media/settings.png",
            "summary": "[CR]".join(details),
        }]

    def handle_lists(self, lists):
        items = []
        for info in lists or []:
            if not isinstance(info, dict):
                continue
            list_id = info.get("id") or info.get("list_id")
            if not list_id:
                continue
            count = info.get("items") or info.get("item_count") or info.get("items_count") or 0
            if str(count).isdigit() and int(count) == 0:
                continue
            name = info.get("name") or info.get("title") or "MDBList List"
            user = info.get("username") or info.get("user") or "MDBList"
            title = "%s [I](x%s)[/I]" % (name, count) if count else name
            summary_parts = []
            description = info.get("description") or info.get("summary") or ""
            if description:
                summary_parts.append(description)
            summary_parts.append("[B]Author:[/B] %s" % user)
            items.append({
                "type": "dir",
                "title": title,
                "link": "mdblist/list/%s" % quote(str(list_id), safe=""),
                "thumbnail": _image_url(info.get("poster") or info.get("image") or info.get("thumbnail")) or "resources/media/playlists.png",
                "summary": "[CR][CR]".join(summary_parts),
            })
        return items

    def handle_list_directory_page(self, payload, response, base_link, offset):
        items = self.handle_lists(payload)
        if _has_more(response):
            items.insert(0, _next_offset_item(base_link, int(offset or 0) + PAGE_LIMIT))
        return json.dumps({"items": items})

    def handle_media_page(self, payload, response, base_link, media_filter=""):
        items = _payload_items(payload, media_filter)
        cursor = _next_cursor(payload, response)
        if cursor:
            items.insert(0, _next_page_item(base_link, cursor))
        return json.dumps({"items": items})
