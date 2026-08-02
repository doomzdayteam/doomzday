import json
import time

from ..DI import DI
from ..plugin import Plugin

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *


DEFAULT_BASE_URL = "https://api.wetrakr.com"
API_TIMEOUT = 20


class WeTrakrAPIError(Exception):
    def __init__(self, status_code, message, payload=None):
        self.status_code = status_code
        self.payload = payload or {}
        Exception.__init__(self, message or "Unknown WeTrakr API error")


def _setting(setting_id, default=""):
    value = xbmcaddon.Addon().getSetting(setting_id)
    return value if value not in (None, "") else default


def _set_setting(setting_id, value):
    xbmcaddon.Addon().setSetting(setting_id, "" if value is None else str(value))


def _token_value(payload):
    if not isinstance(payload, dict):
        return ""
    for key in ("access_token", "accessToken", "api_token", "apiToken", "token", "webhook_token", "webhookToken", "kodi_token", "kodiToken"):
        value = payload.get(key)
        if value:
            return str(value)
    for key in ("auth", "data", "result"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            value = _token_value(nested)
            if value:
                return value
    return ""


def _auth_error_key(value):
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def build_wetrakr_qr_image_url(device_code, size=800):
    try:
        from resources.lib.util.tmdb_qr import build_qr_image_url
    except ImportError:
        from ..util.tmdb_qr import build_qr_image_url
    verification_url = device_code.get("verification_url") or device_code.get("verification_uri") or "https://wetrakr.com/activate"
    return build_qr_image_url(verification_url, size=size)


def _poll_wetrakr_auth(dialog, api, device_code):
    interval = int(device_code.get("interval") or 5)
    expires_in = int(device_code.get("expires_in") or 600)
    elapsed = 0
    code = device_code.get("device_code") or ""
    while not dialog.cancelled and elapsed < expires_in and dialog.response is None:
        xbmc.sleep(interval * 1000)
        elapsed += interval
        try:
            token = api.device_token(code)
            if _token_value(token):
                dialog.response = token
                dialog.close()
                return
            error = str(token.get("error") or "").lower()
            if error in ("authorization_pending", "pending", "slow_down", ""):
                continue
            dialog.error = WeTrakrAPIError(0, token.get("message") or token.get("error") or "WeTrakr authorization failed.", token)
            dialog.close()
            return
        except WeTrakrAPIError as e:
            pending_value = str(e.payload.get("error") or e.payload.get("message") or "").lower()
            if pending_value in ("authorization_pending", "pending", "slow_down"):
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


def _show_wetrakr_qr_auth_window(api, device_code):
    class WeTrakrQRAuthDialog(xbmcgui.WindowXMLDialog):
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

    verification_url = device_code.get("verification_url") or device_code.get("verification_uri") or "https://wetrakr.com/activate"
    interval = int(device_code.get("interval") or 5)
    expires_in = int(device_code.get("expires_in") or 600)
    code = device_code.get("device_code") or ""
    dialog = WeTrakrQRAuthDialog("wetrakr_auth_qr.xml", PATH, "Default", "1080i")
    dialog.setProperty("wetrakr.title", "WeTrakr Account Authorization")
    dialog.setProperty("wetrakr.qr_url", build_wetrakr_qr_image_url(device_code, size=800))
    dialog.setProperty("wetrakr.auth_url", verification_url)
    dialog.setProperty("wetrakr.user_code", device_code.get("user_code") or device_code.get("code") or "")
    dialog.show()
    deadline = time.time() + expires_in
    monitor = xbmc.Monitor()
    result = None
    try:
        while time.time() < deadline and not monitor.abortRequested() and not dialog.cancelled:
            try:
                token = api.device_token(code)
            except WeTrakrAPIError as e:
                pending_value = _auth_error_key(e.payload.get("error") or e.payload.get("message"))
                if pending_value in ("authorization_pending", "pending", "slow_down"):
                    token = None
                else:
                    raise
            if token:
                if _token_value(token):
                    result = token
                    break
                error = _auth_error_key(token.get("error") or token.get("message"))
                if error in ("authorization_pending", "pending", "slow_down", ""):
                    pass
                elif error == "expired_token":
                    break
                else:
                    raise WeTrakrAPIError(0, token.get("message") or token.get("error") or "WeTrakr authorization failed.", token)
            if monitor.waitForAbort(interval):
                break
        return result
    finally:
        try:
            dialog.close()
        except Exception:
            pass


class WeTrakr(Plugin):
    name = "wetrakr"

    def get_list(self, url):
        if not str(url or "").startswith("wetrakr"):
            return False
        return json.dumps({"items": []})

    def _clear_auth_settings(self):
        _set_setting("wetrakr.access_token", "")
        _set_setting("wetrakr.username", "")
        _set_setting("wetrakr.auth_invalid", "false")

    def _account_label(self):
        return _setting("wetrakr.username") or "authorized account"

    def _auth(self):
        api = WeTrakrAPI()
        try:
            device_code = api.device_code()
            token = _show_wetrakr_qr_auth_window(api, device_code)
            if not token:
                xbmcgui.Dialog().ok("WeTrakr Authorization", "WeTrakr authorization timed out or was cancelled.")
                return False
            access_token = _token_value(token)
            if not access_token:
                raise WeTrakrAPIError(0, "WeTrakr authorized the account but did not return a usable Kodi token.", token)
            _set_setting("wetrakr.access_token", access_token)
            _set_setting("wetrakr.username", token.get("username") or token.get("user_name") or token.get("name") or "")
            _set_setting("wetrakr.auth_invalid", "false")
            xbmcgui.Dialog().notification("WeTrakr", "Device authorization was successful!", xbmcgui.NOTIFICATION_INFO)
            return True
        except Exception as e:
            xbmc.log("[TheArchives][WeTrakr] Authorization failed: %s" % e, xbmc.LOGERROR)
            self._clear_auth_settings()
            xbmcgui.Dialog().ok("WeTrakr Authorization Failed", str(e))
            return False

    def _test_connection(self):
        api = WeTrakrAPI()
        if not api.access_token:
            xbmcgui.Dialog().ok("WeTrakr", "WeTrakr is not authorized.")
            return False
        xbmcgui.Dialog().ok(
            "WeTrakr",
            "WeTrakr is paired as %s.\n\nKodi pairing creates a scrobble token. "
            "The website profile, list, favorites, next-to-watch, stats, and social pages are not listed because WeTrakr does not expose a stable Kodi browse API for them yet." % self._account_label(),
        )
        return True

    def routes(self, plugin):
        @plugin.route("/wetrakr/authorize")
        def auth():
            self._auth()

        @plugin.route("/wetrakr/clear")
        def clear():
            if xbmcgui.Dialog().yesno(
                "Revoke WeTrakr Authorization",
                "Are you sure you want to revoke the WeTrakr authorization?",
            ):
                self._clear_auth_settings()
                xbmcgui.Dialog().notification("WeTrakr", "Authorization revoked", xbmcgui.NOTIFICATION_INFO)

        @plugin.route("/wetrakr/test")
        def test():
            self._test_connection()


class WeTrakrAPI:
    session = DI.session

    def __init__(self):
        self.base_url = (_setting("wetrakr.backend_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.access_token = (_setting("wetrakr.access_token") or "").strip()

    def _headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "plugin.video.thearchives WeTrakr",
        }

    def _request_response(self, method, path, data=None, action="calling WeTrakr"):
        response = self.session.request(
            method,
            self.base_url + path,
            data=json.dumps(data or {}) if data is not None else None,
            headers=self._headers(),
            timeout=API_TIMEOUT,
        )
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
            message = "WeTrakr returned HTTP %s while %s. %s" % (response.status_code, action, body[:200])
        raise WeTrakrAPIError(response.status_code, message, payload)

    def device_code(self):
        return self._request_response(
            "POST",
            "/oauth/device/code",
            data={},
            action="starting device authorization",
        )

    def device_token(self, device_code):
        return self._request_response(
            "POST",
            "/oauth/device/token",
            data={"device_code": device_code},
            action="polling device authorization",
        )
