# used accross all addon
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os
from ..plugin import Plugin
from ..DI import DI

addon_id = xbmcaddon.Addon().getAddonInfo('id')
ownAddon = xbmcaddon.Addon(id=addon_id)
debugMode = ownAddon.getSetting('debug') or 'false' 
PATH = xbmcaddon.Addon().getAddonInfo("path")
     
def do_log(info):   
    if debugMode. lower() == 'true' :       
        xbmc.log(f' > MicroJen Log > \n {info}', xbmc.LOGINFO)         

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
   