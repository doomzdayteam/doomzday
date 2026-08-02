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
import xbmcgui
import xbmcvfs
import xbmcaddon
from .downloader import Downloader
from .save_data import save_backup_restore
from .maintenance import fresh_start, clean_backups, truncate_tables
from .addonvar import (dp, dialog, zippath, addon_name, addon_icon, addon_id,
                       home, setting, setting_set, local_string, addons_db)
from .colors import colors

COLOR1 = colors.color_text1
COLOR2 = colors.color_text2

addons_path = Path(xbmcvfs.translatePath('special://home/addons'))
user_data = Path(xbmcvfs.translatePath('special://userdata'))

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
    xbmcgui.Dialog().notification(addon_name, 'Finalizing installation, please wait…', addon_icon, 5000)
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
    xbmcgui.Dialog().notification(addon_name, 'Build Install Complete!', addon_icon, 3000) # Install Complete
    xbmc.sleep(4000)
    xbmcgui.Dialog().notification(addon_name, 'Force Closing Kodi!', addon_icon, 3000)
    xbmc.sleep(4000)
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
    for folder in addons_path.iterdir():
        if not folder.is_dir():
            continue
        addon_xml = folder / 'addon.xml'
        if not addon_xml.exists():
            continue
        try:
            tree = ET.parse(addon_xml)
            root = tree.getroot()
            if 'kodi.binary' not in ET.tostring(root, encoding='unicode'): # Skip non-binaries
                    continue
            changed = False
            if root.attrib.get('version') != '1.0.0':
                    root.attrib['version'] = '1.0.0' # Rollback version
                    changed = True
            for extension in root.findall('extension'): # Convert extension point to xbmc.python.script entrypoint
                    if extension.attrib.get('point', '').startswith('kodi.'):
                            extension.attrib.clear()
                            extension.attrib['point'] = 'xbmc.python.script'
                            extension.attrib['library'] = 'default.py'
                            changed = True
            platform = root.find("./extension[@point='xbmc.addon.metadata']/platform")
            if platform is not None and platform.text != 'all':
                    platform.text = 'all' # Set platform to all
                    changed = True
            dummy_file = folder / 'default.py'
            if not dummy_file.exists():
                    with open(dummy_file, 'w', encoding='utf-8') as f:
                            f.write('# Dummy file used for binary addon update\n') # Create dummy file
                    changed = True
            if changed:
                    tree.write(addon_xml, encoding='utf-8', xml_declaration=True) # Write addon.xml
                    xbmc.log(f'Prepared binary addon for update: {folder.name}', xbmc.LOGINFO)
        except Exception as e:
                xbmc.log(f'Failed to prepare binary addon {folder.name}: {e}', xbmc.LOGINFO)

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
