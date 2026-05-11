"""
maintenance.py — Cache clearing, fresh start, and advanced-settings helpers.

All imports now reference real modules in this package.  The old imports from
non-existent modules (addonvar, save_data, utils) have been removed and
replaced with references to config.py and data_manager.py.
"""

import os
import shutil
import sqlite3
import xbmc
import xbmcgui

from . import config
from .addon_manager import current_skin, swap_skin
from .data_manager import backup_credentials, restore_credentials


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _log(msg, level=xbmc.LOGDEBUG):
    xbmc.log('[OmegaWiz/maintenance] %s' % msg, level)


def _dialog():
    return xbmcgui.Dialog()


def _dp():
    return xbmcgui.DialogProgress()


# ---------------------------------------------------------------------------
# Database purging
# ---------------------------------------------------------------------------
def purge_db(db):
    """Delete all rows from every non-version table in the SQLite DB at *db*."""
    if not os.path.exists(db):
        _log('%s not found.' % db, xbmc.LOGINFO)
        return False

    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
    except Exception as exc:
        _log('DB connection error: %s — %s' % (db, exc), xbmc.LOGERROR)
        return False

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for (table,) in cur.fetchall():
        if table == 'version':
            continue
        try:
            cur.execute('DELETE FROM %s' % table)
            conn.commit()
            _log('Cleared table `%s` in %s' % (table, os.path.basename(db)))
        except Exception as exc:
            _log('Error clearing table `%s`: %s' % (table, exc), xbmc.LOGERROR)

    conn.close()
    _log('DB purge complete: %s' % db, xbmc.LOGINFO)
    return True


# ---------------------------------------------------------------------------
# Thumbnail clearing
# ---------------------------------------------------------------------------
def clear_thumbnails():
    thumbs = config.THUMBS
    try:
        if os.path.isdir(thumbs):
            shutil.rmtree(thumbs)
    except Exception as exc:
        _log('Failed to delete Thumbnails: %s' % exc, xbmc.LOGWARNING)
        return

    textures_db = os.path.join(config.DATABASE, 'Textures13.db')
    if os.path.exists(textures_db):
        try:
            os.remove(textures_db)
        except OSError:
            purge_db(textures_db)

    xbmc.sleep(1000)
    _dialog().ok(config.ADDONTITLE, 'Thumbnails have been deleted.')


# ---------------------------------------------------------------------------
# Advanced settings
# ---------------------------------------------------------------------------
_RAM_OPTIONS = [
    ('Less than 1 GB  (1st-3rd gen FireStick, Lite)', 'less1.xml'),
    ('1 GB - 1.5 GB  (4K FireStick)',                 '1plus.xml'),
    ('1.5 GB - 2 GB  (FireBox / Cube / Shield Tube)', 'firetv.xml'),
    ('2 GB - 3 GB  (general mid-range)',              '2plus.xml'),
    ('3 GB or more  (Nvidia Shield Pro)',             'shield.xml'),
    ('-- Delete advanced settings --',               None),
]


def advanced_settings():
    """Show a RAM-tier picker and write (or delete) advancedsettings.xml."""
    labels = [r[0] for r in _RAM_OPTIONS]
    selection = _dialog().select('Select RAM Tier', labels)

    if selection < 0:
        return

    _, xml_name = _RAM_OPTIONS[selection]
    advsrc = config.ADVANCED
    advsrc_folder = config.ADVANCEDSETTINGS_FOLDER

    if os.path.exists(advsrc):
        try:
            os.remove(advsrc)
        except OSError as exc:
            _log('Could not remove existing advancedsettings.xml: %s' % exc, xbmc.LOGERROR)

    if xml_name is None:
        xbmc.sleep(500)
        _dialog().ok(config.ADDONTITLE, 'Advanced Settings have been deleted.')
    else:
        src = os.path.join(advsrc_folder, xml_name)
        if not os.path.exists(src):
            _dialog().ok(config.ADDONTITLE, 'Template file not found:\n%s' % src)
            return
        shutil.copyfile(src, advsrc)
        xbmc.sleep(500)
        _dialog().ok(config.ADDONTITLE, 'Advanced Settings have been applied.\nKodi will restart to take effect.')

    xbmc.executebuiltin('RestartApp()')


# ---------------------------------------------------------------------------
# Fresh start
# ---------------------------------------------------------------------------
def fresh_start(standalone=False):
    """Wipe Kodi home (except wizard addon) and restore credentials."""
    dlg = _dialog()

    confirmed = dlg.yesno(
        config.ADDONTITLE,
        'This will delete your entire Kodi configuration and start fresh.\n'
        'Your build settings and saved credentials will be preserved.\n\n'
        'Are you sure?',
        nolabel='Cancel',
        yeslabel='Fresh Start',
    )
    if not confirmed:
        return

    if current_skin() not in ('skin.estuary', 'skin.estuary.mono'):
        if not swap_skin('skin.estuary'):
            _log('Fresh Start: skin swap failed — aborting', xbmc.LOGWARNING)
            return

    if standalone:
        backup_credentials()

    dp = _dp()
    dp.create(config.ADDONTITLE, 'Fresh Start — deleting files...')

    try:
        xbmc.sleep(100)
        dp.update(20, 'Removing files...')
        _delete_files(config.HOME, config.EXCLUDES)

        dp.update(60, 'Removing stale folders...')
        _delete_dirs(config.HOME, config.EXCLUDES)

        dp.update(80, 'Recreating packages folder...')
        os.makedirs(config.PACKAGES, exist_ok=True)

        dp.update(100, 'Complete.')
        xbmc.sleep(1000)
    finally:
        dp.close()

    if standalone:
        restore_credentials()
        import xbmcaddon
        addon = xbmcaddon.Addon(config.ADDON_ID)
        addon.setSetting('firstrun', 'true')
        addon.setSetting('buildname', 'No Build Installed')
        addon.setSetting('buildversion', '0')
        dlg.ok(config.ADDONTITLE, 'Fresh Start is complete.\nKodi will now restart.')
        xbmc.executebuiltin('RestartApp()')


def _delete_files(root, excludes):
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in excludes]
        for name in filenames:
            if name in excludes:
                continue
            path = os.path.join(dirpath, name)
            try:
                os.remove(path)
            except Exception as exc:
                _log('Could not delete %s: %s' % (path, exc), xbmc.LOGWARNING)


def _delete_dirs(root, excludes):
    _safe_dirs = {'addons', 'userdata', 'Database', 'addon_data', 'backups', 'temp'}
    for dirpath, dirnames, _ in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in excludes]
        for name in dirnames:
            if name in _safe_dirs or name in excludes:
                continue
            path = os.path.join(dirpath, name)
            try:
                shutil.rmtree(path, ignore_errors=True)
            except Exception as exc:
                _log('Could not remove dir %s: %s' % (path, exc), xbmc.LOGWARNING)


# ---------------------------------------------------------------------------
# Package cache
# ---------------------------------------------------------------------------
def clear_packages():
    """Delete all files and folders inside the Kodi packages directory."""
    packages = config.PACKAGES
    if not os.path.isdir(packages):
        _log('Packages directory not found: %s' % packages, xbmc.LOGWARNING)
        return

    count = 0
    for name in os.listdir(packages):
        path = os.path.join(packages, name)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            count += 1
        except Exception as exc:
            _log('Could not delete %s: %s' % (path, exc), xbmc.LOGWARNING)

    xbmcgui.Dialog().notification(
        config.ADDONTITLE,
        '%d package(s) cleared.' % count,
        config.ICON,
        5000,
        sound=False,
    )
