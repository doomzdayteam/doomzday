from ..plugin import Plugin
from ..DI import DI
import urllib.request
import xbmc


HTTP_HEADERS = {
    "User-Agent": "TheArchives/1.0",
    "Accept": "application/json, application/xml, text/xml, text/plain, text/html, */*",
}


def _fetch_http_text(url):
    try:
        response = DI.session.get(url, headers=HTTP_HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except Exception as requests_error:
        try:
            request = urllib.request.Request(url, headers=HTTP_HEADERS)
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.read().decode("utf-8", "replace")
        except Exception as urllib_error:
            xbmc.log(
                f"TheArchives HTTP list fetch failed for {url}: requests={requests_error}; urllib={urllib_error}",
                xbmc.LOGERROR,
            )
            return False


class http(Plugin):
    name = "http"
    priority = 0

    def get_list(self, url):
        if url.startswith("http"):
            return _fetch_http_text(url)
