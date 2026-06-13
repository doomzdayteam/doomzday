import xbmc
import xbmcgui
from base64 import b64decode
from ..plugin import Plugin, run_hook

DIALOG = xbmcgui.Dialog()

PASSWORD = 'cGVuaXM='


class Password(Plugin):
    name = 'Password'
    description = 'Enable Password'
    priority = 2000
    
    def get_list(self, url: str):
        if url.startswith('password//'):
            url = url.replace('password//', '')
            if self.password_check():
                return run_hook("get_list", url)

    def password_check(self):
        entered = ''
        if DIALOG.yesno('Password Required', 'Enter Password.', 'Cancel', 'OK'):
            keyboard = xbmc.Keyboard('', 'Enter Password')
            keyboard.doModal()
            if (keyboard.isConfirmed()):
                entered = keyboard.getText()
            else:
                quit()
            try:
                password = b64decode(PASSWORD).decode('utf-8')
            except:
                password = PASSWORD
            if entered != password:
                DIALOG.ok('Access Denied', 'Invalid Password.')
                quit()
            else:
                return True
        else:
            DIALOG.ok('Access Denied', 'A password is required to\naccess this content.')
            quit()
