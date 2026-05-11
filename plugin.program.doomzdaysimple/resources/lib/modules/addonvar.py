import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import os
import base64
from datetime import datetime
from .colors import colors


addon_id = xbmcaddon.Addon().getAddonInfo('id')
addon           = xbmcaddon.Addon(addon_id)
addon_info       = addon.getAddonInfo
addon_version   = addon_info('version')
addon_name      = addon_info('name')
addon_icon      = addon_info("icon")
addon_fanart    = addon_info("fanart")
translatePath = xbmcvfs.translatePath
addon_profile   = translatePath(addon_info('profile'))
addon_path      = translatePath(addon_info('path'))    
setting         = addon.getSetting
setting_true    = lambda x: bool(True if setting(str(x)) == "true" else False)
setting_set     = addon.setSetting
local_string    = addon.getLocalizedString
home = translatePath('special://home/')
dialog = xbmcgui.Dialog()
dp = xbmcgui.DialogProgress()
xbmcPath=os.path.abspath(home)
addons_path = os.path.join(home, 'addons/')
user_path = os.path.join(home, 'userdata/')
data_path = os.path.join(user_path, 'addon_data/')
db_path = os.path.join(user_path, 'Database/')
addons_db = os.path.join(db_path,'Addons33.db')
textures_db = os.path.join(db_path,'Textures13.db')
packages = os.path.join(addons_path, 'packages/')
zippath = os.path.join(packages, 'tempzip.zip')
resources = os.path.join(addon_path, 'resources/')
advancedsettings_xml =  os.path.join(user_path, 'advancedsettings.xml')
advancedsettings_folder_k20 = os.path.join(resources, 'advancedsettings_k20/')
advancedsettings_folder_k21 = os.path.join(resources, 'advancedsettings_k21/')
gui_save_default = os.path.join(user_path, 'gui_settings/')
gui_save_user = os.path.join(user_path, 'gui_settings_user/')
user_agent = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
headers = {'User-Agent': user_agent}
current_build = setting('buildname')
KODIV  = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
sleep = xbmc.sleep
build_file = os.path.join(addon_profile,'buildmenu.json')
notify_file = os.path.join(addon_profile,'notify.txt')
texts_path = os.path.join(resources, 'texts/')
authorize = texts_path + 'authorize.json'
installed_date = str(datetime.now())[:-7]
color1 = colors.color_text1
color2 = colors.color_text2

def isBase64(s):
    try:
        if base64.b64encode(base64.b64decode(s)).decode('utf8') == s:
            return True
        else:
            return False
    except:
        return False
try:
    if isBase64(buildfile):
        buildfile = base64.b64decode(buildfile).decode('utf8')
except:
    pass

def currSkin():
    return xbmc.getSkinDir()
def percentage(part, whole):
    return 100 * float(part)/float(whole)
