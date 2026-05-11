import os
import json
import base64
from datetime import datetime
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
from uservar import buildfile
from urllib.request import Request, urlopen
from .parser import XmlParser, TextParser

addon_id = xbmcaddon.Addon().getAddonInfo('id')
addon           = xbmcaddon.Addon(addon_id)
addon_info      = addon.getAddonInfo
addon_version   = addon_info('version')
addon_name      = addon_info('name')
addon_icon      = addon_info("icon")
addon_fanart    = addon_info("fanart")
translatePath   = xbmcvfs.translatePath
addon_profile   = translatePath(addon_info('profile'))
addon_path      = translatePath(addon_info('path'))    
setting         = addon.getSetting
setting_true    = lambda x: bool(True if setting(str(x)) == "true" else False)
setting_set     = addon.setSetting
local_string    = addon.getLocalizedString
CURRENT_BUILD   = setting('buildname')
CURRENT_VERSION = setting('buildversion')
BUILD_VERSION   = setting('buildversion')
home = translatePath('special://home/')
dialog = xbmcgui.Dialog()
dp = xbmcgui.DialogProgress()
xbmcPath=os.path.abspath(home)
addons_path = os.path.join(home, 'addons/')
user_path = os.path.join(home, 'userdata/')
data_path = os.path.join(user_path, 'addon_data/')
db_path = translatePath('special://database/')
#addons_db = os.path.join(db_path,'Addons33.db')
#textures_db = os.path.join(db_path,'Textures13.db')
packages = os.path.join(addons_path, 'packages/')
zippath = os.path.join(packages, 'tempzip.zip')
resources = os.path.join(addon_path, 'resources/')
gui_save_default = os.path.join(user_path, 'gui_settings/')
gui_save_user = os.path.join(user_path, 'gui_settings_user/')
user_agent = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
headers = {'User-Agent': user_agent}
#KODIV  = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
kodi_ver = str(xbmc.getInfoLabel("System.BuildVersion")[:4])
kodi_versions = ['K20', 'K21', 'K22']
sleep = xbmc.sleep
#build_file = os.path.join(addon_profile,'buildmenu.json')
notify_file = os.path.join(addon_profile,'notify.txt')
texts_path = os.path.join(resources, 'texts/')
authorize = texts_path + 'authorize.json'
installed_date = str(datetime.now())[:-7]

#Advanced Settings Paths
advancedsettings_xml =  os.path.join(user_path, 'advancedsettings.xml')
advancedsettings_k20 = os.path.join(resources, 'advancedsettings/nexus/')
advancedsettings_k21 = os.path.join(resources, 'advancedsettings/omega')
advancedsettings_k22 = os.path.join(resources, 'advancedsettings/piers')

def isBase64(s):
    try:
        if base64.b64encode(base64.b64decode(s)).decode('utf8') == s:
            return True
        else:
            return False
    except:
        return False

def currSkin():
    return xbmc.getSkinDir()
    
def percentage(part, whole):
    return 100 * float(part)/float(whole)


def get_latest_db(db_type: str) -> str:
    highest_number = -1
    highest_file = None
    for file in os.listdir(db_path):
        if file.startswith(db_type) and file.endswith('.db'):
            try:
                number = int(file[len(db_type):file.index('.db')])
                if number > highest_number:
                    highest_number = number
                    highest_file = file
            except ValueError:
                pass
    if highest_file is not None:
        return os.path.join(db_path, highest_file)

textures_db = get_latest_db('Textures')
addons_db = get_latest_db('Addons')

def file_check(bfile):
    if isBase64(bfile):
        return base64.b64decode(bfile).decode('utf8')
    return bfile
        
def get_page(url):
       req = Request(file_check(url), headers = headers)
       return urlopen(req).read().decode('utf-8')
    
def get_version():
    response = ''
    try:
       response = get_page(buildfile)
    except:
       version = None
       url = None
    version = ''
    url = ''
    builds = []

    if '"builds"' in response or "'builds'" in response:
       builds = json.loads(response)['builds']
       
    elif '<version>' in response:
       xml = XmlParser(response)
       builds = xml.parse_builds()
       
    elif 'name="' in response:
       text = TextParser(response)
       builds = text.parse_builds()

    for build in builds:
       if build.get('name') == CURRENT_BUILD:
           version = str(build.get('version'))
           url = (build.get('url', ''))
           break
    return version, url
UPDATE_VERSION, BUILD_URL = get_version()
