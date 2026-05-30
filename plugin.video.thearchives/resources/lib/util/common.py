import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os
from ..plugin import Plugin
from ..DI import DI

addon_id = xbmcaddon.Addon().getAddonInfo('id')
ownAddon = xbmcaddon.Addon(id=addon_id)
debugMode = ownAddon.getSetting('debug') or 'false' 
PATH = xbmcaddon.Addon().getAddonInfo("path")


def resolve_addon_art_path(art_path):
    if not art_path:
        return art_path

    art_path = str(art_path)
    lower_path = art_path.lower()
    if lower_path.startswith(("http://", "https://", "special://")) or os.path.isabs(art_path):
        return art_path

    return os.path.join(PATH, art_path.replace("/", os.sep))
     
def do_log(info):   
    if debugMode. lower() == 'true' :       
        xbmc.log(f' > TheArchives Log > \n {info}', xbmc.LOGINFO)         

def get_first_setting(*setting_ids):
    for setting_id in setting_ids:
        value = ownAddon.getSetting(setting_id) or ""
        if value:
            return value
    return ""

def get_tmdb_api_key():
    return get_first_setting("tmdb.api_key")

def get_tmdb_read_access_token():
    return get_first_setting("tmdb.access_token")

def get_trakt_api_client_id():
    return get_first_setting("trakt.api_client_id")

def get_trakt_api_client_secret():
    return get_first_setting("trakt.api_client_secret")

class message(Plugin):
    name = "pop up message box"
    priority = 0    
    
    def routes(self, plugin):
        @plugin.route("/show_message/<path:message>")
        def show_message(message, header = 'Information'):
            message = message.replace('message/','')
            if message.lower().startswith("http"):
                message = DI.session.get(message).text
            elif message.lower().startswith("file://"):                
                message = message.replace("file://", "")
                input_file = xbmcvfs.File(os.path.join(PATH, "xml", message))              
                message = input_file.read()
            xbmc.executebuiltin("ActivateWindow(10147)")
            controller = xbmcgui.Window(10147)
            xbmc.sleep(500)
            controller.getControl(1).setLabel(header)
            controller.getControl(5).setText(f"{message}")
   
