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
LINKSNAPPYFOLD  = os.path.join(ADDONDATA, 'LinkSnappy')
ICON            = os.path.join(PLUGIN,    'icon.png')
TODAY           = date.today()
TOMORROW        = TODAY + timedelta(days=1)
THREEDAYS       = TODAY + timedelta(days=3)
KEEPLINKSNAPPY  = wiz.getS('keeplinksnappy')
LINKSNAPPYSAVE  = wiz.getS('linksnappylastsave')
COLOR1          = uservar.COLOR1
COLOR2          = uservar.COLOR2
ORDER           = ['linksnappy']

LINKSNAPPYID = {
	'linksnappy': {
		'name'     : 'URL Resolver (LinkSnappy)',
		'plugin'   : 'script.module.urlresolver',
		'saved'    : 'linksnappylastsave',
		'path'     : os.path.join(ADDONS, 'script.module.urlresolver'),
		'icon'     : os.path.join(ADDONS, 'script.module.urlresolver', 'icon.png'),
		'fanart'   : os.path.join(ADDONS, 'script.module.urlresolver', 'fanart.jpg'),
		'file'     : os.path.join(LINKSNAPPYFOLD, 'linksnappy_data'),
		'settings' : os.path.join(ADDOND, 'script.module.urlresolver', 'settings.xml'),
		'default'  : 'LinkSnappyResolver_username',
		'data'     : ['LinkSnappyResolver_enabled', 'LinkSnappyResolver_priority', 'LinkSnappyResolver_autopick', 'LinkSnappyResolver_username', 'LinkSnappyResolver_password'],
		'activate' : ''}
}

def linksnappyUser(who):
	user = None
	if LINKSNAPPYID[who]:
		if os.path.exists(LINKSNAPPYID[who]['path']):
			try:
				add  = wiz.addonId(LINKSNAPPYID[who]['plugin'])
				user = add.getSetting(LINKSNAPPYID[who]['default'])
			except:
				pass
	return user

def linksnappyIt(do, who):
	if not os.path.exists(ADDONDATA): os.makedirs(ADDONDATA)
	if not os.path.exists(LINKSNAPPYFOLD):  os.makedirs(LINKSNAPPYFOLD)
	if who == 'all':
		for log in ORDER:
			if os.path.exists(LINKSNAPPYID[log]['path']):
				try:
					addonid = wiz.addonId(LINKSNAPPYID[log]['plugin'])
					default = LINKSNAPPYID[log]['default']
					user    = addonid.getSetting(default)
					if user == '' and do == 'update': continue
					updateLinkSnappy(do, log)
				except: pass
			else: wiz.log('[LinkSnappy Data] %s(%s) is not installed' % (LINKSNAPPYID[log]['name'], LINKSNAPPYID[log]['plugin']), xbmc.LOGERROR)
		wiz.setS('linksnappylastsave', str(THREEDAYS))
	else:
		if LINKSNAPPYID[who]:
			if os.path.exists(LINKSNAPPYID[who]['path']):
				updateLinkSnappy(do, who)
		else: wiz.log('[LinkSnappy Data] Invalid Entry: %s' % who, xbmc.LOGERROR)

def clearSaved(who, over=False):
	if who == 'all':
		for ls in LINKSNAPPYID:
			clearSaved(ls, True)
	elif LINKSNAPPYID[who]:
		file = LINKSNAPPYID[who]['file']
		if os.path.exists(file):
			os.remove(file)
			wiz.LogNotify('[COLOR %s]%s[/COLOR]' % (COLOR1, LINKSNAPPYID[who]['name']), '[COLOR %s]LinkSnappy Data: Removed![/COLOR]' % COLOR2, 2000, LINKSNAPPYID[who]['icon'])
		wiz.setS(LINKSNAPPYID[who]['saved'], '')
	if over == False: wiz.refresh()

def updateLinkSnappy(do, who):
	file     = LINKSNAPPYID[who]['file']
	settings = LINKSNAPPYID[who]['settings']
	data     = LINKSNAPPYID[who]['data']
	addonid  = wiz.addonId(LINKSNAPPYID[who]['plugin'])
	saved    = LINKSNAPPYID[who]['saved']
	default  = LINKSNAPPYID[who]['default']
	user     = addonid.getSetting(default)
	suser    = wiz.getS(saved)
	name     = LINKSNAPPYID[who]['name']
	icon     = LINKSNAPPYID[who]['icon']

	if do == 'update':
		if not user == '':
			try:
				with open(file, 'w') as f:
					for ls in data:
						f.write('<linksnappy>\n\t<id>%s</id>\n\t<value>%s</value>\n</linksnappy>\n' % (ls, addonid.getSetting(ls)))
					f.close()
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]LinkSnappy Data: Saved![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[LinkSnappy Data] Unable to Update %s (%s)" % (who, str(e)), xbmc.LOGERROR)
		else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]LinkSnappy Data: Not Registered![/COLOR]' % COLOR2, 2000, icon)
	elif do == 'restore':
		if os.path.exists(file):
			f = open(file, mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close()
			match = re.compile('<linksnappy><id>(.+?)</id><value>(.+?)</value></linksnappy>').findall(g)
			try:
				if len(match) > 0:
					for ls, value in match:
						addonid.setSetting(ls, value)
				user = addonid.getSetting(default)
				wiz.setS(saved, user)
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, name), '[COLOR %s]LinkSnappy: Restored![/COLOR]' % COLOR2, 2000, icon)
			except Exception as e:
				wiz.log("[LinkSnappy Data] Unable to Restore %s (%s)" % (who, str(e)), xbmc.LOGERROR)
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
				wiz.log("[LinkSnappy Data] Unable to Clear Addon %s (%s)" % (who, str(e)), xbmc.LOGERROR)
	wiz.refresh()

def autoUpdate(who):
	if who == 'all':
		for log in LINKSNAPPYID:
			if os.path.exists(LINKSNAPPYID[log]['path']):
				autoUpdate(log)
	elif LINKSNAPPYID[who]:
		if os.path.exists(LINKSNAPPYID[who]['path']):
			u  = linksnappyUser(who)
			su = wiz.getS(LINKSNAPPYID[who]['saved'])
			n  = LINKSNAPPYID[who]['name']
			if u == None or u == '': return
			elif su == '': linksnappyIt('update', who)
			elif not u == su:
				if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to save the [COLOR %s]LinkSnappy[/COLOR] data for [COLOR %s]%s[/COLOR]?" % (COLOR2, COLOR1, COLOR1, n), "Addon: [COLOR green][B]%s[/B][/COLOR]" % u, "Saved:[/COLOR] [COLOR red][B]%s[/B][/COLOR]" % su if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]', yeslabel="[B][COLOR green]Save Data[/COLOR][/B]", nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
					linksnappyIt('update', who)
			else: linksnappyIt('update', who)

def importlist(who):
	if who == 'all':
		for log in LINKSNAPPYID:
			if os.path.exists(LINKSNAPPYID[log]['file']):
				importlist(log)
	elif LINKSNAPPYID[who]:
		if os.path.exists(LINKSNAPPYID[who]['file']):
			d  = LINKSNAPPYID[who]['default']
			sa = LINKSNAPPYID[who]['saved']
			su = wiz.getS(sa)
			n  = LINKSNAPPYID[who]['name']
			f  = open(LINKSNAPPYID[who]['file'], mode='r'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close()
			m  = re.compile('<linksnappy><id>%s</id><value>(.+?)</value></linksnappy>' % d).findall(g)
			if len(m) > 0:
				if not m[0] == su:
					if DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to import the [COLOR %s]LinkSnappy[/COLOR] data for [COLOR %s]%s[/COLOR]?" % (COLOR2, COLOR1, COLOR1, n), "File: [COLOR green][B]%s[/B][/COLOR]" % m[0], "Saved:[/COLOR] [COLOR red][B]%s[/B][/COLOR]" % su if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]', yeslabel="[B][COLOR green]Save Data[/COLOR][/B]", nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
						wiz.setS(sa, m[0])
						wiz.log('[Import Data] %s: %s' % (who, str(m)), xbmc.LOGINFO)
					else: wiz.log('[Import Data] Declined Import(%s): %s' % (who, str(m)), xbmc.LOGINFO)
				else: wiz.log('[Import Data] Duplicate Entry(%s): %s' % (who, str(m))), xbmc.LOGINFO
			else: wiz.log('[Import Data] No Match(%s): %s' % (who, str(m)), xbmc.LOGINFO)

def activateLinkSnappy(who):
	if LINKSNAPPYID[who]:
		if os.path.exists(LINKSNAPPYID[who]['path']):
			act     = LINKSNAPPYID[who]['activate']
			addonid = wiz.addonId(LINKSNAPPYID[who]['plugin'])
			if act == '': addonid.openSettings()
			else: xbmc.executebuiltin(LINKSNAPPYID[who]['activate'])
		else: DIALOG.ok(ADDONTITLE, '%s is not currently installed.' % LINKSNAPPYID[who]['name'])
	else:
		wiz.refresh()
		return
	check = 0
	while linksnappyUser(who) == None:
		if check == 30: break
		check += 1
		xbmc.sleep(1000)
	wiz.refresh()
