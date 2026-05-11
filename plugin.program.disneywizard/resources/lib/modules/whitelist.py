import json
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
from uservar import excludes
from .addonvar import addon_id

translatePath = xbmcvfs.translatePath
addon_id = xbmcaddon.Addon().getAddonInfo('id')
addon = xbmcaddon.Addon(addon_id)
addoninfo  = addon.getAddonInfo
addon_data  = translatePath(addon.getAddonInfo('profile'))
addons_path = translatePath(translatePath('special://home/addons'))
file_path = addon_data + 'whitelist.json'
dialog = xbmcgui.Dialog()

EXCLUDES_BASIC = excludes + [addon_id, 'kodi.log', 'Addons33.db', 'packages', 'backups']
EXCLUDES_FRESH = [addon_id, 'Addons33.db', 'kodi.log', 'script.module.certifi', 'script.module.chardet', 'script.module.idna', 'script.module.requests', 'script.module.urllib3']

def get_whitelist():
    dirs, files = xbmcvfs.listdir(addons_path)
    dirs.sort()
    for x in ['packages', 'temp']:
        dirs.remove(x)
    preselect = []
    if xbmcvfs.exists(file_path):
        with open(file_path, 'r') as wl:
            current_whitelist = json.load(wl)['whitelist']
        for x in range(len(dirs)):
            if dirs[x] in current_whitelist:
                preselect.append(x)
                
    xbmc.log('dirs = ' + str(dirs), xbmc.LOGINFO)
    names = []
    for foldername in dirs:
        try :
            name = xbmcaddon.Addon(foldername).getAddonInfo('name')
        except:
            name = foldername
        names.append(name)
    ret = dialog.multiselect('Select Items to Add to Your Whitelist', names, preselect=preselect)
    xbmc.log('ret = ' + str(ret), xbmc.LOGINFO)
    if ret is None:
        return None
    whitelist = []
    for x in range(len(dirs)):
        if x in ret:
            whitelist.append(dirs[x])
    xbmc.log('whitelist = ' + str(whitelist), xbmc.LOGINFO)
    if not xbmcvfs.exists(addon_data):
        xbmcvfs.mkdir(addon_data)
    with open(file_path, 'w') as whitelist_file:
        json.dump({'whitelist': whitelist}, whitelist_file, indent = 4)

def add_whitelist(_excludes):
    if xbmcvfs.exists(file_path):
        with open(file_path, 'r') as wl:
            whitelist  = json.loads(wl.read())['whitelist']
        for x in whitelist:
            if not x in _excludes:
                _excludes.append(x)
        return _excludes
    else:
        return _excludes
EXCLUDES_INSTALL = add_whitelist(EXCLUDES_BASIC)
