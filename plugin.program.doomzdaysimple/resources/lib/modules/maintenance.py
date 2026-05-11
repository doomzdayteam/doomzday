import os
import shutil
import sqlite3
import xbmc
import xbmcaddon
import xbmcgui
from .skinSwitch import swapSkins
from .addonvar import currSkin, user_path, db_path, addon_name, textures_db, advancedsettings_xml, dialog, dp, xbmcPath, packages, setting_set, addon_icon, local_string, addons_db
from .whitelist import EXCLUDES_INSTALL, EXCLUDES_FRESH

def purge_db(db):
    if os.path.exists(db):
        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()
        except Exception as e:
            xbmc.log("DB Connection Error: %s" % str(e), xbmc.LOGDEBUG)
            return False
    else: 
        xbmc.log('%s not found.' % db, xbmc.LOGINFO)
        return False
    cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    for table in cur.fetchall():
        if table[0] == 'version': 
            xbmc.log('Data from table `%s` skipped.' % table[0], xbmc.LOGDEBUG)
        else:
            try:
                cur.execute("DELETE FROM %s" % table[0])
                conn.commit()
                xbmc.log('Data from table `%s` cleared.' % table[0], xbmc.LOGDEBUG)
            except Exception as e:
                xbmc.log("DB Remove Table `%s` Error: %s" % (table[0], str(e)), xbmc.LOGERROR)
    conn.close()
    xbmc.log('%s DB Purging Complete.' % db, xbmc.LOGINFO)

def clear_thumbnails():
    try:
        if os.path.exists(os.path.join(user_path, 'Thumbnails')):
            shutil.rmtree(os.path.join(user_path, 'Thumbnails'))
    except Exception as e:
            xbmc.log('Failed to delete %s. Reason: %s' % (os.path.join(user_path, 'Thumbnails'), e), xbmc.LOGINFO)
            return
    try:
        if os.path.exists(os.path.join(db_path, 'Textures13.db')):
            os.unlink(os.path.join(db_path, 'Textures13.db'))
    except:
        purge_db(textures_db)
    xbmc.sleep(1000)
    xbmcgui.Dialog().ok(addon_name, local_string(30037))  # Thumbnails Deleted

def advanced_settings(advancedsettings_folder):
    selection = xbmcgui.Dialog().select(local_string(30038), ['1GB Devices (E.g. 1st-3rd gen Firestick/Firestick Lite)','1.5GB Devices (E.g. 4k Firestick)','2GB+ Devices (E.g. Shield Pro/Shield Tube/FireTV Cube)','Default (Reset to Default)',local_string(30039)])  # Select Ram Size, Delete
    if selection==0:
        xml = os.path.join(advancedsettings_folder, '1_gb.xml')
    elif selection==1:
        xml = os.path.join(advancedsettings_folder, '1_5gb.xml')
    elif selection==2:
        xml = os.path.join(advancedsettings_folder, '2_gb.xml')
    elif selection==3:
        xml = os.path.join(advancedsettings_folder, 'default.xml')
        if os.path.exists(advancedsettings_xml):
            os.unlink(advancedsettings_xml)
        xbmc.sleep(1000)
        dialog.ok(addon_name, local_string(30040))  # Advanced Settings Deleted
        os._exit(1)
    elif selection==4:
        if os.path.exists(advancedsettings_xml):
            os.unlink(advancedsettings_xml)
        xbmc.sleep(1000)
        dialog.ok(addon_name, local_string(30107))  # Advanced Settings Set
        os._exit(1)
    else:
        return
    if os.path.exists(advancedsettings_xml):
        os.unlink(advancedsettings_xml)
    shutil.copyfile(xml, advancedsettings_xml)
    xbmc.sleep(1000)
    dialog.ok(addon_name, local_string(30041))  # Advanced Settings Set
    os._exit(1)

def fresh_start(standalone=False):
    if standalone:
        yesFresh = dialog.yesno(local_string(30012), local_string(30042), nolabel=local_string(30032), yeslabel=local_string(30012))  # Are you sure?
        if not yesFresh:
            quit()
    if not currSkin() in ['skin.estuary']:
        swapSkins('skin.estuary')
        x = 0
        xbmc.sleep(100)
        while not xbmc.getCondVisibility("Window.isVisible(yesnodialog)") and x < 150:
            x += 1
            xbmc.sleep(100)
            xbmc.executebuiltin('SendAction(Select)')
        if xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
            xbmc.executebuiltin('SendClick(11)')
        else: 
            xbmc.log('Fresh Install: Skin Swap Timed Out!', xbmc.LOGINFO)
            return False
        xbmc.sleep(100)
    if not currSkin() in ['skin.estuary']:
        xbmc.log('Fresh Install: Skin Swap failed.', xbmc.LOGINFO)
        return
    dp.create(addon_name, local_string(30043))  # Deleting files and folders...
    xbmc.sleep(100)
    dp.update(30, local_string(30043))
    xbmc.sleep(100)
    if standalone:
        for root, dirs, files in os.walk(xbmcPath, topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDES_FRESH]
            for name in files:
                if name not in EXCLUDES_FRESH:
                    try:
                        os.remove(os.path.join(root, name))
                    except:
                        xbmc.log('Unable to delete ' + name, xbmc.LOGINFO)
        dp.update(60, local_string(30043))
        xbmc.sleep(100)    
        for root, dirs, files in os.walk(xbmcPath,topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDES_FRESH]
            for name in dirs:
                if name not in ['addons', 'userdata', 'Database', 'addon_data', 'backups', 'temp']:
                    try:
                        shutil.rmtree(os.path.join(root,name),ignore_errors=True, onerror=None)
                    except:
                        xbmc.log('Unable to delete ' + name, xbmc.LOGINFO)

    if not standalone:                
        for root, dirs, files in os.walk(xbmcPath, topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDES_INSTALL]
            for name in files:
                if name not in EXCLUDES_INSTALL:
                    try:
                        os.remove(os.path.join(root, name))
                    except:
                        xbmc.log('Unable to delete ' + name, xbmc.LOGINFO)
        dp.update(60, local_string(30043))
        xbmc.sleep(100)    
        for root, dirs, files in os.walk(xbmcPath,topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDES_INSTALL]
            for name in dirs:
                if name not in ['addons', 'userdata', 'Database', 'addon_data', 'backups', 'temp']:
                    try:
                        shutil.rmtree(os.path.join(root,name),ignore_errors=True, onerror=None)
                    except:
                        xbmc.log('Unable to delete ' + name, xbmc.LOGINFO)
    dp.update(60, local_string(30043))
    xbmc.sleep(100)
    if not os.path.exists(packages):
        os.mkdir(packages)
    dp.update(100, local_string(30044))  # Done Deleting Files
    xbmc.sleep(1000)
    if standalone is True:
        setting_set('firstrun', 'true')
        setting_set('buildname', 'No Build Installed')
        setting_set('buildversion', '0')
        truncate_tables()
        dialog.ok(addon_name, local_string(30045))  # Fresh Start Complete
        os._exit(1)
    else:
        return

def clean_backups():
    for filename in os.listdir(packages):
        file_path = os.path.join(packages, filename)
        try:
            os.unlink(file_path)
        except OSError:
            shutil.rmtree(file_path)

def clear_packages_startup():
    packages_dir = os.listdir(packages)
    if len(packages_dir) == 0:
        pass
    else:
        clear_packages()
        
def clear_packages():
    file_count = len([name for name in os.listdir(packages)])
    for filename in os.listdir(packages):
        file_path = os.path.join(packages, filename)
        try:
               if os.path.isfile(file_path) or os.path.islink(file_path):
                   os.unlink(file_path)
               elif os.path.isdir(file_path):
                   shutil.rmtree(file_path)
        except Exception as e:
            xbmc.log('Failed to delete %s. Reason: %s' % (file_path, e), xbmc.LOGINFO)
    xbmcgui.Dialog().notification(addon_name, str(file_count)+' ' + local_string(30046), addon_icon, 5000, sound=False)  # Packages Cleared

def truncate_tables():
    try:
        con = sqlite3.connect(addons_db)
        cursor = con.cursor()
        cursor.execute('DELETE FROM addonlinkrepo;',)
        cursor.execute('DELETE FROM addons;',)
        cursor.execute('DELETE FROM package;',)
        cursor.execute('DELETE FROM repo;',)
        cursor.execute('DELETE FROM update_rules;',)
        cursor.execute('DELETE FROM version;',)
        con.commit()
    except sqlite3.Error as e:
        xbmc.log('There was an error reading the database - %s' %e, xbmc.LOGINFO)
        return ''
    finally:
        try:
            if con:
                con.close()
        except UnboundLocalError as e:
            xbmc.log('%s: There was an error connecting to the database - %s' % (xbmcaddon.Addon().getAddonInfo('name'), e), xbmc.LOGINFO)
    try:
        con = sqlite3.connect(addons_db)
        cursor = con.cursor()
        cursor.execute('VACUUM;',)
        con.commit()
    except sqlite3.Error as e:
        xbmc.log(f"Failed to vacuum data from the sqlite table: {e}", xbmc.LOGINFO)
    finally:
        if con:
            con.close()
