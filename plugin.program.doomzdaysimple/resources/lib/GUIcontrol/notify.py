import xbmcgui
import xbmcaddon
from urllib.request import Request, urlopen
from uservar import notify_url

def get_notify() -> list:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0'}
    req = Request(notify_url, headers=headers)
    response = urlopen(req).read().decode('utf-8')
    try:
        split_response = response.split('|||')
        notify_version = int(split_response[0])
        message = split_response[1]
    except:
        notify_version = 0
        message = 'Improper Notifications format. Please check the Notifications text.'
    return [notify_version, message]
    

def notification(message: str) -> None:  
    class Notify(xbmcgui.WindowXMLDialog):
        KEY_NAV_BACK = 92
        TEXTBOX = 300
        CLOSEBUTTON = 302
        
        def onInit(self):
            self.getControl(self.TEXTBOX).setText(message)
            
        def onAction(self, action):
            if action.getId() == self.KEY_NAV_BACK:
                self.Close()
    
        def onClick(self, controlId):
            if controlId == self.CLOSEBUTTON:
                self.Close()

        def Close(self):
            self.close()
    
    d = Notify('notify.xml', xbmcaddon.Addon().getAddonInfo('path'), 'Default', '720p')
    d.doModal()
    del d