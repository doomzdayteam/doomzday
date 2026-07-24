import json
import time
import uuid
from urllib.parse import quote, unquote

from ..DI import DI
from ..plugin import Plugin

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *


DEFAULT_BASE_URL = "https://punchplay.tv"
DEFAULT_SCOPE = "profile:read playback:read playback:write events:read"
REQUIRED_SCOPES = ("profile:read", "playback:read")
DEVICE_CODE_PATH = "/api/platform/v1/auth/device/code"
DEVICE_TOKEN_PATH = "/api/platform/v1/auth/device/token"
REFRESH_PATH = "/api/platform/v1/auth/refresh"
ME_PATH = "/api/platform/v1/me"
PLAYBACK_PATH = "/api/platform/v1/playback/%s"
PAGE_LIMIT = 25
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"


class PunchPlayAPIError(Exception):
    def __init__(self, status_code, error, message):
        self.status_code = status_code
        self.error = error or ""
        self.message = message or error or "Unknown PunchPlay API error"
        Exception.__init__(self, self.message)


def _setting(setting_id, default=""):
    value = xbmcaddon.Addon().getSetting(setting_id)
    return value if value not in (None, "") else default


def _set_setting(setting_id, value):
    xbmcaddon.Addon().setSetting(setting_id, "" if value is None else str(value))


def _normalized_scope(scope):
    parts = [part for part in str(scope or DEFAULT_SCOPE).split() if part]
    for required in REQUIRED_SCOPES:
        if required not in parts:
            parts.append(required)
    return " ".join(parts)


def _split_state(url):
    parts = str(url or "").split("|")
    state = {"offset": 0, "cursor": ""}
    for part in parts[1:]:
        if part.startswith("offset:"):
            try:
                state["offset"] = max(0, int(part[7:]))
            except (TypeError, ValueError):
                state["offset"] = 0
        elif part.startswith("cursor:"):
            state["cursor"] = unquote(part[7:])
    return parts[0], state


def _next_offset_item(base_link, offset):
    return {
        "type": "dir",
        "title": "Next Page",
        "link": "%s|offset:%s" % (base_link, offset),
        "thumbnail": "resources/media/playlists.png",
        "summary": "Load the next PunchPlay page",
    }


def _next_cursor_item(base_link, cursor):
    return {
        "type": "dir",
        "title": "Next Page",
        "link": "%s|cursor:%s" % (base_link, quote(str(cursor), safe="")),
        "thumbnail": "resources/media/playlists.png",
        "summary": "Load the next PunchPlay page",
    }


def _next_cursor(payload):
    if not isinstance(payload, dict):
        return ""
    for key in ("nextCursor", "next_cursor", "cursor"):
        value = payload.get(key)
        if value:
            return str(value)
    pagination = payload.get("pagination") if isinstance(payload.get("pagination"), dict) else {}
    for key in ("nextCursor", "next_cursor", "cursor"):
        value = pagination.get(key)
        if value:
            return str(value)
    return ""


def _first_value(source, *keys):
    if not isinstance(source, dict):
        return ""
    for key in keys:
        value = source.get(key)
        if value not in (None, "", []):
            return value
    return ""


def _image_url(value):
    if not value:
        return ""
    value = str(value)
    if value.startswith(("http://", "https://", "special://")):
        return value
    if value.startswith("/"):
        return TMDB_IMAGE_URL + value
    return value


def _message_item(title, message, thumbnail="resources/media/settings.png"):
    return {
        "type": "item",
        "title": title,
        "link": "message/%s" % quote(str(message or ""), safe=""),
        "thumbnail": thumbnail,
        "summary": str(message or ""),
    }


def _payload_list(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in (
        "items",
        "data",
        "results",
        "history",
        "watchHistory",
        "recentWatchHistory",
        "ratings",
        "favourites",
        "favorites",
        "statuses",
        "collection",
        "lists",
        "continueWatching",
        "inProgress",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _payload_list(value)
            if nested:
                return nested
    return []


def _ids(item):
    ids = item.get("ids") if isinstance(item.get("ids"), dict) else {}
    return {
        "tmdb": _first_value(item, "tmdbId", "tmdb_id", "tmdb") or ids.get("tmdb") or ids.get("tmdbId") or "",
        "imdb": _first_value(item, "imdbId", "imdb_id", "imdb") or ids.get("imdb") or ids.get("imdbId") or "",
        "tvdb": _first_value(item, "tvdbId", "tvdb_id", "tvdb") or ids.get("tvdb") or ids.get("tvdbId") or "",
        "punchplay": _first_value(item, "punchplayId", "punchplay_id", "id", "sourceId") or ids.get("punchplay") or "",
    }


def _media_type(item):
    value = str(_first_value(item, "mediaType", "media_type", "type", "kind", "format") or "").lower()
    if value in ("movie", "movies", "film"):
        return "movie"
    if value in ("episode", "episodes"):
        return "episode"
    if value in ("show", "shows", "tv", "tvshow", "series"):
        return "show"
    if item.get("season") or item.get("episode") or item.get("episodeNumber"):
        return "episode"
    return value


def _progress_text(item):
    progress = _first_value(item, "progressPercent", "progress_percent", "progress")
    if progress in (None, ""):
        return ""
    try:
        value = float(progress)
        if value <= 1:
            value *= 100
        return "[B]Progress:[/B] %.1f%%" % value
    except (TypeError, ValueError):
        return "[B]Progress:[/B] %s" % progress


def _media_title(item):
    title = _first_value(item, "title", "name", "showTitle", "movieTitle") or "PunchPlay Item"
    season = _first_value(item, "season", "seasonNumber")
    episode = _first_value(item, "episode", "episodeNumber")
    episode_title = _first_value(item, "episodeTitle", "episode_title")
    if season and episode:
        try:
            prefix = "%s S%02dE%02d" % (title, int(season), int(episode))
        except (TypeError, ValueError):
            prefix = "%s S%sE%s" % (title, season, episode)
        return "%s - %s" % (prefix, episode_title) if episode_title else prefix
    year = _first_value(item, "year", "releaseYear")
    if year:
        return "%s (%s)" % (title, year)
    return title


def _summary(item):
    parts = []
    for label, keys in (
        ("Status", ("watchStatus", "watch_status", "status", "playbackState")),
        ("Rating", ("rating", "userRating", "user_rating")),
        ("Updated", ("updatedAt", "updated_at")),
        ("Watched", ("watchedAt", "watched_at", "lastWatchedAt")),
        ("Source", ("mediaSource", "source", "externalSource")),
    ):
        value = _first_value(item, *keys)
        if value:
            parts.append("[B]%s:[/B] %s" % (label, value))
    progress = _progress_text(item)
    if progress:
        parts.append(progress)
    overview = _first_value(item, "overview", "summary", "description")
    if overview:
        parts.insert(0, str(overview))
    return "[CR][CR]".join(parts) if parts else "PunchPlay item"


def _media_item(item):
    if not isinstance(item, dict):
        return None
    ids = _ids(item)
    media_type = _media_type(item)
    poster = _image_url(_first_value(item, "posterPath", "poster", "thumbnail", "image"))
    fanart = _image_url(_first_value(item, "backdropPath", "fanart", "backdrop"))
    if media_type == "episode":
        content = "episode"
        link = "search"
        item_type = "item"
    elif media_type in ("show", "tv"):
        content = "tv"
        link = "tmdb/tv/%s" % ids["tmdb"] if ids["tmdb"] else "search"
        item_type = "dir" if ids["tmdb"] else "item"
    else:
        content = "movie"
        link = "search"
        item_type = "item"
    return {
        "type": item_type,
        "title": _media_title(item),
        "content": content,
        "link": link,
        "summary": _summary(item),
        "year": _first_value(item, "year", "releaseYear") or "",
        "tmdb_id": ids["tmdb"],
        "imdb_id": ids["imdb"],
        "tvdb_id": ids["tvdb"],
        "thumbnail": poster,
        "fanart": fanart,
    }


def _media_items(payload):
    items = []
    for item in _payload_list(payload):
        converted = _media_item(item)
        if converted:
            items.append(converted)
    return items


def _now_expires(expires_in):
    try:
        return str(int(time.time()) + int(expires_in or 0))
    except (TypeError, ValueError):
        return "0"


def _device_id():
    device_id = _setting("punchplay.device_id")
    if not device_id:
        device_id = str(uuid.uuid4())
        _set_setting("punchplay.device_id", device_id)
    return device_id


def build_punchplay_qr_image_url(device_code, size=800):
    try:
        from resources.lib.util.tmdb_qr import build_qr_image_url
    except ImportError:
        from ..util.tmdb_qr import build_qr_image_url
    qr_url = device_code.get("verification_uri_qr") or ""
    if qr_url.lower().startswith(("http://", "https://")):
        return qr_url
    approval_url = (
        device_code.get("verification_uri_complete")
        or device_code.get("verification_uri")
        or DEFAULT_BASE_URL
    )
    return build_qr_image_url(approval_url, size=size)


def _poll_punchplay_auth(dialog, api, device_code):
    interval = int(device_code.get("interval") or 5)
    expires_in = int(device_code.get("expires_in") or 600)
    elapsed = 0
    while not dialog.cancelled and elapsed < expires_in and dialog.response is None:
        xbmc.sleep(interval * 1000)
        elapsed += interval
        try:
            token = api.device_token(device_code["device_code"])
            if token:
                dialog.response = token
                dialog.close()
                return
        except PunchPlayAPIError as e:
            if e.error in ("authorization_pending", "slow_down"):
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


def _show_punchplay_qr_auth_window(api, device_code):
    import threading

    class PunchPlayQRAuthDialog(xbmcgui.WindowXMLDialog):
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

    verification_url = device_code.get("verification_uri") or DEFAULT_BASE_URL
    dialog = PunchPlayQRAuthDialog("punchplay_auth_qr.xml", PATH, "Default", "1080i")
    dialog.setProperty("punchplay.title", "PunchPlay Account Authorization")
    dialog.setProperty("punchplay.qr_url", build_punchplay_qr_image_url(device_code, size=800))
    dialog.setProperty("punchplay.auth_url", verification_url)
    dialog.setProperty("punchplay.user_code", device_code.get("user_code", ""))
    worker = threading.Thread(target=_poll_punchplay_auth, args=(dialog, api, device_code))
    worker.daemon = True
    worker.start()
    dialog.doModal()
    dialog.cancelled = True
    worker.join(0.1)
    if dialog.error:
        raise dialog.error
    return dialog.response


class PunchPlay(Plugin):
    name = "punchplay"

    def get_list(self, url):
        if not str(url or "").startswith("punchplay"):
            return False
        base_url, state = _split_state(url)
        parts = base_url.split("/")
        api = PunchPlayAPI()
        if len(parts) < 2:
            return json.dumps({"items": []})
        section = parts[1]
        try:
            if section == "user" and len(parts) > 2 and parts[2] == "profile":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.identity_items(api.load_identity())})
            if section == "public":
                if len(parts) > 2 and parts[2] == "self":
                    username = _setting("punchplay.username")
                    if not username:
                        username = xbmcgui.Dialog().input("PunchPlay Username")
                elif len(parts) > 2 and parts[2] == "search":
                    username = xbmcgui.Dialog().input("PunchPlay Username")
                else:
                    username = unquote(parts[2]) if len(parts) > 2 else ""
                if not username:
                    return json.dumps({"items": []})
                return json.dumps({"items": api.public_profile_items(api.public_profile(username))})
            if section == "playback" and len(parts) > 2:
                if not self.__check_auth():
                    return json.dumps({"items": []})
                if parts[2] == "now-playing":
                    return json.dumps({"items": api.single_media_items(api.now_playing(), "Nothing is currently playing in PunchPlay.")})
                if parts[2] == "in-progress":
                    return json.dumps({"items": api.media_page(api.in_progress(), base_url, state.get("offset", 0))})
            if section == "continue-watching":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.media_page(api.continue_watching(), base_url, state.get("offset", 0))})
            if section == "history":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                payload = api.history(state.get("cursor", ""))
                return json.dumps({"items": api.media_page(payload, base_url, state.get("offset", 0), paginate=True, next_cursor=_next_cursor(payload))})
            if section == "ratings":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.media_page(api.ratings(), base_url, state.get("offset", 0))})
            if section == "favourites":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.media_page(api.favourites(), base_url, state.get("offset", 0))})
            if section == "watch-status":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.media_page(api.watch_status(), base_url, state.get("offset", 0))})
            if section == "collection":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.media_page(api.collection(), base_url, state.get("offset", 0))})
            if section == "lists":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.list_directory(api.lists())})
            if section == "list" and len(parts) > 2:
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.media_page(api.list_items(unquote(parts[2]), state.get("offset", 0)), base_url, state.get("offset", 0), paginate=True)})
            if section == "community-stats":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                return json.dumps({"items": api.stats_items(api.community_stats())})
        except Exception as e:
            xbmc.log("[TheArchives][PunchPlay] Menu load failed: %s" % e, xbmc.LOGERROR)
            xbmcgui.Dialog().ok("PunchPlay Error", str(e))
        return json.dumps({"items": []})

    def __check_auth(self):
        if _setting("punchplay.access_token"):
            return True
        if xbmcgui.Dialog().yesno(
            "PunchPlay Authorization",
            "This action requires a PunchPlay account.\n\nWould you like to authorize PunchPlay now?",
        ):
            return self._auth()
        return False

    def _clear_auth_settings(self):
        for setting_id in (
            "punchplay.access_token",
            "punchplay.refresh_token",
            "punchplay.user_id",
            "punchplay.username",
            "punchplay.expires",
            "punchplay.refresh_expires",
        ):
            _set_setting(setting_id, "")

    def _auth(self):
        api = PunchPlayAPI()
        if not api.client_id:
            xbmcgui.Dialog().ok(
                "PunchPlay Authorization",
                "The addon is missing its PunchPlay API credentials.\nPlease add PUNCHPLAY_CLIENT_ID to dev_api.py before authorizing.",
            )
            return False
        try:
            device_code = api.device_code()
            token = _show_punchplay_qr_auth_window(api, device_code)
            if not token:
                xbmcgui.Dialog().ok(
                    "PunchPlay Authorization",
                    "PunchPlay authorization timed out or was cancelled.",
                )
                return False
            api.store_token(token)
            try:
                api.load_identity()
            except Exception as e:
                xbmc.log("[TheArchives][PunchPlay] Identity check after auth failed: %s" % e, xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(
                "PunchPlay",
                "Device authorization was successful!",
                xbmcgui.NOTIFICATION_INFO,
            )
            return True
        except Exception as e:
            xbmc.log("[TheArchives][PunchPlay] Authorization failed: %s" % e, xbmc.LOGERROR)
            self._clear_auth_settings()
            xbmcgui.Dialog().ok("PunchPlay Authorization Failed", str(e))
            return False

    def _test_connection(self):
        api = PunchPlayAPI()
        if not api.access_token:
            xbmcgui.Dialog().ok("PunchPlay", "PunchPlay is not authorized.")
            return False
        try:
            identity = api.load_identity()
            username = (
                identity.get("username")
                or identity.get("name")
                or identity.get("email")
                or "authorized account"
            )
            xbmcgui.Dialog().ok("PunchPlay", "Connected as %s." % username)
            return True
        except Exception as e:
            xbmc.log("[TheArchives][PunchPlay] Connection test failed: %s" % e, xbmc.LOGERROR)
            xbmcgui.Dialog().ok("PunchPlay Connection Failed", str(e))
            return False

    def routes(self, plugin):
        @plugin.route("/punchplay/authorize")
        def auth():
            self._auth()

        @plugin.route("/punchplay/clear")
        def clear():
            if xbmcgui.Dialog().yesno(
                "Revoke PunchPlay Authorization",
                "Are you sure you want to revoke the PunchPlay authorization?",
            ):
                self._clear_auth_settings()
                xbmcgui.Dialog().notification("PunchPlay", "Authorization revoked", xbmcgui.NOTIFICATION_INFO)

        @plugin.route("/punchplay/test")
        def test():
            self._test_connection()


class PunchPlayAPI:
    session = DI.session

    def __init__(self):
        self.base_url = (_setting("punchplay.backend_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.client_id = get_punchplay_api_client_id()
        self.client_secret = get_punchplay_api_client_secret()
        self.scope = _normalized_scope(_setting("punchplay.scope", DEFAULT_SCOPE))
        self.access_token = _setting("punchplay.access_token")
        self.refresh_token = _setting("punchplay.refresh_token")

    def _headers(self, auth=True):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "plugin.video.thearchives PunchPlay",
        }
        if auth and self.access_token:
            headers["Authorization"] = "Bearer " + self.access_token
        return headers

    def _client_payload(self):
        payload = {"client_id": self.client_id}
        if self.client_secret:
            payload["client_secret"] = self.client_secret
        return payload

    def _json_or_error(self, response, action):
        try:
            payload = response.json() if response.text else {}
        except Exception:
            payload = {}
        if 200 <= response.status_code < 300:
            return payload
        error = payload.get("error") if isinstance(payload, dict) else ""
        message = payload.get("message") if isinstance(payload, dict) else ""
        if not message:
            body = (getattr(response, "text", "") or "").strip()
            message = "PunchPlay returned HTTP %s while %s. %s" % (
                response.status_code,
                action,
                body[:200],
            )
        raise PunchPlayAPIError(response.status_code, error, message)

    def _request(self, method, path, payload=None, auth=True, retry_on_401=True, params=None):
        response = self.session.request(
            method,
            self.base_url + path,
            params=params,
            data=json.dumps(payload) if payload is not None else None,
            headers=self._headers(auth=auth),
            timeout=20,
        )
        if response.status_code == 401 and auth and retry_on_401 and self.refresh_token:
            if self.refresh_access_token():
                return self._request(method, path, payload, auth=auth, retry_on_401=False, params=params)
        return self._json_or_error(response, path)

    def device_code(self):
        payload = self._client_payload()
        if self.scope:
            payload["scope"] = self.scope
        return self._request("POST", DEVICE_CODE_PATH, payload, auth=False)

    def device_token(self, device_code):
        payload = self._client_payload()
        payload.update({
            "device_code": device_code,
            "device_id": _device_id(),
            "device_name": xbmc.getInfoLabel("System.FriendlyName") or "Kodi",
        })
        return self._request("POST", DEVICE_TOKEN_PATH, payload, auth=False)

    def store_token(self, token):
        self.access_token = token.get("access_token", "")
        self.refresh_token = token.get("refresh_token", "")
        _set_setting("punchplay.access_token", self.access_token)
        _set_setting("punchplay.refresh_token", self.refresh_token)
        _set_setting("punchplay.expires", _now_expires(token.get("expires_in")))
        _set_setting("punchplay.refresh_expires", _now_expires(token.get("refresh_expires_in")))
        if token.get("username"):
            _set_setting("punchplay.username", token.get("username"))

    def refresh_access_token(self):
        if not self.client_id or not self.refresh_token:
            return False
        payload = self._client_payload()
        payload["refresh_token"] = self.refresh_token
        try:
            token = self._request("POST", REFRESH_PATH, payload, auth=False, retry_on_401=False)
            self.store_token(token)
            return True
        except Exception as e:
            xbmc.log("[TheArchives][PunchPlay] Token refresh failed: %s" % e, xbmc.LOGWARNING)
            return False

    def load_identity(self):
        identity = self._request("GET", ME_PATH, auth=True)
        _set_setting("punchplay.user_id", identity.get("id", ""))
        _set_setting("punchplay.username", identity.get("username") or identity.get("name") or identity.get("email") or "")
        return identity

    def send_playback_event(self, action, payload):
        if action not in ("start", "pause", "resume", "stop", "progress"):
            raise ValueError("Unsupported PunchPlay playback action: %s" % action)
        return self._request("POST", PLAYBACK_PATH % action, payload, auth=True)

    def public_profile(self, username):
        return self._request(
            "GET",
            "/api/public/v1/users/%s" % quote(str(username), safe=""),
            auth=False,
            params={"historyLimit": 20},
        )

    def now_playing(self):
        return self._request("GET", "/api/platform/v1/playback/now-playing", auth=True)

    def in_progress(self):
        return self._request("GET", "/api/platform/v1/playback/in-progress", auth=True)

    def continue_watching(self):
        return self._request("GET", "/api/platform/v1/me/continue-watching", auth=True)

    def history(self, cursor=""):
        params = {"limit": PAGE_LIMIT}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/api/platform/v1/me/history", auth=True, params=params)

    def ratings(self):
        return self._request("GET", "/api/platform/v1/me/ratings", auth=True)

    def favourites(self):
        return self._request("GET", "/api/platform/v1/me/favourites", auth=True)

    def watch_status(self):
        return self._request("GET", "/api/platform/v1/me/watch-status", auth=True)

    def lists(self):
        return self._request("GET", "/api/platform/v1/me/lists", auth=True)

    def list_items(self, list_id, offset=0):
        return self._request("GET", "/api/platform/v1/lists/%s/items" % quote(str(list_id), safe=""), auth=True, params={"offset": int(offset or 0), "limit": PAGE_LIMIT})

    def collection(self):
        return self._request("GET", "/api/platform/v1/me/collection", auth=True)

    def community_stats(self):
        return self._request("GET", "/api/platform/v1/me/community-stats", auth=True)

    def identity_items(self, identity):
        username = _first_value(identity, "username", "name", "email") or "PunchPlay"
        details = [
            "[B]Username:[/B] %s" % username,
        ]
        user_id = _first_value(identity, "id", "userId")
        if user_id:
            details.append("[B]User ID:[/B] %s" % user_id)
        scopes = _first_value(identity, "scope", "scopes") or self.scope
        if isinstance(scopes, list):
            scopes = " ".join(scopes)
        if scopes:
            details.append("[B]Scopes:[/B] %s" % scopes)
        return [_message_item("PunchPlay Account: %s" % username, "[CR]".join(details))]

    def public_profile_items(self, payload):
        if not isinstance(payload, dict):
            return []
        profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
        stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
        username = _first_value(profile, "displayName", "username") or "PunchPlay User"
        details = []
        for label, value in (
            ("Username", _first_value(profile, "username")),
            ("Display Name", _first_value(profile, "displayName")),
            ("Bio", _first_value(profile, "bio")),
            ("Watched", _first_value(stats, "watched")),
            ("Top Genre", _first_value(stats, "topGenre")),
            ("Member Since", _first_value(profile, "memberSince")),
        ):
            if value:
                details.append("[B]%s:[/B] %s" % (label, value))
        items = [_message_item("PunchPlay Public Profile: %s" % username, "[CR]".join(details), _image_url(_first_value(profile, "avatarUrl")) or "resources/media/settings.png")]
        items.extend(_media_items(payload.get("recentWatchHistory") or []))
        return items

    def single_media_items(self, payload, empty_message):
        if not payload:
            return [_message_item("PunchPlay", empty_message, "resources/media/progress.png")]
        if isinstance(payload, dict) and payload.get("data") is None and len(payload) == 1:
            return [_message_item("PunchPlay", empty_message, "resources/media/progress.png")]
        item = _media_item(payload)
        return [item] if item else [_message_item("PunchPlay", empty_message, "resources/media/progress.png")]

    def media_page(self, payload, base_link, offset=0, paginate=False, next_cursor=""):
        items = _media_items(payload)
        if paginate and next_cursor:
            items.insert(0, _next_cursor_item(base_link, next_cursor))
        elif paginate and len(items) >= PAGE_LIMIT:
            items.insert(0, _next_offset_item(base_link, int(offset or 0) + PAGE_LIMIT))
        if not items:
            items.append(_message_item("PunchPlay", "No PunchPlay items were returned for this view.", "resources/media/playlists.png"))
        return items

    def list_directory(self, payload):
        items = []
        for info in _payload_list(payload):
            if not isinstance(info, dict):
                continue
            list_id = _first_value(info, "id", "listId")
            if not list_id:
                continue
            title = _first_value(info, "name", "title") or "PunchPlay List"
            count = _first_value(info, "itemCount", "itemsCount", "count")
            label = "%s [I](x%s)[/I]" % (title, count) if count not in ("", None) else title
            summary_parts = []
            description = _first_value(info, "description", "summary")
            if description:
                summary_parts.append(str(description))
            external = _first_value(info, "externalSource")
            if external:
                summary_parts.append("[B]External Source:[/B] %s" % external)
            items.append({
                "type": "dir",
                "title": label,
                "link": "punchplay/list/%s" % quote(str(list_id), safe=""),
                "thumbnail": "resources/media/playlists.png",
                "summary": "[CR][CR]".join(summary_parts) if summary_parts else "PunchPlay list",
            })
        if not items:
            items.append(_message_item("PunchPlay Lists", "No PunchPlay lists were returned.", "resources/media/playlists.png"))
        return items

    def stats_items(self, payload):
        if not isinstance(payload, dict):
            return [_message_item("PunchPlay Community Stats", "No community stats were returned.")]
        lines = []
        for key in sorted(payload.keys()):
            value = payload.get(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value, sort_keys=True)[:1000]
            if value not in (None, ""):
                lines.append("[B]%s:[/B] %s" % (key, value))
        return [_message_item("PunchPlay Community Stats", "[CR]".join(lines) if lines else "No community stats were returned.")]
