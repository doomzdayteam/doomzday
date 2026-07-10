import json
import time
import uuid

from ..DI import DI
from ..plugin import Plugin

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *


DEFAULT_BASE_URL = "https://punchplay.tv"
DEFAULT_SCOPE = "profile:read playback:read playback:write events:read"
DEVICE_CODE_PATH = "/api/platform/v1/auth/device/code"
DEVICE_TOKEN_PATH = "/api/platform/v1/auth/device/token"
REFRESH_PATH = "/api/platform/v1/auth/refresh"
ME_PATH = "/api/platform/v1/me"
PLAYBACK_PATH = "/api/platform/v1/playback/%s"


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
        self.scope = _setting("punchplay.scope", DEFAULT_SCOPE)
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

    def _request(self, method, path, payload=None, auth=True, retry_on_401=True):
        response = self.session.request(
            method,
            self.base_url + path,
            data=json.dumps(payload) if payload is not None else None,
            headers=self._headers(auth=auth),
            timeout=20,
        )
        if response.status_code == 401 and auth and retry_on_401 and self.refresh_token:
            if self.refresh_access_token():
                return self._request(method, path, payload, auth=auth, retry_on_401=False)
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
