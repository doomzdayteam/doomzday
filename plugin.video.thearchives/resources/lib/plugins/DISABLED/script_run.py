import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from ..plugin import Plugin
from resources.lib.util.common import do_log

class scriptrun(Plugin):
    name = "external script"
    priority = 100    
    
    def routes(self, plugin):
        @plugin.route("/run_script/<path:url>")
        def run_script(url):
            from urllib.parse import unquote_plus,urlparse,parse_qs
            script_link = parse_qs(urlparse(unquote_plus(url)).query)
            script = script_link.get('script')[0]
            script_args = script_link.get('args')
            is_addon = True    
            dialog = xbmcgui.Dialog()
            if script.startswith('special://'):
                script = xbmcvfs.translatePath(script)
                is_addon = False
            for i,args in enumerate(script_args):
                if args.startswith('special://'):
                    script_args[i] = xbmcvfs.translatePath(args)
            if len(script_args) >=2:
                script_args = ','.join(script_args)
            else:
                script_args = script_args[0]
            if is_addon:
                if not xbmc.getCondVisibility(f'System.HasAddon({script})'):
                    ret = dialog.yesno(xbmcaddon.Addon().getAddonInfo('name'),'Addon to run this item appears to not be installed, would you like to install?')
                    if ret:
                        xbmc.executebuiltin(f'InstallAddon({script})')
                    else:
                        return
            else:
                if not xbmcvfs.exists(script):
                    return
            xbmc.executebuiltin(f'RunScript({script},{script_args})')
            
