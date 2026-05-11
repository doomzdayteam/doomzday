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
TRAKTFOLD      = os.path.join(ADDONDATA, 'Trakt')
ICON           = os.path.join(PLUGIN,    'icon.png')
TODAY          = date.today()
TOMORROW       = TODAY + timedelta(days=1)
THREEDAYS      = TODAY + timedelta(days=3)
KEEPTRAKT      = wiz.getS('keeptrakt')
TRAKTSAVE      = wiz.getS('traktlastsave')
COLOR1         = uservar.COLOR1
COLOR2         = uservar.COLOR2
ORDER          = ['trakt']

TRAKTID = {
	'trakt': {
		'name'     : 'Trakt',
		'plugin'   : 'script.trakt',
		'saved'    : 'trakt',
		'path'     : os.path.join(ADDONS, 'script.trakt'),
		'icon'     : os.path.join(ADDONS, 'script.trakt', 'icon.png'),
		'fanart'   : os.path.join(ADDONS, 'script.trakt', 'fanart.jpg'),
		'file'     : os.path.join(TRAKTFOLD, 'trakt_trakt'),
		'settings' : os.path.join(ADDOND, 'script.trakt', 'settings.xml'),
		'default'  : 'user',
		'data'     : ['user', 'Auth_Info', 'authorization'],
		'activate' : 'RunScript(script.trakt, action=auth_info)'}
}

def traktUser(who):
	user=None
	if TRAKTID[who]:
		if os.path.exists(TRAKTID[who]['path']):
			try:
				add = wiz.addonId(TRAKTID[who]['plugin'])
				user = add.getSetting(TRAKTID[who]['default'])
			except:
				return None
	return user

def traktIt(do, who):
	if not os.path.exists(ADDONDATA): os.makedirs(ADDONDATA)
	if not os.path.exists(TRAKTFOLD): os.makedirs(TRAKTFOLD)
	if who == 'all':
		for log in ORDER:
			if os.path.exists(TRAKTID[log]['path']):
				try:
					addonid   = wiz.addonId(TRAKTID[log]['plugin'])
					default   = TRAKTID[log]['default']
					user      = addonid.getSetting(default)
					if user == '' and do == 'update': continue
					updateTrakt(do, log)
				except: pass
			else: wiz.log('[Trakt Data] %s(%s) is not installed' % (TRAKTID[log]['name'],TRAKTID[log]['plugin']), xbmc.LOGERROR)
		wiz.setS('traktlastsave', str(THREEDAYS))
	else:
		if TRAKTID[who]:
			if os.path.exists(TRAKTID[who]['path']):
				updateTrakt(do, who)
		else: wiz.log('[Trakt Data] Invalid Entry: %s' % who, xbmc.LOGERROR)

def clearSaved(who, over=False):
	if who == 'all':
		for trakt in TRAKTID:
			clearSaved(trakt,  True)
	elif TRAKTID[who]:
		file = TRAKTID[who]['file']
		if os.path.exists(file):
			os.remove(file)
			wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, TRAKTID[who]['name']),'[COLOR %s]Trakt Data: Removed![/COLOR]' % COLOR2, 2000, TRAKTID[who]['icon'])
		wiz.setS(TRAKTID[who]['saved'], '')
	if over == False: wiz.refresh()

def updateTrakt(do, who):
	file      = TRAKTID[who]['file']
	settings  = TRAKTID[who]['settings']
	data      = TRAKTID[who]['data']
	addonid   = wiz.addonId(TRAKTID[who]['plugin'])
	saved     = TRAKTID[who]['saved']
	default   = TRAKTID[who]['default']
	user      = addonid.getSetting(default)
	suser     = wiz.getS(saved)
	name      = TRAKTID[who]['name']
	icon      = TRAKTID[who]['icon']

	if do == 'update':
		if not user == '':
			try:
				with open(file, 'w') as f:
					for trakt in data: 
						f.write('<trakt>\n\t<id>%s</id>\n\t<value>%s</value>\n</trakt>\n' % (trakt, addonid.getSetting(trakt)))
					f.close()
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]Trakt Data: Saved![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[Trakt Data] Unable to Update %s (%s)" % (who, str(e)), xbmc.LOGERROR)
		else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]Trakt Data: Not Registered![/COLOR]' % COLOR2, 2000, icon)
	elif do == 'restore':
		if os.path.exists(file):
			f = open(file,mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close();
			match = re.compile('<trakt><id>(.+?)</id><value>(.+?)</value></trakt>').findall(g)
			try:
				if len(match) > 0:
					for trakt, value in match:
						addonid.setSetting(trakt, value)
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]Trakt: Restored![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[Trakt Data] Unable to Restore %s (%s)" % (who, str(e)), xbmc.LOGERROR)
		#else: wiz.LogNotify(name,'Trakt Data: [COLOR red]Not Found![/COLOR]', 2000, icon)
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
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name),'[COLOR %s]Addon Data: Cleared![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[Trakt Data] Unable to Clear Addon %s (%s)" % (who, str(e)), xbmc.LOGERROR)
	wiz.refresh()

def autoUpdate(who):
	if who == 'all':
		for log in TRAKTID:
			if os.path.exists(TRAKTID[log]['path']):
				autoUpdate(log)
	elif TRAKTID[who]:
		if os.path.exists(TRAKTID[who]['path']):
			u  = traktUser(who)
			su = wiz.getS(TRAKTID[who]['saved'])
			n = TRAKTID[who]['name']
			if u == None or u == '': return
			elif su == '': traktIt('update', who)
			elif not u == su:
					if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to save the [COLOR %s]Trakt[/COLOR] data for [COLOR %s]%s[/COLOR]?[CR]Addon: [COLOR green][B]%s[/B][/COLOR][CR]Saved: [COLOR red][B]%s[/B][/COLOR]" % (COLOR2, COLOR1, COLOR1, n, u, su if su != '' else 'None'), yeslabel="[B][COLOR green]Save Data[/COLOR][/B]", nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
						traktIt('update', who)
			else: traktIt('update', who)

def importlist(who):
	if who == 'all':
		for log in TRAKTID:
			if os.path.exists(TRAKTID[log]['file']):
				importlist(log)
	elif TRAKTID[who]:
		if os.path.exists(TRAKTID[who]['file']):
			d  = TRAKTID[who]['default']
			sa = TRAKTID[who]['saved']
			su = wiz.getS(sa)
			n  = TRAKTID[who]['name']
			f  = open(TRAKTID[who]['file'],mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close();
			m  = re.compile('<trakt><id>%s</id><value>(.+?)</value></trakt>' % d).findall(g)
			if len(m) > 0:
				if not m[0] == su:
					if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to import the [COLOR %s]Trakt[/COLOR] data for [COLOR %s]%s[/COLOR]?[CR]File: [COLOR green][B]%s[/B][/COLOR][CR]Saved: [COLOR red][B]%s[/B][/COLOR]" % (COLOR2, COLOR1, COLOR1, n, m[0], su if su != '' else 'None'), yeslabel="[B]Save Data[/B]", nolabel="[B]No Cancel[/B]"):
						wiz.setS(sa, m[0])
						wiz.log('[Import Data] %s: %s' % (who, str(m)), xbmc.LOGINFO)
					else: wiz.log('[Import Data] Declined Import(%s): %s' % (who, str(m)), xbmc.LOGINFO)
				else: wiz.log('[Import Data] Duplicate Entry(%s): %s' % (who, str(m)), xbmc.LOGINFO)
			else: wiz.log('[Import Data] No Match(%s): %s' % (who, str(m)), xbmc.LOGINFO)

def activateTrakt(who):
	if TRAKTID[who]:
		if os.path.exists(TRAKTID[who]['path']): 
			act     = TRAKTID[who]['activate']
			addonid = wiz.addonId(TRAKTID[who]['plugin'])
			if act == '': addonid.openSettings()
			else: url = xbmc.executebuiltin(TRAKTID[who]['activate'])
		else: DIALOG.ok(ADDONTITLE, '%s is not currently installed.' % TRAKTID[who]['name'])
	else: 
		wiz.refresh()
		return
	check = 0
	while traktUser(who) == None:
		if check == 30: break
		check += 1
		time.sleep(10)
	if traktUser(who) is not None:
		name = TRAKTID[who]['name']
		icon = TRAKTID[who]['icon'] if os.path.exists(TRAKTID[who]['path']) else ICON
		wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]Trakt: Authorized![/COLOR]' % COLOR2, 4000, icon)
	wiz.refresh()
