"""
system_info.py — Hardware and Kodi version detection for Omega GUI Wizard.

Provides a single clean API so the rest of the addon never has to call
xbmc.getInfoLabel directly for version/platform data.
"""

import platform
import xbmc
import xbmcvfs


def _log(msg: str, level: int = xbmc.LOGDEBUG) -> None:
    xbmc.log('[OmegaWiz/system_info] %s' % msg, level)


# ---------------------------------------------------------------------------
# Kodi version
# ---------------------------------------------------------------------------
def get_kodi_version() -> dict:
    """Return a dict with keys: major, minor, build, tag, codename, display.

    Codenames cover every official Kodi release through 22 (Pliers) and mark
    any future release as 'Unknown' rather than returning a stale name.
    """
    raw = xbmc.getInfoLabel('System.BuildVersion')            # e.g. "20.1.3 (Nexus)"
    version_str = raw.split()[0] if raw else '0.0.0'
    parts = version_str.split('.')
    major = int(parts[0]) if parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    build = parts[2] if len(parts) > 2 else '0'

    _CODENAMES = {
        0:  'Pre-Release',
        1:  'Babylon',
        2:  'Camelot',
        3:  'Dharma',
        4:  'Eden',
        5:  'Frodo',
        6:  'Gotham',
        7:  'Helix',
        8:  'Isengard',
        9:  'Jarvis',
        10: 'Krypton',
        11: 'Leia',
        12: 'Matrix',
        13: 'Nexus',      # NOTE: Kodi 19 was "Matrix"; 20 is "Nexus"
        14: 'Omega',
        # --- keep the correct major→codename mapping below ---
    }
    # Override with the accurate major-version map
    _CORRECT = {
        18: 'Leia',
        19: 'Matrix',
        20: 'Nexus',
        21: 'Omega',
        22: 'Pliers',
    }
    codename = _CORRECT.get(major, _CODENAMES.get(major, 'Unknown (%d)' % major))

    display = '%d.%d.%s (%s)' % (major, minor, build, codename)
    _log('Kodi version detected: %s' % display)
    return {
        'major':    major,
        'minor':    minor,
        'build':    build,
        'codename': codename,
        'display':  display,
        'raw':      raw,
    }


def kodi_version_major() -> int:
    """Convenience — return the Kodi major version number as int."""
    return get_kodi_version()['major']


# ---------------------------------------------------------------------------
# Platform / OS
# ---------------------------------------------------------------------------
def get_platform() -> dict:
    """Return a dict describing the host OS and architecture.

    Keys: os_name, arch, is_android, is_windows, is_linux, is_osx, is_ios,
          is_arm, is_arm64, is_x86, is_x64, display.
    """
    os_name  = xbmc.getInfoLabel('System.OSVersionInfo') or platform.system()
    raw_arch = platform.machine().lower()

    is_android = xbmc.getCondVisibility('System.Platform.Android')
    is_windows = xbmc.getCondVisibility('System.Platform.Windows')
    is_linux   = xbmc.getCondVisibility('System.Platform.Linux') and not is_android
    is_osx     = xbmc.getCondVisibility('System.Platform.OSX')
    is_ios     = xbmc.getCondVisibility('System.Platform.IOS')

    is_arm64 = 'aarch64' in raw_arch or 'arm64' in raw_arch
    is_arm   = ('arm' in raw_arch or 'armv7' in raw_arch) and not is_arm64
    is_x64   = 'x86_64' in raw_arch or 'amd64' in raw_arch
    is_x86   = ('x86' in raw_arch or 'i686' in raw_arch) and not is_x64

    if is_android:
        plat = 'Android'
    elif is_windows:
        plat = 'Windows'
    elif is_osx:
        plat = 'macOS'
    elif is_ios:
        plat = 'iOS'
    elif is_linux:
        plat = 'Linux'
    else:
        plat = platform.system() or 'Unknown'

    display = '%s  %s' % (plat, raw_arch)
    result = {
        'os_name':    os_name,
        'arch':       raw_arch,
        'platform':   plat,
        'is_android': bool(is_android),
        'is_windows': bool(is_windows),
        'is_linux':   bool(is_linux),
        'is_osx':     bool(is_osx),
        'is_ios':     bool(is_ios),
        'is_arm':     is_arm,
        'is_arm64':   is_arm64,
        'is_x86':     is_x86,
        'is_x64':     is_x64,
        'display':    display,
    }
    _log('Platform: %s' % display)
    return result


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
def get_storage_info() -> dict:
    """Return total / free / used bytes and a human-readable display string.

    Uses Kodi's System info labels where available; falls back to shutil on
    desktop platforms.  Returns zeroes if detection fails.
    """
    # Kodi info labels give values in MB as strings like "12345 MB"
    def _parse_mb(label_name):
        val = xbmc.getInfoLabel(label_name)
        try:
            return int(val.split()[0]) * 1024 * 1024
        except Exception:
            return 0

    total = _parse_mb('System.TotalSpace')
    free  = _parse_mb('System.FreeSpace')

    if not total:
        try:
            import shutil
            st = shutil.disk_usage(xbmcvfs.translatePath('special://home/'))
            total, used, free = st.total, st.used, st.free
        except Exception:
            total = used = free = 0

    used = total - free if total else 0

    def _fmt(b):
        if b >= 1 << 30:
            return '%.1f GB' % (b / (1 << 30))
        return '%.0f MB' % (b / (1 << 20))

    display = 'Total: %s  Free: %s  Used: %s' % (_fmt(total), _fmt(free), _fmt(used))
    return {'total': total, 'free': free, 'used': used, 'display': display}
