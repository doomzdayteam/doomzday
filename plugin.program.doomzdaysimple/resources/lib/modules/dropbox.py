import xbmc
import os
import shutil
import urllib
from .utils import Log

def DownloadFile(url,dst):
    if not xbmc.getCondVisibility('System.HasAddon(script.module.requests)'):
        xbmc.executebuiltin('InstallAddon(script.module.requests)')
    if not xbmc.getCondVisibility('System.HasAddon(script.module.urllib3)'):
        xbmc.executebuiltin('InstallAddon(script.module.urllib3)')
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    file = session.get(url, stream=True,proxies=urllib.request.getproxies())
    dump = file.raw
    with open(dst, 'wb') as location:
        shutil.copyfileobj(dump, location)
    if os.path.exists(dst):
        Log('File {} downloaded From {}'.format(dst,url))
        return True
    else:
        Log('File {} not downloaded From {}'.format(dst,url))
        return False