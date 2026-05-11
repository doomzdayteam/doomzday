# -*- coding: utf-8 -*-
"""
    MicroJen Scrapers Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import traceback
from datetime import datetime
from kodi_six import xbmc

import six

from io import open

from microjenscrapers.modules import control

LOGDEBUG = xbmc.LOGDEBUG
LOGINFO = xbmc.LOGINFO
LOGNOTICE = xbmc.LOGNOTICE if control.getKodiVersion() < 19 else xbmc.LOGINFO
LOGWARNING = xbmc.LOGWARNING
LOGERROR = xbmc.LOGERROR
LOGFATAL = xbmc.LOGFATAL
LOGNONE = xbmc.LOGNONE

name = control.addonInfo('name')
DEBUGPREFIX = '[ MicroJen Scrapers DEBUG ]'
LOGPATH = control.transPath('special://logpath/')
log_file = os.path.join(LOGPATH, 'pressplay.log')
debug_enabled = control.addon('script.module.microjenscrapers').getSetting('addon.debug')
debug_enabled = False


def log(msg, trace=0):

    if not debug_enabled == 'true':
        return

    try:
        if trace == 1:
            failure = six.ensure_str(traceback.format_exc())
            _msg = '%s: %s' % (six.ensure_text(msg), failure)
        else:
            _msg = '%s' % six.ensure_text(msg)

        #if not debug_log == '0':
        if not os.path.exists(log_file):
            f = open(log_file, 'w')
            f.close()
        with open(log_file, 'a', encoding='utf-8') as f:
            line = '[%s %s] %s: %s' % (datetime.now().date(), str(datetime.now().time())[:8], DEBUGPREFIX, _msg)
            f.write(line.rstrip('\r\n')+'\n\n')
        #else:
            #xbmc.log('%s: %s' % (DEBUGPREFIX, _msg), LOGDEBUG)
    except Exception as e:
        try:
            xbmc.log('MicroJen Scrapers Logging Failure: %s' % e, LOGDEBUG)
        except:
            pass

