"""
network.py — All HTTP/network helpers for Omega GUI Wizard.

Consolidates the fetch / cache / download logic that was scattered across
wizard.py, downloader.py, and apkscraper.py into a single, testable module.
"""

import os
import time
import xbmc
import xbmcvfs

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse

from . import config

# User-agent that mirrors what Kodi's built-in HTTP client sends
_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/122.0.0.0 Safari/537.36'
)
_TIMEOUT = 20  # seconds


def _log(msg: str, level: int = xbmc.LOGDEBUG) -> None:
    xbmc.log('[OmegaWiz/network] %s' % msg, level)


# ---------------------------------------------------------------------------
# Raw fetch
# ---------------------------------------------------------------------------
def fetch_url(url: str, as_bytes: bool = False, timeout: int = _TIMEOUT):
    """Return the body of *url* as str (default) or bytes.

    Returns None on any error so callers can do a simple ``if result:`` check.
    """
    if not url or url.startswith('https://') and len(url) < 10:
        return None
    try:
        req = Request(url, headers={'User-Agent': _UA})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return raw if as_bytes else raw.decode('utf-8', errors='replace')
    except (HTTPError, URLError) as exc:
        _log('fetch_url failed for %s — %s' % (url, exc), xbmc.LOGERROR)
        return None
    except Exception as exc:
        _log('fetch_url unexpected error for %s — %s' % (url, exc), xbmc.LOGERROR)
        return None


# ---------------------------------------------------------------------------
# Caching layer
# ---------------------------------------------------------------------------
def _cache_path(url: str) -> str:
    """Return a filesystem path under ADDONDATA_CACHE for the given URL."""
    safe = ''.join(c if c.isalnum() or c in '._-' else '_' for c in url)
    safe = safe[-180:]  # keep filename manageable
    return os.path.join(config.ADDONDATA_CACHE, safe + '.cache')


def text_cache(url: str, max_age_hours: int = None) -> str | None:
    """Fetch *url*, caching the result locally for *max_age_hours* hours.

    Falls back to cached copy if the network request fails (stale-if-error).
    Returns None when both live fetch and cache are unavailable.
    """
    if max_age_hours is None:
        max_age_hours = config.CACHEAGE

    os.makedirs(config.ADDONDATA_CACHE, exist_ok=True)
    cache_file = _cache_path(url)

    # Serve from cache if fresh enough
    if os.path.exists(cache_file):
        age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600
        if age_hours < max_age_hours:
            _log('Cache hit for %s (age %.1fh)' % (url, age_hours))
            try:
                with open(cache_file, 'r', encoding='utf-8') as fh:
                    return fh.read()
            except OSError:
                pass  # fall through to live fetch

    # Live fetch
    content = fetch_url(url)
    if content:
        try:
            with open(cache_file, 'w', encoding='utf-8') as fh:
                fh.write(content)
        except OSError as exc:
            _log('Could not write cache for %s — %s' % (url, exc), xbmc.LOGWARNING)
        return content

    # Stale-if-error: return whatever we have, even if expired
    if os.path.exists(cache_file):
        _log('Network error; serving stale cache for %s' % url, xbmc.LOGWARNING)
        try:
            with open(cache_file, 'r', encoding='utf-8') as fh:
                return fh.read()
        except OSError:
            pass

    return None


def bust_cache(url: str) -> None:
    """Delete the cached copy of *url*, forcing a live fetch next time."""
    cache_file = _cache_path(url)
    if os.path.exists(cache_file):
        try:
            os.remove(cache_file)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# URL health check (used by build_manager to find a live mirror)
# ---------------------------------------------------------------------------
def working_url(url_or_list) -> str | None:
    """Return the first URL from *url_or_list* that responds with HTTP 200.

    Accepts either a single URL string or a list of URL strings.
    """
    urls = [url_or_list] if isinstance(url_or_list, str) else list(url_or_list)
    for url in urls:
        if not url or url.rstrip('/') == 'http:':
            continue
        try:
            req = Request(url, headers={'User-Agent': _UA})
            with urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Streaming download with progress callback
# ---------------------------------------------------------------------------
def download_file(
    url: str,
    dest_path: str,
    callback=None,
    chunk_size: int = 512 * 1024,
) -> bool:
    """Download *url* to *dest_path*, calling *callback* with progress info.

    *callback(percent, label1, label2)* — same signature as
    ``xbmcgui.DialogProgress.update`` so InstallWindow and DialogProgress
    are interchangeable.

    Returns True on success, False on failure or user cancel.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    try:
        req = Request(url, headers={'User-Agent': _UA})
        with urlopen(req, timeout=_TIMEOUT) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            start = time.time()
            with open(dest_path, 'wb') as fh:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)

                    if callback is not None:
                        # Check for user cancel
                        if hasattr(callback, 'iscanceled') and callback.iscanceled():
                            _log('Download cancelled by user', xbmc.LOGINFO)
                            try:
                                os.remove(dest_path)
                            except OSError:
                                pass
                            return False

                        if total > 0:
                            pct = int(downloaded * 100 / total)
                            elapsed = max(time.time() - start, 0.001)
                            speed_mb = (downloaded / elapsed) / (1024 * 1024)
                            remaining = ((total - downloaded) / (downloaded / elapsed)) if downloaded else 0
                            mins, secs = divmod(int(remaining), 60)
                            line2 = '%.1f MB/s  —  ETA %02d:%02d' % (speed_mb, mins, secs)
                            callback.update(pct, 'Downloading…', line2)
                        else:
                            mb = downloaded / (1024 * 1024)
                            callback.update(0, 'Downloading…', '%.1f MB received' % mb)

        _log('Download complete: %s' % dest_path, xbmc.LOGINFO)
        return True

    except (HTTPError, URLError) as exc:
        _log('download_file failed: %s — %s' % (url, exc), xbmc.LOGERROR)
        try:
            os.remove(dest_path)
        except OSError:
            pass
        return False
    except Exception as exc:
        _log('download_file unexpected error: %s — %s' % (url, exc), xbmc.LOGERROR)
        try:
            os.remove(dest_path)
        except OSError:
            pass
        return False
