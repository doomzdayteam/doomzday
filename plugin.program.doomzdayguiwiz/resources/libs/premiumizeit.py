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
PREMFOLD       = os.path.join(ADDONDATA, 'Premiumize')
ICON           = os.path.join(PLUGIN,    'icon.png')
TODAY          = date.today()
TOMORROW       = TODAY + timedelta(days=1)
THREEDAYS      = TODAY + timedelta(days=3)
KEEPPREMIUMIZE = wiz.getS('keeppremiumize')
PREMSAVE       = wiz.getS('premiumizelastsave')
COLOR1         = uservar.COLOR1
COLOR2         = uservar.COLOR2
ORDER          = ['premiumize']

PREMIUMIZEID = {
	'premiumize': {
		'name'     : 'Premiumize.me',
		'plugin'   : 'service.premiumize.me',
		'saved'    : 'premiumizelastsave',
		'path'     : os.path.join(ADDONS, 'service.premiumize.me'),
		'icon'     : os.path.join(ADDONS, 'service.premiumize.me', 'icon.png'),
		'fanart'   : os.path.join(ADDONS, 'service.premiumize.me', 'fanart.jpg'),
		'file'     : os.path.join(PREMFOLD, 'premiumize_data'),
		'settings' : os.path.join(ADDOND, 'service.premiumize.me', 'settings.xml'),
		'default'  : 'apikey',
		'data'     : ['apikey'],
		'activate' : ''}
}

def premiumizeUser(who):
	user = None
	if PREMIUMIZEID[who]:
		if os.path.exists(PREMIUMIZEID[who]['path']):
			try:
				add = wiz.addonId(PREMIUMIZEID[who]['plugin'])
				user = add.getSetting(PREMIUMIZEID[who]['default'])
			except:
				pass
	return user

def premiumizeIt(do, who):
	if not os.path.exists(ADDONDATA): os.makedirs(ADDONDATA)
	if not os.path.exists(PREMFOLD):  os.makedirs(PREMFOLD)
	if who == 'all':
		for log in ORDER:
			if os.path.exists(PREMIUMIZEID[log]['path']):
				try:
					addonid = wiz.addonId(PREMIUMIZEID[log]['plugin'])
					default = PREMIUMIZEID[log]['default']
					user    = addonid.getSetting(default)
					if user == '' and do == 'update': continue
					updatePremiumize(do, log)
				except: pass
			else: wiz.log('[Premiumize Data] %s(%s) is not installed' % (PREMIUMIZEID[log]['name'], PREMIUMIZEID[log]['plugin']), xbmc.LOGERROR)
		wiz.setS('premiumizelastsave', str(THREEDAYS))
	else:
		if PREMIUMIZEID[who]:
			if os.path.exists(PREMIUMIZEID[who]['path']):
				updatePremiumize(do, who)
		else: wiz.log('[Premiumize Data] Invalid Entry: %s' % who, xbmc.LOGERROR)

def clearSaved(who, over=False):
	if who == 'all':
		for prem in PREMIUMIZEID:
			clearSaved(prem, True)
	elif PREMIUMIZEID[who]:
		file = PREMIUMIZEID[who]['file']
		if os.path.exists(file):
			os.remove(file)
			wiz.LogNotify('[COLOR %s]%s[/COLOR]' % (COLOR1, PREMIUMIZEID[who]['name']), '[COLOR %s]Premiumize Data: Removed![/COLOR]' % COLOR2, 2000, PREMIUMIZEID[who]['icon'])
		wiz.setS(PREMIUMIZEID[who]['saved'], '')
	if over == False: wiz.refresh()

def updatePremiumize(do, who):
	file     = PREMIUMIZEID[who]['file']
	settings = PREMIUMIZEID[who]['settings']
	data     = PREMIUMIZEID[who]['data']
	addonid  = wiz.addonId(PREMIUMIZEID[who]['plugin'])
	saved    = PREMIUMIZEID[who]['saved']
	default  = PREMIUMIZEID[who]['default']
	user     = addonid.getSetting(default)
	suser    = wiz.getS(saved)
	name     = PREMIUMIZEID[who]['name']
	icon     = PREMIUMIZEID[who]['icon']

	if do == 'update':
		if not user == '':
			try:
				with open(file, 'w') as f:
					for prem in data:
						f.write('<premiumize>\n\t<id>%s</id>\n\t<value>%s</value>\n</premiumize>\n' % (prem, addonid.getSetting(prem)))
					f.close()
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]Premiumize Data: Saved![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[Premiumize Data] Unable to Update %s (%s)" % (who, str(e)), xbmc.LOGERROR)
		else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]Premiumize Data: Not Registered![/COLOR]' % COLOR2, 2000, icon)
	elif do == 'restore':
		if os.path.exists(file):
			f = open(file, mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close()
			match = re.compile('<premiumize><id>(.+?)</id><value>(.+?)</value></premiumize>').findall(g)
			try:
				if len(match) > 0:
					for prem, value in match:
						addonid.setSetting(prem, value)
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]Premiumize: Restored![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[Premiumize Data] Unable to Restore %s (%s)" % (who, str(e)), xbmc.LOGERROR)
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
				wiz.log("[Premiumize Data] Unable to Clear Addon %s (%s)" % (who, str(e)), xbmc.LOGERROR)
	wiz.refresh()

def autoUpdate(who):
	if who == 'all':
		for log in PREMIUMIZEID:
			if os.path.exists(PREMIUMIZEID[log]['path']):
				autoUpdate(log)
	elif PREMIUMIZEID[who]:
		if os.path.exists(PREMIUMIZEID[who]['path']):
			u  = premiumizeUser(who)
			su = wiz.getS(PREMIUMIZEID[who]['saved'])
			n  = PREMIUMIZEID[who]['name']
			if u == None or u == '': return
			elif su == '': premiumizeIt('update', who)
			elif not u == su:
				if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to save the [COLOR %s]Premiumize[/COLOR] data for [COLOR %s]%s[/COLOR]?" % (COLOR2, COLOR1, COLOR1, n), "Addon: [COLOR green][B]%s[/B][/COLOR]" % u, "Saved:[/COLOR] [COLOR red][B]%s[/B][/COLOR]" % su if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]', yeslabel="[B][COLOR green]Save Data[/COLOR][/B]", nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
					premiumizeIt('update', who)
			else: premiumizeIt('update', who)

def importlist(who):
	if who == 'all':
		for log in PREMIUMIZEID:
			if os.path.exists(PREMIUMIZEID[log]['file']):
				importlist(log)
	elif PREMIUMIZEID[who]:
		if os.path.exists(PREMIUMIZEID[who]['file']):
			d  = PREMIUMIZEID[who]['default']
			sa = PREMIUMIZEID[who]['saved']
			su = wiz.getS(sa)
			n  = PREMIUMIZEID[who]['name']
			f  = open(PREMIUMIZEID[who]['file'], mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close()
			m  = re.compile('<premiumize><id>%s</id><value>(.+?)</value></premiumize>' % d).findall(g)
			if len(m) > 0:
				if not m[0] == su:
					if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to import the [COLOR %s]Premiumize[/COLOR] data for [COLOR %s]%s[/COLOR]?" % (COLOR2, COLOR1, COLOR1, n), "File: [COLOR green][B]%s[/B][/COLOR]" % m[0], "Saved:[/COLOR] [COLOR red][B]%s[/B][/COLOR]" % su if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]', yeslabel="[B][COLOR green]Save Data[/COLOR][/B]", nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
						wiz.setS(sa, m[0])
						wiz.log('[Import Data] %s: %s' % (who, str(m)), xbmc.LOGINFO)
					else: wiz.log('[Import Data] Declined Import(%s): %s' % (who, str(m)), xbmc.LOGINFO)
				else: wiz.log('[Import Data] Duplicate Entry(%s): %s' % (who, str(m))), xbmc.LOGINFO
			else: wiz.log('[Import Data] No Match(%s): %s' % (who, str(m)), xbmc.LOGINFO)

def activatePremiumize(who):
	if PREMIUMIZEID[who]:
		if os.path.exists(PREMIUMIZEID[who]['path']):
			act     = PREMIUMIZEID[who]['activate']
			addonid = wiz.addonId(PREMIUMIZEID[who]['plugin'])
			if act == '': addonid.openSettings()
			else: xbmc.executebuiltin(PREMIUMIZEID[who]['activate'])
		else: DIALOG.ok(ADDONTITLE, '%s is not currently installed.' % PREMIUMIZEID[who]['name'])
	else:
		wiz.refresh()
		return
	check = 0
	while premiumizeUser(who) == None:
		if check == 30: break
		check += 1
		time.sleep(10)
	if premiumizeUser(who) is not None:
		name = PREMIUMIZEID[who]['name']
		icon = PREMIUMIZEID[who]['icon'] if os.path.exists(PREMIUMIZEID[who]['path']) else ICON
		wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]Premiumize: Authorized![/COLOR]' % COLOR2, 4000, icon)
	wiz.refresh()
