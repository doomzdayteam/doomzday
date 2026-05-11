import sys
import os
import xbmc
import xbmcplugin
import xbmcgui
from .params import Params
from .play_video import play_video
from uservar import notify_url, changelog_dir
from .menus import main_menu, build_menu, submenu_maintenance, backup_restore, restore_gui_skin
from .authorize import authorize_menu, authorize_submenu
from .build_install import build_install
from .maintenance import fresh_start, clear_packages, clear_thumbnails, advanced_settings
from .whitelist import get_whitelist
from .addonvar import addon, addon_name, addon_icon, gui_save_default, gui_save_user, advancedsettings_k20, advancedsettings_k21, advancedsettings_k22, UPDATE_VERSION, CURRENT_BUILD, BUILD_URL
from .save_data import restore_gui, restore_skin, backup_gui_skin
from .backup_restore import backup_build, restore_menu, restore_build, get_backup_folder, reset_backup_folder

try:
    HANDLE = int(sys.argv[1])
except IndexError:
    HANDLE = 0

def router(paramstring):
    p = Params(paramstring)
    xbmc.log(str(p.get_params()), xbmc.LOGDEBUG)
    
    name = p.get_name()
    name2 = p.get_name2()
    version = p.get_version()
    url = p.get_url()
    mode = p.get_mode()
    icon = p.get_icon()
    description = p.get_description()
    
    xbmcplugin.setContent(HANDLE, 'files')

    if mode is None:
        main_menu()
    
    elif mode == 1:
        build_menu()
    
    elif mode == 2:
        play_video(name, url, icon, description)
    
    elif mode == 3:
        build_install(name, name2, version, url)
    
    elif mode == 4:
        fresh_start(standalone=True)
    
    elif mode == 5:
        submenu_maintenance()
    
    elif mode == 6:
        clear_packages()
    
    elif mode == 7:
        clear_thumbnails()
    
    elif mode == 8:
        advanced_settings(advancedsettings_k20)
    
    elif mode == 9:
        addon.openSettings()
    
    elif mode == 10:
        authorize_menu()
    
    elif mode == 11:
        get_whitelist()
    
    elif mode == 12:
        backup_restore()
    
    elif mode == 13:
        backup_build()
    
    elif mode == 14:
        restore_menu()
    
    elif mode == 15:
        restore_build(url)
    
    elif mode == 16:
        get_backup_folder()
    
    elif mode == 17:
        reset_backup_folder()
    
    elif mode == 18:
        os._exit(1)

    elif mode == 19:
        restore_gui_skin()

    elif mode == 20:
        restore_gui(gui_save_default)

    elif mode == 21:
        restore_skin(gui_save_default)

    elif mode == 22:
        backup_gui_skin(gui_save_user)
        xbmcgui.Dialog().notification(addon_name, 'Backup Complete!', addon_icon, 3000)

    elif mode == 23:
        restore_gui(gui_save_user)
        
    elif mode == 24:
        restore_skin(gui_save_user)
    
    elif mode == 25:
        xbmc.executebuiltin(url)
    
    elif mode == 26:
        from .quick_log import log_viewer
        log_viewer()
    
    elif mode == 27:
        authorize_submenu(name2, icon)
    
    elif mode == 28:
        from .speedtester.addon import run
        run()

    elif mode == 29:
        advanced_settings(advancedsettings_k21)
    
    elif mode == 30:
        from .play_video import video_menu
        video_menu()

    elif mode == 31:
        advanced_settings(advancedsettings_k22)
        
    elif mode == 32:
        name = CURRENT_BUILD
        name2 = name
        if BUILD_URL.startswith('https://www.dropbox.com'):
           url = BUILD_URL.replace('dl=0', 'dl=1')
        else:
            url = BUILD_URL
        build_install(name, name2, UPDATE_VERSION, url) 
    
    elif mode == 100:
        if notify_url in ('http://CHANGEME', 'http://slamiousproject.com/wzrd/notify19.txt', ''):
            xbmcgui.Dialog().notification(addon_name, 'No Notifications to Display!!', addon_icon, 3000)
            sys.exit()
        from . import notify
        message = notify.get_notify()[1]
        notify.notification(message)

    elif mode == 101:
        if changelog_dir in ('http://CHANGEME', ''):
            xbmcgui.Dialog().notification(addon_name, 'No Changelog to Display!!', addon_icon, 3000)
            sys.exit()
        from . import notify
        message = notify.get_changelog()
        notify.notification(message)
        
    xbmcplugin.endOfDirectory(HANDLE)
