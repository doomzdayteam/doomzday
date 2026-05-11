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

ADDON_ID        = uservar.ADDON_ID
ADDONTITLE      = uservar.ADDONTITLE
ADDON           = wiz.addonId(ADDON_ID)
DIALOG          = xbmcgui.Dialog()
HOME            = xbmcvfs.translatePath('special://home/')
ADDONS          = os.path.join(HOME,      'addons')
USERDATA        = os.path.join(HOME,      'userdata')
PLUGIN          = os.path.join(ADDONS,    ADDON_ID)
PACKAGES        = os.path.join(ADDONS,    'packages')
ADDONDATA       = os.path.join(USERDATA,  'addon_data', ADDON_ID)
ADDOND          = os.path.join(USERDATA,  'addon_data')
ALLDEBRFOLD     = os.path.join(ADDONDATA, 'AllDebrid')
ICON            = os.path.join(PLUGIN,    'icon.png')
TODAY           = date.today()
TOMORROW        = TODAY + timedelta(days=1)
THREEDAYS       = TODAY + timedelta(days=3)
KEEPALLDEBRID   = wiz.getS('keepalldebrid')
ALLDEBRIDSAVE   = wiz.getS('alldebridlastsave')
COLOR1          = uservar.COLOR1
COLOR2          = uservar.COLOR2
ORDER           = ['alldebrid']

ALLDEBRIDID = {
	'alldebrid': {
		'name'     : 'URL Resolver (AllDebrid)',
		'plugin'   : 'script.module.urlresolver',
		'saved'    : 'alldebridlastsave',
		'path'     : os.path.join(ADDONS, 'script.module.urlresolver'),
		'icon'     : os.path.join(ADDONS, 'script.module.urlresolver', 'icon.png'),
		'fanart'   : os.path.join(ADDONS, 'script.module.urlresolver', 'fanart.jpg'),
		'file'     : os.path.join(ALLDEBRFOLD, 'alldebrid_data'),
		'settings' : os.path.join(ADDOND, 'script.module.urlresolver', 'settings.xml'),
		'default'  : 'AllDebridResolver_token',
		'data'     : ['AllDebridResolver_enabled', 'AllDebridResolver_priority', 'AllDebridResolver_autopick', 'AllDebridResolver_token'],
		'activate' : 'RunPlugin(plugin://script.module.urlresolver/?mode=auth_alldebrid)'}
}

def alldebridUser(who):
	user = None
	if ALLDEBRIDID[who]:
		if os.path.exists(ALLDEBRIDID[who]['path']):
			try:
				add  = wiz.addonId(ALLDEBRIDID[who]['plugin'])
				user = add.getSetting(ALLDEBRIDID[who]['default'])
			except:
				pass
	return user

def alldebridIt(do, who):
	if not os.path.exists(ADDONDATA): os.makedirs(ADDONDATA)
	if not os.path.exists(ALLDEBRFOLD):  os.makedirs(ALLDEBRFOLD)
	if who == 'all':
		for log in ORDER:
			if os.path.exists(ALLDEBRIDID[log]['path']):
				try:
					addonid = wiz.addonId(ALLDEBRIDID[log]['plugin'])
					default = ALLDEBRIDID[log]['default']
					user    = addonid.getSetting(default)
					if user == '' and do == 'update': continue
					updateAllDebrid(do, log)
				except: pass
			else: wiz.log('[AllDebrid Data] %s(%s) is not installed' % (ALLDEBRIDID[log]['name'], ALLDEBRIDID[log]['plugin']), xbmc.LOGERROR)
		wiz.setS('alldebridlastsave', str(THREEDAYS))
	else:
		if ALLDEBRIDID[who]:
			if os.path.exists(ALLDEBRIDID[who]['path']):
				updateAllDebrid(do, who)
		else: wiz.log('[AllDebrid Data] Invalid Entry: %s' % who, xbmc.LOGERROR)

def clearSaved(who, over=False):
	if who == 'all':
		for ad in ALLDEBRIDID:
			clearSaved(ad, True)
	elif ALLDEBRIDID[who]:
		file = ALLDEBRIDID[who]['file']
		if os.path.exists(file):
			os.remove(file)
			wiz.LogNotify('[COLOR %s]%s[/COLOR]' % (COLOR1, ALLDEBRIDID[who]['name']), '[COLOR %s]AllDebrid Data: Removed![/COLOR]' % COLOR2, 2000, ALLDEBRIDID[who]['icon'])
		wiz.setS(ALLDEBRIDID[who]['saved'], '')
	if over == False: wiz.refresh()

def updateAllDebrid(do, who):
	file     = ALLDEBRIDID[who]['file']
	settings = ALLDEBRIDID[who]['settings']
	data     = ALLDEBRIDID[who]['data']
	addonid  = wiz.addonId(ALLDEBRIDID[who]['plugin'])
	saved    = ALLDEBRIDID[who]['saved']
	default  = ALLDEBRIDID[who]['default']
	user     = addonid.getSetting(default)
	suser    = wiz.getS(saved)
	name     = ALLDEBRIDID[who]['name']
	icon     = ALLDEBRIDID[who]['icon']

	if do == 'update':
		if not user == '':
			try:
				with open(file, 'w') as f:
					for ad in data:
						f.write('<alldebrid>\n\t<id>%s</id>\n\t<value>%s</value>\n</alldebrid>\n' % (ad, addonid.getSetting(ad)))
					f.close()
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]AllDebrid Data: Saved![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[AllDebrid Data] Unable to Update %s (%s)" % (who, str(e)), xbmc.LOGERROR)
		else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]AllDebrid Data: Not Registered![/COLOR]' % COLOR2, 2000, icon)
	elif do == 'restore':
		if os.path.exists(file):
			f = open(file, mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close()
			match = re.compile('<alldebrid><id>(.+?)</id><value>(.+?)</value></alldebrid>').findall(g)
			try:
				if len(match) > 0:
					for ad, value in match:
						addonid.setSetting(ad, value)
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]AllDebrid: Restored![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[AllDebrid Data] Unable to Restore %s (%s)" % (who, str(e)), xbmc.LOGERROR)
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
				wiz.log("[AllDebrid Data] Unable to Clear Addon %s (%s)" % (who, str(e)), xbmc.LOGERROR)
	wiz.refresh()

def autoUpdate(who):
	if who == 'all':
		for log in ALLDEBRIDID:
			if os.path.exists(ALLDEBRIDID[log]['path']):
				autoUpdate(log)
	elif ALLDEBRIDID[who]:
		if os.path.exists(ALLDEBRIDID[who]['path']):
			u  = alldebridUser(who)
			su = wiz.getS(ALLDEBRIDID[who]['saved'])
			n  = ALLDEBRIDID[who]['name']
			if u == None or u == '': return
			elif su == '': alldebridIt('update', who)
			elif not u == su:
				if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to save the [COLOR %s]AllDebrid[/COLOR] data for [COLOR %s]%s[/COLOR]?" % (COLOR2, COLOR1, COLOR1, n), "Addon: [COLOR green][B]%s[/B][/COLOR]" % u, "Saved:[/COLOR] [COLOR red][B]%s[/B][/COLOR]" % su if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]', yeslabel="[B][COLOR green]Save Data[/COLOR][/B]", nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
					alldebridIt('update', who)
			else: alldebridIt('update', who)

def importlist(who):
	if who == 'all':
		for log in ALLDEBRIDID:
			if os.path.exists(ALLDEBRIDID[log]['file']):
				importlist(log)
	elif ALLDEBRIDID[who]:
		if os.path.exists(ALLDEBRIDID[who]['file']):
			d  = ALLDEBRIDID[who]['default']
			sa = ALLDEBRIDID[who]['saved']
			su = wiz.getS(sa)
			n  = ALLDEBRIDID[who]['name']
			f  = open(ALLDEBRIDID[who]['file'], mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close()
			m  = re.compile('<alldebrid><id>%s</id><value>(.+?)</value></alldebrid>' % d).findall(g)
			if len(m) > 0:
				if not m[0] == su:
					if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to import the [COLOR %s]AllDebrid[/COLOR] data for [COLOR %s]%s[/COLOR]?" % (COLOR2, COLOR1, COLOR1, n), "File: [COLOR green][B]%s[/B][/COLOR]" % m[0], "Saved:[/COLOR] [COLOR red][B]%s[/B][/COLOR]" % su if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]', yeslabel="[B][COLOR green]Save Data[/COLOR][/B]", nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
						wiz.setS(sa, m[0])
						wiz.log('[Import Data] %s: %s' % (who, str(m)), xbmc.LOGINFO)
					else: wiz.log('[Import Data] Declined Import(%s): %s' % (who, str(m)), xbmc.LOGINFO)
				else: wiz.log('[Import Data] Duplicate Entry(%s): %s' % (who, str(m))), xbmc.LOGINFO
			else: wiz.log('[Import Data] No Match(%s): %s' % (who, str(m)), xbmc.LOGINFO)

def activateAllDebrid(who):
	if ALLDEBRIDID[who]:
		if os.path.exists(ALLDEBRIDID[who]['path']):
			act     = ALLDEBRIDID[who]['activate']
			addonid = wiz.addonId(ALLDEBRIDID[who]['plugin'])
			if act == '': addonid.openSettings()
			else: xbmc.executebuiltin(ALLDEBRIDID[who]['activate'])
		else: DIALOG.ok(ADDONTITLE, '%s is not currently installed.' % ALLDEBRIDID[who]['name'])
	else:
		wiz.refresh()
		return
	check = 0
	while alldebridUser(who) == None:
		if check == 30: break
		check += 1
		xbmc.sleep(1000)
	wiz.refresh()
