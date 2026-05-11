"""
build_manager.py — Build list fetching, parsing, and update checking.

Replaces the ad-hoc parsing scattered across wizard.py so there is a single,
tested code path for every build-related operation.
"""

import re
import xbmc
import xbmcgui

from . import config
from .network import text_cache, fetch_url, bust_cache


def _log(msg: str, level: int = xbmc.LOGDEBUG) -> None:
    xbmc.log('[OmegaWiz/build_manager] %s' % msg, level)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _get_raw(url: str, force_refresh: bool = False) -> str | None:
    """Fetch the raw build-list text, optionally skipping the cache."""
    if force_refresh:
        bust_cache(url)
    return text_cache(url, max_age_hours=config.CACHEAGE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def parse_builds(url: str, force_refresh: bool = False) -> list[dict]:
    """Fetch and parse a wizard-format builds.txt from *url*.

    Each entry in the returned list is a dict with keys:
        name, version, url, icon, fanart, description, color (optional extra keys)

    Returns an empty list on failure so callers never have to handle None.
    """
    raw = _get_raw(url, force_refresh)
    if not raw:
        _log('Could not fetch build list from %s' % url, xbmc.LOGWARNING)
        return []

    builds = []
    current: dict | None = None

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Start of a new build block
        if line.startswith('<build>'):
            current = {
                'name': '', 'version': '0', 'url': '',
                'icon': config.ICON, 'fanart': config.FANART,
                'description': '', 'theme': '',
            }
        elif line.startswith('</build>') and current:
            if current.get('name'):
                builds.append(current)
            current = None
        elif current is not None:
            _parse_tag(line, current)

    if not builds:
        # Legacy flat-file format —  parse as key=value pairs per build
        builds = _parse_legacy(raw)

    _log('Parsed %d build(s) from %s' % (len(builds), url))
    return builds


def _parse_tag(line: str, dest: dict) -> None:
    """Extract a single <tag>value</tag> line into *dest*."""
    m = re.match(r'<(\w+)>(.*?)</\1>', line, re.DOTALL)
    if not m:
        return
    key, val = m.group(1).lower(), m.group(2).strip()
    if key in dest or key in ('name', 'version', 'url', 'icon', 'fanart', 'description', 'theme', 'color'):
        dest[key] = val


def _parse_legacy(raw: str) -> list[dict]:
    """Parse the older key=value repeated-block format.

    Expected pattern::

        Build Name
        version=1.0
        url=https://...
        icon=https://...
        fanart=https://...

    Blocks are separated by blank lines (or the start of the next build name).
    """
    builds = []
    block: dict = {}
    keys = {'version', 'url', 'icon', 'fanart', 'description', 'theme'}

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            if block.get('name'):
                builds.append(block)
            block = {}
            continue
        if '=' in line:
            k, _, v = line.partition('=')
            k = k.strip().lower()
            if k in keys:
                block[k] = v.strip()
        else:
            # Non-key lines are treated as the build name
            if block.get('name') and block.get('url'):
                builds.append(block)
            block = {
                'name': line,
                'version': '0',
                'url': '',
                'icon': config.ICON,
                'fanart': config.FANART,
                'description': '',
                'theme': '',
            }

    if block.get('name') and block.get('url'):
        builds.append(block)

    return builds


def get_build(url: str, name: str, force_refresh: bool = False) -> dict | None:
    """Return the single build entry matching *name*, or None if not found."""
    for b in parse_builds(url, force_refresh):
        if b.get('name', '').strip().lower() == name.strip().lower():
            return b
    return None


# ---------------------------------------------------------------------------
# Update check
# ---------------------------------------------------------------------------
def check_build_update(current_name: str, current_version: str) -> dict | None:
    """Compare the locally-installed build version against the remote list.

    Returns a dict (the remote entry) if an update is available, or None.
    *current_version* is compared as a simple string; a different (typically
    higher) remote version is considered an update.
    """
    if not current_name or current_name == 'No Build Installed':
        return None

    remote = get_build(config.BUILDFILE, current_name, force_refresh=False)
    if not remote:
        _log('check_build_update: %r not found in remote list' % current_name, xbmc.LOGINFO)
        return None

    remote_ver = remote.get('version', '0')
    if remote_ver != current_version:
        _log('Update available for %r: %s → %s' % (current_name, current_version, remote_ver), xbmc.LOGINFO)
        return remote

    _log('%r is up to date (version %s)' % (current_name, current_version))
    return None


# ---------------------------------------------------------------------------
# Convenience: installed build info (reads addon settings)
# ---------------------------------------------------------------------------
def installed_build_name() -> str:
    import xbmcaddon
    return xbmcaddon.Addon(config.ADDON_ID).getSetting('buildname') or 'No Build Installed'


def installed_build_version() -> str:
    import xbmcaddon
    return xbmcaddon.Addon(config.ADDON_ID).getSetting('buildversion') or '0'
