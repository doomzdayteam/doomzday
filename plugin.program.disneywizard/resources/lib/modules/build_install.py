import os
import json
from datetime import datetime
import time
import sqlite3
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pathlib import Path
import shutil
import xbmc
import xbmcvfs
import xbmcaddon
from .downloader import Downloader
from .save_data import save_backup_restore
from .maintenance import fresh_start, clean_backups, truncate_tables
from .addonvar import dp, dialog, zippath, addon_name, addon_id, home, setting, setting_set, local_string, addons_db
from .colors import colors

COLOR1 = colors.color_text1
COLOR2 = colors.color_text2

addons_path = Path(xbmcvfs.translatePath('special://home/addons'))
user_data = Path(xbmcvfs.translatePath('special://userdata'))
binaries_path = Path(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))) / 'binaries.json'

def build_install(name, name2, version, url):
    # Ready to install, Cancel, Continue
    if not dialog.yesno(
        COLOR2(name),
        COLOR2(local_string(30028)),
        nolabel=local_string(30029),
        yeslabel=local_string(30030)
    ):
        return
    
    download_build(name, url)
    save_backup_restore('backup')
    fresh_start()
    extract_build()
    if name2 == setting('buildname'):
        save_backup_restore('restore_gui')
    else:
        save_backup_restore('restore')
    clean_backups()
    setting_set('buildname', name2)
    setting_set('buildversion', version)
    setting_set('update_passed', 'false')
    setting_set('firstrun', 'true')
    check_binary()
    enable_wizard()
    truncate_tables()
    
    dialog.ok(addon_name, local_string(30036))  # Install Complete
    os._exit(1)

def download_build(name, url):
    if os.path.exists(zippath):
        os.unlink(zippath)
    d = Downloader(url)
    d.download_build(name, zippath)

def extract_build():
    if os.path.exists(zippath):
        dp.create(addon_name, local_string(30034))  # Extracting files
        counter = 1
        with ZipFile(zippath, 'r') as z:
            files = z.infolist()
            for file in files:
                filename = file.filename
                filename_path = os.path.join(home, filename)
                progress_percentage = int(counter/len(files)*100)
                try:
                    if not os.path.exists(filename_path) or 'Addons33.db' in filename:
                        z.extract(file, home)
                except Exception as e:
                    xbmc.log(f'Error extracting {filename} - {e}', xbmc.LOGINFO)
                dp.update(progress_percentage, f'{local_string(30034)}...\n{progress_percentage}%\n{filename}')
                counter += 1
        dp.update(100, local_string(30035))  # Done Extracting
        xbmc.sleep(500)
        dp.close()
        os.unlink(zippath)

def check_binary():
    binary_list = []
    for folder in addons_path.iterdir():
        if folder.is_dir():
            addon_xml = folder / 'addon.xml'
            if addon_xml.exists():
              with open(addon_xml, 'r', encoding='utf-8', errors='ignore') as f:
                  _xml = f.read()
              if 'kodi.binary' in _xml:
                  try:
                      root = ET.fromstring(_xml)
                      binary_list.append(root.attrib['id'])
                  except:
                      binary_list.append(folder.name)
                  try:
                      shutil.rmtree(folder)
                  except PermissionError as e:
                      xbmc.log(f'Unable to delete binary {folder} - {e}')
    if len(binary_list) > 0:
        with open(binaries_path, 'w', encoding='utf-8') as f:
            json.dump({'items': binary_list}, f, indent = 4)

def restore_binary():
    with open(binaries_path, 'r', encoding='utf-8', errors='ignore') as f:
        binaries_list = json.loads(f.read())['items']
    failed = []
    for plugin_id in binaries_list:
        install = install_addon(plugin_id)
        if install is not True:
            failed.append(plugin_id)
    if len(failed) == 0:
        binaries_path.unlink()
    else:
        with open(binaries_path, 'w', encoding='utf-8') as f:
            json.dump({'items': failed}, f, indent = 4)

def install_addon(plugin_id):
    if xbmc.getCondVisibility(f'System.HasAddon({plugin_id})'):
        return True
    xbmc.executebuiltin(f'InstallAddon({plugin_id})')
    clicked = False
    start = time.time()
    timeout = 20
    while not xbmc.getCondVisibility(f'System.HasAddon({plugin_id})'):
        if time.time() >= start + timeout:
            return False
        xbmc.sleep(500)
        if xbmc.getCondVisibility('Window.IsTopMost(yesnodialog)') and not clicked:
            xbmc.executebuiltin('SendClick(yesnodialog, 11)')
            clicked = True
    return True
# Binaries inspired Dr. Infernoo

def enable_wizard():
    try:
        timestamp = str(datetime.now())[:-7]

        con = sqlite3.connect(addons_db)
        cursor = con.cursor()
        cursor.execute('INSERT or IGNORE into installed (addonID , enabled, installDate) VALUES (?,?,?)', (addon_id, 1, timestamp,))

        cursor.execute('UPDATE installed SET enabled = ? WHERE addonID = ? ', (1, addon_id,))
        con.commit()
    except sqlite3.Error as e:
        xbmc.log('There was an error writing to the database - %s' %e, xbmc.LOGINFO)
        return
    finally:
        try:
            if con:
                con.close()
        except UnboundLocalError as e:
            xbmc.log('%s: There was an error connecting to the database - %s' % (xbmcaddon.Addon().getAddonInfo('name'), e), xbmc.LOGINFO)
