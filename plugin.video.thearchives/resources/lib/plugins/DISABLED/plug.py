import json
import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.util.common import do_log
from ..plugin import Plugin

class plugplay(Plugin):
    name = "external plugin"
    priority = 100    
    
    def routes(self, plugin):
        @plugin.route("/run_plug/<path:url>")
        def run_plug(url):
            from urllib.parse import unquote_plus,urlparse
            plug_link = url 
            this_plug = unquote_plus(plug_link)
            this_link = unquote_plus(plug_link)
            dialog = xbmcgui.Dialog()
            if 'dailymotion' in this_plug.lower():
                u = 'plugin.video.dailymotion_com' + ',' + this_plug.split('?')[-1]
                z = 'plugin://plugin.video.dailymotion_com/?'+ this_plug.split('?')[-1]                
                xbmc.executebuiltin('RunAddon({})'.format(u))
                
            elif 'resolveurl_auth' in this_plug.lower():
                u = 'script.module.resolveurl/?mode=auth_rd'
                z = 'plugin://script.module.resolveurl/?mode=auth_rd'
                xbmc.executebuiltin('RunPlugin({})'.format(z))
                
            elif 'resolveurl_settings' in this_plug.lower():
                u = 'script.module.resolveurl'
                z = 'plugin://script.module.resolveurl'
                xbmcaddon.Addon(u).openSettings()
                
            else:
                this_plug = urlparse(this_plug)
                              
                if this_plug.scheme == 'plugin' :
                    addon_id = this_plug.netloc
                else :
                    addon_id = this_plug.path
                                       
                if addon_id.endswith('/') : addon_id=addon_id.replace('/','')
                
                splitter = addon_id.count('/')
                if splitter >= 1 :
                    addon_id = addon_id.split('/')[0]
                
                if not xbmc.getCondVisibility(f'System.HasAddon({addon_id})'):
                    ret = dialog.yesno(xbmcaddon.Addon().getAddonInfo('name'),addon_id + ' Addon to run this item appears to not be installed, would you like to install?')
                    if ret:
                        xbmc.executebuiltin(f'InstallAddon({addon_id})')
                    else:
                        return
                        
                if xbmc.getCondVisibility(f'System.HasAddon({addon_id})'):    
                    this_link ='plugin://' + this_link              
                    if 'play' in this_link.lower() :      
                        xbmc.executebuiltin(f'PlayMedia({this_link})')   
                    else :
                        xbmc.executebuiltin("ActivateWindow({} , {} , return)".format('10025', this_link))     
                        
                        
                else:
                    return