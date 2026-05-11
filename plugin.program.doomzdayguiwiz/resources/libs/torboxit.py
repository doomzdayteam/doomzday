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

import xbmc, xbmcaddon, xbmcgui, os, sys, xbmcvfs, glob
import shutil
import urllib.request, urllib.error, urllib.parse
import re
import uservar
import time
from sqlite3 import dbapi2 as database
from datetime import date, datetime, timedelta
from resources.libs import wizard as wiz

ADDON_ID       = uservar.ADDON_ID
ADDONTITLE     = uservar.ADDONTITLE
ADDON          = wiz.addonId(ADDON_ID)
DIALOG         = xbmcgui.Dialog()
HOME           = xbmcvfs.translatePath('special://home/')
ADDONS         = os.path.join(HOME,      'addons')
USERDATA       = os.path.join(HOME,      'userdata')
PLUGIN         = os.path.join(ADDONS,    ADDON_ID)
PACKAGES       = os.path.join(ADDONS,    'packages')
ADDONDATA      = os.path.join(USERDATA,  'addon_data', ADDON_ID)
ADDOND         = os.path.join(USERDATA,  'addon_data')
TORBOXFOLD     = os.path.join(ADDONDATA, 'TorBox')
ICON           = os.path.join(PLUGIN,    'icon.png')
TODAY          = date.today()
TOMORROW       = TODAY + timedelta(days=1)
THREEDAYS      = TODAY + timedelta(days=3)
KEEPTORBOX     = wiz.getS('keeptorbox')
TORBOXSAVE     = wiz.getS('torboxlastsave')
COLOR1         = uservar.COLOR1
COLOR2         = uservar.COLOR2
ORDER          = ['torbox']

TORBOXID = {
	'torbox': {
		'name'     : 'URL Resolver (TorBox)',
		'plugin'   : 'script.module.urlresolver',
		'saved'    : 'torboxlastsave',
		'path'     : os.path.join(ADDONS, 'script.module.urlresolver'),
		'icon'     : os.path.join(ADDONS, 'script.module.urlresolver', 'icon.png'),
		'fanart'   : os.path.join(ADDONS, 'script.module.urlresolver', 'fanart.jpg'),
		'file'     : os.path.join(TORBOXFOLD, 'torbox_data'),
		'settings' : os.path.join(ADDOND, 'script.module.urlresolver', 'settings.xml'),
		'default'  : 'TorBoxResolver_apikey',
		'data'     : ['TorBoxResolver_enabled', 'TorBoxResolver_priority', 'TorBoxResolver_autopick', 'TorBoxResolver_apikey'],
		'activate' : ''}
}

def torboxUser(who):
	user = None
	if TORBOXID[who]:
		if os.path.exists(TORBOXID[who]['path']):
			try:
				add  = wiz.addonId(TORBOXID[who]['plugin'])
				user = add.getSetting(TORBOXID[who]['default'])
			except:
				pass
	return user

def torboxIt(do, who):
	if not os.path.exists(ADDONDATA): os.makedirs(ADDONDATA)
	if not os.path.exists(TORBOXFOLD):  os.makedirs(TORBOXFOLD)
	if who == 'all':
		for log in ORDER:
			if os.path.exists(TORBOXID[log]['path']):
				try:
					addonid = wiz.addonId(TORBOXID[log]['plugin'])
					default = TORBOXID[log]['default']
					user    = addonid.getSetting(default)
					if user == '' and do == 'update': continue
					updateTorBox(do, log)
				except: pass
			else: wiz.log('[TorBox Data] %s(%s) is not installed' % (TORBOXID[log]['name'], TORBOXID[log]['plugin']), xbmc.LOGERROR)
		wiz.setS('torboxlastsave', str(THREEDAYS))
	else:
		if TORBOXID[who]:
			if os.path.exists(TORBOXID[who]['path']):
				updateTorBox(do, who)
		else: wiz.log('[TorBox Data] Invalid Entry: %s' % who, xbmc.LOGERROR)

def clearSaved(who, over=False):
	if who == 'all':
		for tb in TORBOXID:
			clearSaved(tb, True)
	elif TORBOXID[who]:
		file = TORBOXID[who]['file']
		if os.path.exists(file):
			os.remove(file)
			wiz.LogNotify('[COLOR %s]%s[/COLOR]' % (COLOR1, TORBOXID[who]['name']), '[COLOR %s]TorBox Data: Removed![/COLOR]' % COLOR2, 2000, TORBOXID[who]['icon'])
		wiz.setS(TORBOXID[who]['saved'], '')
	if over == False: wiz.refresh()

def updateTorBox(do, who):
	file     = TORBOXID[who]['file']
	settings = TORBOXID[who]['settings']
	data     = TORBOXID[who]['data']
	addonid  = wiz.addonId(TORBOXID[who]['plugin'])
	saved    = TORBOXID[who]['saved']
	default  = TORBOXID[who]['default']
	user     = addonid.getSetting(default)
	suser    = wiz.getS(saved)
	name     = TORBOXID[who]['name']
	icon     = TORBOXID[who]['icon']

	if do == 'update':
		if not user == '':
			try:
				with open(file, 'w') as f:
					for tb in data:
						f.write('<torbox>\n\t<id>%s</id>\n\t<value>%s</value>\n</torbox>\n' % (tb, addonid.getSetting(tb)))
					f.close()
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]TorBox Data: Saved![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[TorBox Data] Unable to Update %s (%s)" % (who, str(e)), xbmc.LOGERROR)
		else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]TorBox Data: Not Registered![/COLOR]' % COLOR2, 2000, icon)
	elif do == 'restore':
		if os.path.exists(file):
			f = open(file, mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close()
			match = re.compile('<torbox><id>(.+?)</id><value>(.+?)</value></torbox>').findall(g)
			try:
				if len(match) > 0:
					for tb, value in match:
						addonid.setSetting(tb, value)
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]TorBox: Restored![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[TorBox Data] Unable to Restore %s (%s)" % (who, str(e)), xbmc.LOGERROR)
	elif do == 'clearaddon':
		wiz.log('%s SETTINGS: %s' % (name, settings), xbmc.LOGDEBUG)
		if os.path.exists(settings):
			try:
				f = open(settings, "r"); lines = f.readlines(); f.close()
				f = open(settings, "w")
				for line in lines:
					match = wiz.parseDOM(line, 'setting', ret='id')
					if len(match) == 0: f.write(line)
					else:
						if match[0] not in data: f.write(line)
						else: wiz.log('Removing Line: %s' % line, xbmc.LOGINFO)
				f.close()
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]Addon Data: Cleared![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[TorBox Data] Unable to Clear Addon %s (%s)" % (who, str(e)), xbmc.LOGERROR)
	wiz.refresh()

def autoUpdate(who):
	if who == 'all':
		for log in TORBOXID:
			if os.path.exists(TORBOXID[log]['path']):
				autoUpdate(log)
	elif TORBOXID[who]:
		if os.path.exists(TORBOXID[who]['path']):
			u  = torboxUser(who)
			su = wiz.getS(TORBOXID[who]['saved'])
			n  = TORBOXID[who]['name']
			if u == None or u == '': return
			elif su == '': torboxIt('update', who)
			elif not u == su:
				if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to save the [COLOR %s]TorBox[/COLOR] data for [COLOR %s]%s[/COLOR]?" % (COLOR2, COLOR1, COLOR1, n), "Addon: [COLOR green][B]%s[/B][/COLOR]" % u, "Saved:[/COLOR] [COLOR red][B]%s[/B][/COLOR]" % su if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]', yeslabel="[B][COLOR green]Save Data[/COLOR][/B]", nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
					torboxIt('update', who)
			else: torboxIt('update', who)

def importlist(who):
	if who == 'all':
		for log in TORBOXID:
			if os.path.exists(TORBOXID[log]['file']):
				importlist(log)
	elif TORBOXID[who]:
		if os.path.exists(TORBOXID[who]['file']):
			d  = TORBOXID[who]['default']
			sa = TORBOXID[who]['saved']
			su = wiz.getS(sa)
			n  = TORBOXID[who]['name']
			f  = open(TORBOXID[who]['file'], mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close()
			m  = re.compile('<torbox><id>%s</id><value>(.+?)</value></torbox>' % d).findall(g)
			if len(m) > 0:
				if not m[0] == su:
					if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to import the [COLOR %s]TorBox[/COLOR] data for [COLOR %s]%s[/COLOR]?" % (COLOR2, COLOR1, COLOR1, n), "File: [COLOR green][B]%s[/B][/COLOR]" % m[0], "Saved:[/COLOR] [COLOR red][B]%s[/B][/COLOR]" % su if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]', yeslabel="[B][COLOR green]Save Data[/COLOR][/B]", nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
						wiz.setS(sa, m[0])
						wiz.log('[Import Data] %s: %s' % (who, str(m)), xbmc.LOGINFO)
					else: wiz.log('[Import Data] Declined Import(%s): %s' % (who, str(m)), xbmc.LOGINFO)
				else: wiz.log('[Import Data] Duplicate Entry(%s): %s' % (who, str(m))), xbmc.LOGINFO
			else: wiz.log('[Import Data] No Match(%s): %s' % (who, str(m)), xbmc.LOGINFO)

def activateTorBox(who):
	if TORBOXID[who]:
		if os.path.exists(TORBOXID[who]['path']):
			act     = TORBOXID[who]['activate']
			addonid = wiz.addonId(TORBOXID[who]['plugin'])
			if act == '': addonid.openSettings()
			else: xbmc.executebuiltin(TORBOXID[who]['activate'])
		else: DIALOG.ok(ADDONTITLE, '%s is not currently installed.' % TORBOXID[who]['name'])
	else:
		wiz.refresh()
		return
	check = 0
	while torboxUser(who) == None:
		if check == 30: break
		check += 1
		xbmc.sleep(1000)
	wiz.refresh()
