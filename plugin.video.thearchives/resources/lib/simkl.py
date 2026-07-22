import json

from ..DI import DI
from ..plugin import Plugin

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *


DEFAULT_BASE_URL = "https://api.simkl.com"
PIN_PATH = "/oauth/pin"
TEST_PATH = "/sync/activities"
API_TIMEOUT = 20


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

    def _request(self, method, path, params=None, payload=None, auth=True, action="calling Simkl"):
        response = self.session.request(
            method,
            self.base_url + path,
            params=self._app_params(params),
            data=json.dumps(payload) if payload is not None else None,
            headers=self._headers(auth=auth),
            timeout=API_TIMEOUT,
        )
        return self._json_or_error(response, action)

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
