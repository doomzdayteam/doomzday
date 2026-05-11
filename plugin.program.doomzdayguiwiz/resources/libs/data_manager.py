"""
data_manager.py — Credential backup and restore for Omega GUI Wizard.

Strategy
--------
Each supported addon's entire ``addon_data/<addon_id>/`` folder is copied into
a timestamped sub-directory of ``BACKUPDIR`` (which MUST live outside
``special://home/`` so the backup survives a build install that wipes the Kodi
home directory).

Layout::

    BACKUPDIR/
      OmegaWizardCreds/
        2025-01-15_143022/        ← dated snapshot
          script.trakt/
            settings.xml
            token.json
          script.module.resolveurl/
            settings.xml
          ...
        2025-01-14_091500/        ← previous snapshot (kept up to BACKUP_KEEP)

Restore simply copies everything from the latest snapshot back into
``special://home/userdata/addon_data/``.
"""

from __future__ import annotations

import os
import shutil
import time
import xbmc
import xbmcgui

from . import config


def _log(msg: str, level: int = xbmc.LOGDEBUG) -> None:
    xbmc.log('[OmegaWiz/data_manager] %s' % msg, level)


# Addons whose data is backed up (combined list; extend in uservar.py)
_ALL_CRED_ADDON_IDS: list[str] = (
    config.TRAKT_ADDON_IDS
    + config.DEBRID_ADDON_IDS
)


def _datestamp() -> str:
    return time.strftime('%Y-%m-%d_%H%M%S')


def _snapshot_dir(base: str) -> str:
    return os.path.join(base, _datestamp())


def _sorted_snapshots(base: str) -> list[str]:
    """Return a list of snapshot directory paths sorted oldest-first."""
    try:
        entries = [
            os.path.join(base, d)
            for d in os.listdir(base)
            if os.path.isdir(os.path.join(base, d))
        ]
        return sorted(entries)
    except OSError:
        return []


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------
def backup_credentials(backup_dir: str = None) -> bool:
    """Copy all credentialed addon_data folders to a dated snapshot.

    Returns True if at least one addon was backed up, False otherwise.
    Rotates old snapshots so only BACKUP_KEEP copies are kept.
    """
    if backup_dir is None:
        backup_dir = config.CREDS_BACKUP

    os.makedirs(backup_dir, exist_ok=True)

    snapshot = _snapshot_dir(backup_dir)
    os.makedirs(snapshot, exist_ok=True)

    backed_up = 0
    for addon_id in _ALL_CRED_ADDON_IDS:
        src = os.path.join(config.ADDON_DATA_ROOT, addon_id)
        if not os.path.isdir(src):
            _log('No addon_data for %r — skipping' % addon_id)
            continue
        dest = os.path.join(snapshot, addon_id)
        try:
            shutil.copytree(src, dest)
            _log('Backed up %r → %s' % (addon_id, dest))
            backed_up += 1
        except Exception as exc:
            _log('Failed to back up %r: %s' % (addon_id, exc), xbmc.LOGERROR)

    if backed_up == 0:
        # Remove the empty snapshot directory we just created
        try:
            os.rmdir(snapshot)
        except OSError:
            pass
        _log('Nothing to back up — all addon_data directories missing', xbmc.LOGWARNING)
        xbmcgui.Dialog().notification('Credentials Backup', 'Nothing to back up — no addon data found', xbmcgui.NOTIFICATION_WARNING, 5000)
        return False

    _log('Backup complete: %d addon(s) in %s' % (backed_up, snapshot), xbmc.LOGINFO)
    xbmcgui.Dialog().notification('Credentials Backup', 'Backup complete: %d addon(s) saved' % backed_up, xbmcgui.NOTIFICATION_INFO, 5000)
    _rotate(backup_dir)
    return True


def _rotate(backup_dir: str) -> None:
    """Remove the oldest snapshots so we keep at most BACKUP_KEEP copies."""
    snaps = _sorted_snapshots(backup_dir)
    keep = max(1, config.BACKUP_KEEP)
    while len(snaps) > keep:
        oldest = snaps.pop(0)
        try:
            shutil.rmtree(oldest)
            _log('Rotated old backup: %s' % oldest)
        except Exception as exc:
            _log('Could not remove old backup %s: %s' % (oldest, exc), xbmc.LOGWARNING)


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------
def restore_credentials(backup_dir: str = None, snapshot_path: str = None) -> bool:
    """Copy the latest (or specified) snapshot back into addon_data.

    Returns True if at least one addon was restored.
    Also sets module-level ``last_restore_summary`` dict with keys
    'trakt' and 'debrid' (booleans) for use by callers wanting a UI message.
    """
    global last_restore_summary
    last_restore_summary = {'trakt': False, 'debrid': False}

    if backup_dir is None:
        backup_dir = config.CREDS_BACKUP

    if snapshot_path is None:
        snaps = _sorted_snapshots(backup_dir)
        if not snaps:
            _log('No backup snapshots found in %s' % backup_dir, xbmc.LOGWARNING)
            xbmcgui.Dialog().notification('Credentials Restore', 'No backup found!', xbmcgui.NOTIFICATION_WARNING, 5000)
            return False
        snapshot_path = snaps[-1]  # most recent

    _log('Restoring credentials from %s' % snapshot_path, xbmc.LOGINFO)

    trakt_ids  = set(config.TRAKT_ADDON_IDS)
    debrid_ids = set(config.DEBRID_ADDON_IDS)

    restored = 0
    for addon_id in os.listdir(snapshot_path):
        src = os.path.join(snapshot_path, addon_id)
        if not os.path.isdir(src):
            continue
        dest = os.path.join(config.ADDON_DATA_ROOT, addon_id)
        try:
            os.makedirs(dest, exist_ok=True)
            # Copy each item individually so we don't obliterate the dest dir
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dest, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            _log('Restored %r → %s' % (addon_id, dest))
            restored += 1
            if addon_id in trakt_ids:
                last_restore_summary['trakt'] = True
            if addon_id in debrid_ids:
                last_restore_summary['debrid'] = True
        except Exception as exc:
            _log('Failed to restore %r: %s' % (addon_id, exc), xbmc.LOGERROR)

    if restored > 0:
        xbmcgui.Dialog().notification('Credentials Restore', '%d addon(s) restored' % restored, xbmcgui.NOTIFICATION_INFO, 5000)
    else:
        xbmcgui.Dialog().notification('Credentials Restore', 'Nothing restored — backup may be empty', xbmcgui.NOTIFICATION_WARNING, 5000)
    _log('Restore complete: %d addon(s) restored' % restored, xbmc.LOGINFO)
    return restored > 0


last_restore_summary: dict = {'trakt': False, 'debrid': False}


# ---------------------------------------------------------------------------
# Snapshot list (for a "choose backup" UI)
# ---------------------------------------------------------------------------
def list_snapshots(backup_dir: str = None) -> list[str]:
    """Return snapshot directory paths sorted newest-first."""
    if backup_dir is None:
        backup_dir = config.CREDS_BACKUP
    return list(reversed(_sorted_snapshots(backup_dir)))


def has_backup(backup_dir: str = None) -> bool:
    return bool(list_snapshots(backup_dir))
