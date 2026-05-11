from ..plugin import Plugin
import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import json, sys

import requests
session = requests.Session()

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *

addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')
default_fanart = xbmcaddon.Addon(addon_id).getAddonInfo('fanart')
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 OPR/73.0.3856.344'
iStream_Agent = 'user-agent=' + USER_AGENT


class mpd_play_video(Plugin):
    name = "ffmpeg video playback"
    priority = 10

    def play_video(self, item):
        if not '"link":' in str(item) : return False
        item = json.loads(item)
        link = item["link"]
        title = item["title"]
        thumbnail = item.get("thumbnail", default_icon)
        liz = xbmcgui.ListItem(title)
        liz.setInfo('video', {'Title': title})
        liz.setArt({'thumb': thumbnail, 'icon': thumbnail})   
        
        mpd_url = '' 
                                       
        if  'X-forwarded-for' in link :
            xf_url = link.split("|X-forwarded-for=")
            # link = xf_url[0]
            header_url = xf_url[-1]
            if not header_url. startswith('http'): header_url = 'http://' + header_url
            
        else :
            header_url = link.replace(
                                "is_hls://", "").replace(
                                "is_msready://", "").replace(
                                "is_mpd://", "")
 
        headers = {'User-Agent': USER_AGENT ,
                               'Referer': header_url }         
        
        if link :                                            
            if link.startswith("is_ffmpeg://"):
                mpd_url = link.replace("is_ffmpeg://", "")               
                liz.setProperty('inputstream', 'inputstream.ffmpegdirect')           
                liz.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
                liz.setProperty('inputstream.ffmpegdirect.stream_mode', 'timeshift')
                liz.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')                  
                liz.setProperty('inputstream.ffmpegdirect.stream_headers', str(headers) )   
                liz.setMimeType('application/x-mpegURL')      
            
            if mpd_url :         
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
                xbmc.Player().play(mpd_url, liz)   
                return True
    
        else:
        	return False 
        
    