################################################################################
#      Copyright (C) 2015 Surfacingx                                           #
#                                                                              #
#  This Program is free software; you can redistribute it and/or modify        #
#  it under the terms of the GNU General Public License as published by        #
#  the Free Software Foundation; either version 2, or (at your option)         #
#  any later version.                                                          #
#                                                                              #
#  This Program is distributed in the hope that it will be useful,             #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of              #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the                #
#  GNU General Public License for more details.                                #
#                                                                              #
#  You should have received a copy of the GNU General Public License           #
#  along with XBMC; see the file COPYING.  If not, write to                    #
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.       #
#  http://www.gnu.org/copyleft/gpl.html                                        #
################################################################################

import os
import time
import xbmc
import xbmcgui
import uservar

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from . import wizard as wiz

ADDONTITLE = uservar.ADDONTITLE
COLOR1     = uservar.COLOR1
COLOR2     = uservar.COLOR2

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
       'AppleWebKit/537.36 (KHTML, like Gecko) '
       'Chrome/122.0.0.0 Safari/537.36')


def download(url, dest, dp=None):
    """Download *url* to *dest*, updating *dp* with progress.

    *dp* may be an ``xbmcgui.DialogProgress`` **or** an
    ``InstallWindow`` instance — both implement the same interface.
    Returns True on success, False on failure or user cancel.
    """
    own_dp = dp is None
    if own_dp:
        dp = xbmcgui.DialogProgress()
        dp.create(ADDONTITLE, 'Downloading…')

    dp.update(0)
    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)

    try:
        req = Request(url, headers={'User-Agent': _UA})
        with urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get('Content-Length') or 0)
            downloaded = 0
            start = time.time()
            chunk = 512 * 1024
            with open(dest, 'wb') as fh:
                while True:
                    data = resp.read(chunk)
                    if not data:
                        break
                    fh.write(data)
                    downloaded += len(data)

                    if dp.iscanceled():
                        break

                    elapsed = max(time.time() - start, 0.001)
                    if total > 0:
                        pct = int(downloaded * 100 / total)
                        dl_mb  = downloaded / (1024 * 1024)
                        tot_mb = total / (1024 * 1024)
                        speed  = downloaded / elapsed
                        speed_mb = speed / (1024 * 1024)
                        eta = (total - downloaded) / speed if speed > 0 else 0
                        line1 = ('[COLOR %s][B]Size:[/B][/COLOR] '
                                 '[COLOR %s]%.2f[/COLOR] MB of '
                                 '[COLOR %s]%.2f[/COLOR] MB'
                                 % (COLOR2, COLOR1, dl_mb, COLOR1, tot_mb))
                        line2 = ('[COLOR %s][B]Speed:[/B][/COLOR] '
                                 '[COLOR %s]%.2f[/COLOR] MB/s  '
                                 '[B]ETA:[/B] [COLOR %s]%02d:%02d[/COLOR]'
                                 % (COLOR2, COLOR1, speed_mb,
                                    COLOR1, *divmod(int(eta), 60)))
                    else:
                        pct   = 0
                        dl_mb = downloaded / (1024 * 1024)
                        line1 = '[COLOR %s]%.1f MB received[/COLOR]' % (COLOR1, dl_mb)
                        line2 = ''

                    dp.update(pct, line1 + ('\n' + line2 if line2 else ''))

        if dp.iscanceled():
            try:
                os.remove(dest)
            except OSError:
                pass
            wiz.LogNotify(
                '[COLOR %s]%s[/COLOR]' % (COLOR1, ADDONTITLE),
                '[COLOR %s]Download Cancelled[/COLOR]' % COLOR2,
            )
            if own_dp:
                dp.close()
            return False

        if own_dp:
            dp.close()
        return True

    except (HTTPError, URLError) as exc:
        wiz.log('download ERROR %s: %s' % (url, exc), xbmc.LOGERROR)
        try:
            os.remove(dest)
        except OSError:
            pass
        if own_dp:
            dp.close()
        return False
    except Exception as exc:
        wiz.log('download UNEXPECTED ERROR %s: %s' % (url, exc), xbmc.LOGERROR)
        try:
            os.remove(dest)
        except OSError:
            pass
        if own_dp:
            dp.close()
        return False