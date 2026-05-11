"""
config.py — Centralised runtime constants for Omega GUI Wizard.

Every new module imports from here instead of duplicating the path/constant
setup that used to be spread across wizard.py, traktit.py, debridit.py, etc.
Existing code that imports wizard.py directly is unaffected; wizard.py still
re-exposes the same names for backward compatibility.
"""

import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import uservar

# ---------------------------------------------------------------------------
# Addon identity
# ---------------------------------------------------------------------------
ADDON_ID    = uservar.ADDON_ID
ADDON       = xbmcaddon.Addon(ADDON_ID)
ADDONTITLE  = uservar.ADDONTITLE
VERSION     = ADDON.getAddonInfo('version')
ADDONPATH   = ADDON.getAddonInfo('path')

# ---------------------------------------------------------------------------
# Kodi special:// paths — computed once at import
# ---------------------------------------------------------------------------
HOME         = xbmcvfs.translatePath('special://home/')
XBMCROOT     = xbmcvfs.translatePath('special://xbmc/')
LOGPATH      = xbmcvfs.translatePath('special://logpath/')
PROFILE      = xbmcvfs.translatePath('special://profile/')
TEMPDIR      = xbmcvfs.translatePath('special://temp/')
DATABASE_DIR = xbmcvfs.translatePath('special://database/')

# ---------------------------------------------------------------------------
# Derived paths
# ---------------------------------------------------------------------------
ADDONS           = os.path.join(HOME, 'addons')
USERDATA         = os.path.join(HOME, 'userdata')
PLUGIN_DIR       = os.path.join(ADDONS, ADDON_ID)
PACKAGES         = os.path.join(ADDONS, 'packages')
ADDON_DATA_ROOT  = os.path.join(USERDATA, 'addon_data')
ADDONDATA        = os.path.join(ADDON_DATA_ROOT, ADDON_ID)
DATABASE         = os.path.join(USERDATA, 'Database')
ADVANCED         = os.path.join(USERDATA, 'advancedsettings.xml')
SOURCES          = os.path.join(USERDATA, 'sources.xml')
FAVOURITES       = os.path.join(USERDATA, 'favourites.xml')
PROFILES         = os.path.join(USERDATA, 'profiles.xml')
GUISETTINGS      = os.path.join(USERDATA, 'guisettings.xml')
THUMBS           = os.path.join(USERDATA, 'Thumbnails')

FANART           = os.path.join(ADDONPATH, 'fanart.jpg')
ICON             = os.path.join(ADDONPATH, 'icon.png')
ART              = os.path.join(ADDONPATH, 'resources', 'art')
ADVANCEDSETTINGS_FOLDER = os.path.join(ADDONPATH, 'resources', 'advancedsettings')

ADDONDATA_CACHE  = os.path.join(ADDONDATA, 'Cache')
WIZLOG           = os.path.join(ADDONDATA, 'wizard.log')
WHITELIST        = os.path.join(ADDONDATA, 'whitelist.txt')
QRCODES          = os.path.join(ADDONDATA, 'QRCodes')
_raw_backup_dir  = getattr(uservar, 'BACKUPDIR', 'special://home/')
BACKUPDIR        = xbmcvfs.translatePath(_raw_backup_dir) if _raw_backup_dir.startswith('special://') else _raw_backup_dir
CREDS_BACKUP     = os.path.join(BACKUPDIR, 'OmegaWizardCreds') if BACKUPDIR else os.path.join(ADDONDATA, 'CredBackups')
BACKUP_KEEP      = int(getattr(uservar, 'BACKUP_KEEP', 3))

# ---------------------------------------------------------------------------
# Shared dialog objects
# ---------------------------------------------------------------------------
DIALOG = xbmcgui.Dialog()
DP     = xbmcgui.DialogProgress()

# ---------------------------------------------------------------------------
# uservar tunables — exposed so new modules only import config, not uservar
# ---------------------------------------------------------------------------
EXCLUDES       = uservar.EXCLUDES
BUILDFILE      = uservar.BUILDFILE
CACHETEXT      = uservar.CACHETEXT
CACHEAGE       = int(uservar.CACHEAGE) if str(uservar.CACHEAGE).isdigit() else 30
UPDATECHECK    = getattr(uservar, 'UPDATECHECK', 0)
NOTIFICATION   = getattr(uservar, 'NOTIFICATION', 'https://')
ENABLE         = getattr(uservar, 'ENABLE', 'No')
HEADERMESSAGE  = getattr(uservar, 'HEADERMESSAGE', '')
CONTACT        = getattr(uservar, 'CONTACT', '')
BUILDERNAME    = getattr(uservar, 'BUILDERNAME', '')

# Credential addon ID lists (config-driven — edit in uservar.py)
TRAKT_ADDON_IDS  = getattr(uservar, 'TRAKT_ADDON_IDS', ['script.trakt'])
DEBRID_ADDON_IDS = getattr(uservar, 'DEBRID_ADDON_IDS', [
    'script.module.resolveurl',
    'script.module.a4kresolver',
])
APK_EXTRA_SOURCES = getattr(uservar, 'APK_EXTRA_SOURCES', [])

# Colour constants
COLOR1 = uservar.COLOR1
COLOR2 = uservar.COLOR2
COLOR3 = uservar.COLOR3
COLOR4 = uservar.COLOR4
COLOR5 = getattr(uservar, 'COLOR5', 'lime')

# Log files to skip during extraction (never overwrite these)
LOGFILES = [
    'xbmc.log', 'xbmc.old.log', 'kodi.log', 'kodi.old.log',
    'spmc.log', 'spmc.old.log', 'tvmc.log', 'tvmc.old.log',
    'firemc.log', 'firemc.old.log', 'Thumbs.db', '.gitignore', '.DS_Store',
]
# Corrupt/stale cache DBs that should always be removed on install
BAD_FILES = [
    'onechannelcache.db', 'saltscache.db', 'saltscache.db-shm',
    'saltscache.db-wal', 'saltshd.lite.db', 'saltshd.lite.db-shm',
    'saltshd.lite.db-wal', 'queue.db', 'commoncache.db', 'access.log',
    'trakt.db', 'video_cache.db',
]
