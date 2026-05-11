"""
addon_manager.py — Addon installation, enable/disable, and skin-swapping.

Replaces the JSON-RPC calls that were duplicated in wizard.py, skinSwitch.py,
and addons_enable.py with a single, clean interface.
"""

import os
import time
import xbmc
import xbmcaddon
import xbmcgui

from . import config


def _log(msg: str, level: int = xbmc.LOGDEBUG) -> None:
    xbmc.log('[OmegaWiz/addon_manager] %s' % msg, level)


def _json(method: str, params: dict):
    """Execute a Kodi JSON-RPC call and return the parsed result dict (or {})."""
    import json
    payload = json.dumps({'jsonrpc': '2.0', 'method': method, 'params': params, 'id': 1})
    raw = xbmc.executeJSONRPC(payload)
    try:
        return json.loads(raw)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------
def is_installed(addon_id: str) -> bool:
    """Return True if the addon is present in the Kodi addon database."""
    resp = _json('Addons.GetAddonDetails', {'addonid': addon_id, 'properties': ['enabled']})
    return 'error' not in resp and 'result' in resp


def is_enabled(addon_id: str) -> bool:
    """Return True if the addon is installed *and* enabled."""
    resp = _json('Addons.GetAddonDetails', {'addonid': addon_id, 'properties': ['enabled']})
    if 'error' in resp or 'result' not in resp:
        return False
    return resp['result'].get('addon', {}).get('enabled', False)


def addon_version(addon_id: str) -> str | None:
    """Return the installed version string, or None if not installed."""
    resp = _json('Addons.GetAddonDetails', {'addonid': addon_id, 'properties': ['version']})
    if 'error' in resp or 'result' not in resp:
        return None
    return resp['result'].get('addon', {}).get('version')


# ---------------------------------------------------------------------------
# Enable / disable
# ---------------------------------------------------------------------------
def set_addon_enabled(addon_id: str, enable: bool = True) -> bool:
    """Enable or disable *addon_id*.  Returns True on success."""
    resp = _json('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': enable})
    ok = 'error' not in resp
    _log('%s %r: %s' % ('Enabled' if enable else 'Disabled', addon_id, 'OK' if ok else 'FAILED'))
    return ok


def enable_all_installed(addon_ids: list[str]) -> None:
    """Enable every addon in *addon_ids* that is installed.  Skips missing ones."""
    for aid in addon_ids:
        if is_installed(aid):
            set_addon_enabled(aid, True)


# ---------------------------------------------------------------------------
# Unknown sources
# ---------------------------------------------------------------------------
def enable_unknown_sources() -> None:
    """Ensure 'Allow unknown sources' is on (required for sideloaded addons)."""
    resp = _json('Settings.GetSettingValue', {'setting': 'general.addonforeignfilter'})
    # On Kodi 20+ the setting key changed to general.addonforeignfilter
    # Fallback: use executebuiltin toggle
    current = resp.get('result', {}).get('value')
    if current is False:
        _json('Settings.SetSettingValue', {'setting': 'general.addonforeignfilter', 'value': True})
        _log('Unknown sources enabled via JSON-RPC', xbmc.LOGINFO)
    else:
        # Kodi 18/19 path
        xbmc.executebuiltin('Addon.default.OpenSettings(xbmc.addon.settings)')


# ---------------------------------------------------------------------------
# Skin switching
# ---------------------------------------------------------------------------
def current_skin() -> str:
    """Return the addon ID of the currently active skin."""
    return xbmc.getSkinDir()


def swap_skin(target_skin_id: str, timeout: int = 15) -> bool:
    """Switch to *target_skin_id* and wait until it is active.

    Returns True if the skin was successfully swapped within *timeout* seconds.
    NOTE: Kodi shows a confirmation dialog when switching skins; this function
    auto-confirms it by sending a click to the YES button.
    """
    if current_skin() == target_skin_id:
        _log('Skin %r already active' % target_skin_id)
        return True

    _log('Swapping skin to %r' % target_skin_id, xbmc.LOGINFO)
    xbmc.executebuiltin('ActivateAddon(%s)' % target_skin_id)

    deadline = time.time() + timeout
    while time.time() < deadline:
        xbmc.sleep(200)
        # Dismiss the "Keep this skin?" yes/no dialog if it appears
        if xbmc.getCondVisibility('Window.IsVisible(yesnodialog)'):
            xbmc.executebuiltin('SendClick(11)')  # button ID 11 = "Yes"
            xbmc.sleep(200)
        if current_skin() == target_skin_id:
            _log('Skin swap to %r complete' % target_skin_id, xbmc.LOGINFO)
            return True

    _log('Skin swap to %r timed out after %ds' % (target_skin_id, timeout), xbmc.LOGWARNING)
    return False


# ---------------------------------------------------------------------------
# Install from ZIP
# ---------------------------------------------------------------------------
def install_addon_from_zip(zip_path: str) -> bool:
    """Install an addon from a local ZIP file using Kodi's built-in installer.

    Returns True immediately (result is async; caller should check is_installed
    after a brief delay if confirmation is needed).
    """
    if not os.path.exists(zip_path):
        _log('install_addon_from_zip: file not found — %s' % zip_path, xbmc.LOGERROR)
        return False
    xbmc.executebuiltin('InstallAddon(%s)' % zip_path)
    return True


# ---------------------------------------------------------------------------
# Repo install helper (used by wizard flow and community.py)
# ---------------------------------------------------------------------------
def install_repo(repo_zip_url: str, repo_id: str, packages_dir: str = None) -> bool:
    """Download and install a repository ZIP identified by *repo_id*.

    Returns True if the repo ends up installed after the operation.
    """
    from .network import download_file

    if packages_dir is None:
        packages_dir = config.PACKAGES
    os.makedirs(packages_dir, exist_ok=True)

    filename = '%s.zip' % repo_id
    dest = os.path.join(packages_dir, filename)
    _log('Downloading repo zip from %s' % repo_zip_url, xbmc.LOGINFO)
    ok = download_file(repo_zip_url, dest)
    if not ok:
        return False

    xbmc.executebuiltin('InstallAddon(%s)' % dest)
    # Wait up to 10 s for Kodi to finish installing
    deadline = time.time() + 10
    while time.time() < deadline:
        xbmc.sleep(500)
        if is_installed(repo_id):
            _log('Repo %r installed successfully' % repo_id, xbmc.LOGINFO)
            return True

    _log('Repo %r install timed out' % repo_id, xbmc.LOGWARNING)
    return is_installed(repo_id)
