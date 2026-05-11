############################################################################
#                             /T /I                                        #
#                              / |/ | .-~/                                 #
#                          T\ Y  I  |/  /  _                               #
#         /T               | \I  |  I  Y.-~/                               #
#        I l   /I       T\ |  |  l  |  T  /                                #
#     T\ |  \ Y l  /T   | \I  l   \ `  l Y       If your going to copy     #
# __  | \l   \l  \I l __l  l   \   `  _. |       this addon just           #
# \ ~-l  `\   `\  \  \ ~\  \   `. .-~   |        give credit!              #
#  \   ~-. "-.  `  \  ^._ ^. "-.  /  \   |                                 #
#.--~-._  ~-  `  _  ~-_.-"-." ._ /._ ." ./        Stop Deleting the        #
# >--.  ~-.   ._  ~>-"    "\   7   7   ]          credits file!            #
#^.___~"--._    ~-{  .-~ .  `\ Y . /    |                                  #
# <__ ~"-.  ~       /_/   \   \I  Y   : |                                  #
#   ^-.__           ~(_/   \   >._:   | l______                            #
#       ^--.,___.-~"  /_/   !  `-.~"--l_ /     ~"-.                        #
#              (_/ .  ~(   /'     "~"--,Y   -=b-. _)                       #
#               (_/ .  \  :           / l      c"~o \                      #
#                \ /    `.    .     .^   \_.-~"~--.  )                     #
#                 (_/ .   `  /     /       !       )/                      #
#                  / / _.   '.   .':      /        '                       #
#                  ~(_/ .   /    _  `  .-<_                                #
#                    /_/ . ' .-~" `.  / \  \          ,z=.  Surfacingx     #
#                    ~( /   '  :   | K   "-.~-.______//   Original Author  #
#                      "-,.    l   I/ \_    __{--->._(==.                  #
#                       //(     \  <    ~"~"     //                        #
#                      /' /\     \  \     ,v=.  ((     Fire TV Guru        #
#                    .^. / /\     "  }__ //===-  `    PyXBMCt LaYOUt       #
#                   / / ' '  "-.,__ {---(==-                               #
#                 .^ '       :  T  ~"   ll                                 #
#                / .  .  . : | :!        \                                 #
#               (_/  /   | | j-"          ~^                               #
#                 ~-<_(_.^-~"                                              #
#                                                                          #
#                  Copyright (C) One of those Years....                    #
#                                                                          #
#  This program is free software: you can redistribute it and/or modify    #
#  it under the terms of the GNU General Public License as published by    #
#  the Free Software Foundation, either version 3 of the License, or       #
#  (at your option) any later version.                                     #
#                                                                          #
#  This program is distributed in the hope that it will be useful,         #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#  GNU General Public License for more details.                            #
#                                                                          #
############################################################################
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, os, sys, xbmcvfs, glob
import shutil
import urllib.request, urllib.error, urllib.parse
import http.client
import re
import zipfile
import uservar
import fnmatch
from datetime import date, timedelta
from urllib.parse import parse_qsl
from resources.libs import extract, downloader, notify, debridit, traktit, loginit, premiumizeit, alldebridit, torboxit, linksnappit, net, skinSwitch, uploadLog, yt, wizard as wiz, addonwindow as pyxbmct


ADDON_ID         = uservar.ADDON_ID
ADDONTITLE       = uservar.ADDONTITLE
ADDON            = wiz.addonId(ADDON_ID)
VERSION          = wiz.addonInfo(ADDON_ID,'version')
ADDONPATH        = wiz.addonInfo(ADDON_ID, 'path')
DIALOG           = xbmcgui.Dialog()
DP               = xbmcgui.DialogProgress()
HOME             = xbmcvfs.translatePath('special://home/')
LOG              = xbmcvfs.translatePath('special://logpath/')
PROFILE          = xbmcvfs.translatePath('special://profile/')
TEMPDIR          = xbmcvfs.translatePath('special://temp')
ADDONS           = os.path.join(HOME,      'addons')
USERDATA         = os.path.join(HOME,      'userdata')
PLUGIN           = os.path.join(ADDONS,    ADDON_ID)
PACKAGES         = os.path.join(ADDONS,    'packages')
ADDOND           = os.path.join(USERDATA,  'addon_data')
ADDONDATA        = os.path.join(USERDATA,  'addon_data', ADDON_ID)
ADVANCED         = os.path.join(USERDATA,  'advancedsettings.xml')
SOURCES          = os.path.join(USERDATA,  'sources.xml')
FAVOURITES       = os.path.join(USERDATA,  'favourites.xml')
PROFILES         = os.path.join(USERDATA,  'profiles.xml')
GUISETTINGS      = os.path.join(USERDATA,  'guisettings.xml')
THUMBS           = os.path.join(USERDATA,  'Thumbnails')
DATABASE         = os.path.join(USERDATA,  'Database')
FANART           = os.path.join(PLUGIN,    'fanart.jpg')
ICON             = os.path.join(PLUGIN,    'icon.png')
ART              = os.path.join(PLUGIN,    'resources', 'art')
WIZLOG           = os.path.join(ADDONDATA, 'wizard.log')
SPEEDTESTFOLD    = os.path.join(ADDONDATA, 'SpeedTest')
ARCHIVE_CACHE    = os.path.join(TEMPDIR,   'archive_cache')
SKIN             = xbmc.getSkinDir()
BUILDNAME        = wiz.getS('buildname')
DEFAULTSKIN      = wiz.getS('defaultskin')
DEFAULTNAME      = wiz.getS('defaultskinname')
DEFAULTIGNORE    = wiz.getS('defaultskinignore')
BUILDVERSION     = wiz.getS('buildversion')
BUILDTHEME       = wiz.getS('buildtheme')
BUILDLATEST      = wiz.getS('latestversion')
SHOW19           = wiz.getS('show19')
SHOW20           = wiz.getS('show20')
SHOW21           = wiz.getS('show21')
SHOWADULT        = wiz.getS('adult')
SHOWMAINT        = wiz.getS('showmaint')
AUTOCLEANUP      = wiz.getS('autoclean')
AUTOCACHE        = wiz.getS('clearcache')
AUTOPACKAGES     = wiz.getS('clearpackages')
AUTOTHUMBS       = wiz.getS('clearthumbs')
AUTOFEQ          = wiz.getS('autocleanfeq')
AUTONEXTRUN      = wiz.getS('nextautocleanup')
INCLUDEVIDEO     = wiz.getS('includevideo')
INCLUDEALL       = wiz.getS('includeall')
SEPERATE         = wiz.getS('seperate')
NOTIFY           = wiz.getS('notify')
NOTEID           = wiz.getS('noteid')
NOTEDISMISS      = wiz.getS('notedismiss')
TRAKTSAVE        = wiz.getS('traktlastsave')
REALSAVE         = wiz.getS('debridlastsave')
LOGINSAVE        = wiz.getS('loginlastsave')
KEEPFAVS         = wiz.getS('keepfavourites')
FAVSsave         = wiz.getS('favouriteslastsave')
KEEPSOURCES      = wiz.getS('keepsources')
KEEPPROFILES     = wiz.getS('keepprofiles')
KEEPADVANCED     = wiz.getS('keepadvanced')
KEEPREPOS        = wiz.getS('keeprepos')
KEEPSUPER        = wiz.getS('keepsuper')
KEEPWHITELIST    = wiz.getS('keepwhitelist')
KEEPTRAKT        = wiz.getS('keeptrakt')
KEEPREAL         = wiz.getS('keepdebrid')
KEEPPREMIUMIZE   = wiz.getS('keeppremiumize')
PREMIUMIZESAVE   = wiz.getS('premiumizelastsave')
KEEPALLDEBRID    = wiz.getS('keepalldebrid')
ALLDEBRIDSAVE    = wiz.getS('alldebridlastsave')
KEEPTORBOX       = wiz.getS('keeptorbox')
TORBOXSAVE       = wiz.getS('torboxlastsave')
KEEPLINKSNAPPY   = wiz.getS('keeplinksnappy')
LINKSNAPPYSAVE   = wiz.getS('linksnappylastsave')
KEEPLOGIN        = wiz.getS('keeplogin')
DEVELOPER        = wiz.getS('developer')
BACKUPLOCATION   = ADDON.getSetting('path') if not ADDON.getSetting('path') == '' else 'special://home/'
BACKUPROMS       = wiz.getS('rompath')
MYBUILDS         = os.path.join(BACKUPLOCATION, 'My_Builds', '')
AUTOFEQ          = int(float(AUTOFEQ)) if AUTOFEQ.isdigit() else 0
TODAY            = date.today()
TOMORROW         = TODAY + timedelta(days=1)
THREEDAYS        = TODAY + timedelta(days=3)
KODIV          = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
MCNAME           = wiz.mediaCenter()
EXCLUDES         = uservar.EXCLUDES
CACHETEXT        = uservar.CACHETEXT
CACHEAGE         = uservar.CACHEAGE if str(uservar.CACHEAGE).isdigit() else 30
BUILDFILE        = uservar.BUILDFILE
UPDATECHECK      = uservar.UPDATECHECK if str(uservar.UPDATECHECK).isdigit() else 1
NEXTCHECK        = TODAY + timedelta(days=UPDATECHECK)
NOTIFICATION     = uservar.NOTIFICATION
ENABLE           = uservar.ENABLE
HEADERMESSAGE    = uservar.HEADERMESSAGE
BUILDERNAME      = uservar.BUILDERNAME  
HIDECONTACT      = uservar.HIDECONTACT
CONTACT          = uservar.CONTACT
CONTACTICON      = uservar.CONTACTICON if not uservar.CONTACTICON == 'https://' else ICON 
CONTACTFANART    = uservar.CONTACTFANART if not uservar.CONTACTFANART == 'https://' else FANART
HIDESPACERS      = uservar.HIDESPACERS
COLOR1           = uservar.COLOR1
COLOR2           = uservar.COLOR2
THEME1           = uservar.THEME1
THEME2           = uservar.THEME2
THEME3           = uservar.THEME3
THEME4           = uservar.THEME4
THEME5           = uservar.THEME5
THEME6           = uservar.THEME6
ICONBUILDS = ICONMAINT = ICONADDONS = ICONYOUTUBE = ICONSAVE = ICONTRAKT = ICONREAL = ICONLOGIN = ICONCONTACT = ICONSETTINGS = ICON
Images           = xbmcvfs.translatePath(os.path.join('special://home','addons',ADDON_ID,'resources','images/'))
LOGFILES         = wiz.LOGFILES
TRAKTID          = traktit.TRAKTID
DEBRIDID         = debridit.DEBRIDID
PREMIUMIZEID     = premiumizeit.PREMIUMIZEID
ALLDEBRIDID      = alldebridit.ALLDEBRIDID
TORBOXID         = torboxit.TORBOXID
LINKSNAPPYID     = linksnappit.LINKSNAPPYID
LOGINID          = loginit.LOGINID
INSTALLMETHODS   = ['Always Ask', 'Reload Profile', 'Force Close']
DEFAULTPLUGINS   = ['metadata.album.universal', 'metadata.artists.universal', 'metadata.common.fanart.tv', 'metadata.common.imdb.com', 'metadata.common.musicbrainz.org', 'metadata.themoviedb.org', 'metadata.tvdb.com', 'service.xbmc.versioncheck']

try:
	INSTALLMETHOD    = int(float(wiz.getS('installmethod')))
except:
	INSTALLMETHOD    = 0



	

###########################
###### Menu Items   #######
###########################
#addDir (display,mode,name=None,url=None,menu=None,overwrite=True,fanart=FANART,icon=ICON, themeit=None)
#addFile(display,mode,name=None,url=None,menu=None,overwrite=True,fanart=FANART,icon=ICON, themeit=None)
def index():
	errors = int(errorChecking(count=True))
	err = str(errors)
	errorsfound = '[COLOR red]%s[/COLOR] Error(s) Found'  % (err) if errors > 0 else 'None Found'
	addFile('%s [v%s]' % (ADDONTITLE, VERSION), '', themeit=THEME2)
	if len(BUILDNAME) > 0:
		version = wiz.checkBuild(BUILDNAME, 'version')
		build = '%s (v%s)' % (BUILDNAME, BUILDVERSION)
		if version > BUILDVERSION: build = '%s [COLOR red][B][UPDATE v%s][/B][/COLOR]' % (build, version)
		addDir(build,'viewbuild',BUILDNAME, themeit=THEME4)
	else: addDir('None', 'builds', themeit=THEME4)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	addDir ('Builds', 'builds',   icon=ICONBUILDS,   themeit=THEME1)
	addDir ('Maintenance', 'maint',    icon=ICONMAINT,    themeit=THEME1)
	addDir ('Internet Tools' ,'net', icon=ICONCONTACT, themeit=THEME1)
	addDir ('Save Login Data / Favs Options', 'savedata', icon=ICONSAVE,     themeit=THEME1)
	addDir ('Backup/Restore Data Options'     ,'backup', icon=ICONSAVE,     themeit=THEME1)
	if HIDECONTACT == 'No': addFile('Contact' ,'contact', icon=ICONCONTACT,  themeit=THEME1)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	addFile('Upload Log File', 'uploadlog',       icon=ICONMAINT, themeit=THEME1)
	addFile('View Errors in Log: %s' % (errorsfound), 'viewerrorlog', icon=ICONMAINT, themeit=THEME1)
	if errors > 0: addFile('View Last Error In Log', 'viewerrorlast', icon=ICONMAINT, themeit=THEME1)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	addFile('Settings', 'settings', icon=ICONSETTINGS, themeit=THEME1)
	addFile('Force Update Text Files', 'forcetext', icon=ICONMAINT, themeit=THEME1)
	if DEVELOPER == 'true': addDir('Developer Menu', 'developer', icon=ICON, themeit=THEME1)
	setView('files', 'viewType')
def KodiVer():
	if KODIV >= 19.0 and KODIV <= 19.9:
		vername = 'Matrix'
	elif KODIV >= 20.0 and KODIV <= 20.9:
		vername = 'Nexus'
	elif KODIV >= 21.0 and KODIV <= 21.9:
		vername = 'Omega'
	else:
		vername = "Unknown"
	return vername

def buildMenu():
	kodi_ver = KodiVer()
	bf = wiz.textCache(BUILDFILE).decode('utf-8')
	if bf == False:
		WORKINGURL = wiz.workingURL(BUILDFILE)
		addFile('%s Version: %s' % (MCNAME, KODIV), '', icon=ICONBUILDS, themeit=THEME3)
		addDir ('Save Data Menu'       ,'savedata', icon=ICONSAVE,     themeit=THEME3)
		if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
		addFile('Url for txt file not valid', '', icon=ICONBUILDS, themeit=THEME3)
		addFile('%s' % WORKINGURL, '', icon=ICONBUILDS, themeit=THEME3)
		return
	total, count19, count20, count21,  adultcount, hidden = wiz.buildCount()
	addFile('%s Version: %s' % (MCNAME, KODIV), '', icon=ICONBUILDS, themeit=THEME3)
	addDir ('Save Data Menu'       ,'savedata', icon=ICONSAVE,     themeit=THEME3)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	if len(match) >= 1:
		if SEPERATE == 'true':
			for name, version, url, kodi, icon, fanart, adult, description in match:
				if not SHOWADULT == 'true' and adult.lower() == 'yes': continue
				if not DEVELOPER == 'true' and wiz.strTest(name): continue
				menu = createMenu('install', '', name)
				addDir('[%s] %s (v%s)' % (float(kodi), name, version), 'viewbuild', name, description=description, fanart=fanart,icon=icon, menu=menu, themeit=THEME6 if wiz.strTest(name) else THEME2)
		elif DEVELOPER == 'true':
			if count20 > 0:
				state = '+' if SHOW20 == 'false' else '-'
				addFile('[B]%s Nexus Builds(%s)[/B]' % (state, count20), 'togglesetting',  'show20', themeit=THEME3)
				if SHOW20 == 'true':
					for name, version, url, kodi, icon, fanart, adult, description in match:
						if not SHOWADULT == 'true' and adult.lower() == 'yes': continue
						if not DEVELOPER == 'true' and wiz.strTest(name): continue
						kodiv = int(float(kodi))
						if kodiv == 20:
							menu = createMenu('install', '', name)
							addDir('[%s] %s (v%s)' % (float(kodi), name, version), 'viewbuild', name, description=description, fanart=fanart,icon=icon, menu=menu, themeit=THEME6 if wiz.strTest(name) else THEME2)
			if count19 > 0:
				state = '+' if SHOW19 == 'false' else '-'
				addFile('[B]%s Matrix Builds(%s)[/B]' % (state, count19), 'togglesetting',  'show19', themeit=THEME3)
				if SHOW19 == 'true':
					for name, version, url, kodi, icon, fanart, adult, description in match:
						if not SHOWADULT == 'true' and adult.lower() == 'yes': continue
						if not DEVELOPER == 'true' and wiz.strTest(name): continue
						kodiv = int(float(kodi))
						if kodiv == 19:
							menu = createMenu('install', '', name)
							addDir('[%s] %s (v%s)' % (float(kodi), name, version), 'viewbuild', name, description=description, fanart=fanart,icon=icon, menu=menu, themeit=THEME6 if wiz.strTest(name) else THEME2)
		else:
			if kodi_ver == "Nexus":
				state = '+' if SHOW20 == 'false' else '-'
				addFile('[B]%s Nexus Builds(%s)[/B]' % (state, count20), 'togglesetting',  'show20', themeit=THEME3)
				if SHOW20 == 'true':
					for name, version, url, kodi, icon, fanart, adult, description in match:
						if not SHOWADULT == 'true' and adult.lower() == 'yes': continue
						if not DEVELOPER == 'true' and wiz.strTest(name): continue
						kodiv = int(float(kodi))
						if kodiv == 20:
							menu = createMenu('install', '', name)
							addDir('[%s] %s (v%s)' % (float(kodi), name, version), 'viewbuild', name, description=description, fanart=fanart,icon=icon, menu=menu, themeit=THEME6 if wiz.strTest(name) else THEME2)
			elif kodi_ver == "Matrix":
				state = '+' if SHOW19 == 'false' else '-'
				addFile('[B]%s Matrix Builds(%s)[/B]' % (state, count19), 'togglesetting',  'show19', themeit=THEME3)
				if SHOW19 == 'true':
					for name, version, url, kodi, icon, fanart, adult, description in match:
						if not SHOWADULT == 'true' and adult.lower() == 'yes': continue
						if not DEVELOPER == 'true' and wiz.strTest(name): continue
						kodiv = int(float(kodi))
						if kodiv == 19:
							menu = createMenu('install', '', name)
							addDir('[%s] %s (v%s)' % (float(kodi), name, version), 'viewbuild', name, description=description, fanart=fanart,icon=icon, menu=menu, themeit=THEME6 if wiz.strTest(name) else THEME2)
	elif hidden > 0: 
		if adultcount > 0:
			addFile('There is currently only Adult builds', '', icon=ICONBUILDS, themeit=THEME3)
			addFile('Enable Show Adults in Addon Settings > Misc', '', icon=ICONBUILDS, themeit=THEME3)
		else:
			addFile('Currently No Builds Offered from %s' % ADDONTITLE, '', icon=ICONBUILDS, themeit=THEME3)
	else: addFile('Text file for builds not formated correctly.', '', icon=ICONBUILDS, themeit=THEME3)
	setView('files', 'viewType')
def viewBuild(name):
	bf = wiz.textCache(BUILDFILE)
	if bf == False:
		WORKINGURL = wiz.workingURL(BUILDFILE)
		addFile('Url for txt file not valid', '', themeit=THEME3)
		addFile('%s' % WORKINGURL, '', themeit=THEME3)
		return
	if wiz.checkBuild(name, 'version') == False: 
		addFile('Error reading the txt file.', '', themeit=THEME3)
		addFile('%s was not found in the builds list.' % name, '', themeit=THEME3)
		return
	link  = bf.replace('\n','').replace('\r','').replace('\t','')
	match = re.compile('name="%s".+?ersion="(.+?)".+?rl="(.+?)".+?odi="(.+?)".+?con="(.+?)".+?anart="(.+?)".+?dult="(.+?)".+?escription="(.+?)"' % name).findall(link)
	for version, url, kodi, icon, fanart, adult, description in match:
		icon        = icon
		fanart      = fanart
		build       = '%s (v%s)' % (name, version)
		if BUILDNAME == name and version > BUILDVERSION:
			build = '%s [COLOR red][CURRENT v%s][/COLOR]' % (build, BUILDVERSION)
		addFile(build, '', description=description, fanart=fanart, icon=icon, themeit=THEME4)
		if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
		addDir ('Save Data Menu',       'savedata', icon=ICONSAVE,     themeit=THEME3)
		addFile('Build Information',    'buildinfo', name, description=description, fanart=fanart, icon=icon, themeit=THEME3)
		temp1 = int(float(KODIV)); temp2 = int(float(kodi))
		if not temp1 == temp2: 
			if temp1 == 16 and temp2 <= 15: warning = False
			else: warning = True
		else: warning = False
		if warning == True:
			addFile('BUILD DESIGNED FOR KODI VERSION %s [COLOR yellow](INSTALLED: %s)[/COLOR]' % (str(kodi), str(KODIV)), '', fanart=fanart, icon=icon, themeit=THEME6)
		addFile(wiz.sep('INSTALL'), '', fanart=fanart, icon=icon, themeit=THEME3)
		addFile('Fresh Start then Install'   , 'install', name, 'fresh'  , description=description, fanart=fanart, icon=icon, themeit=THEME1)
		addFile('Standard Install', 'install', name, 'normal' , description=description, fanart=fanart, icon=icon, themeit=THEME1)
	setView('files', 'viewType')


###########################################################################
def maintMenu(view=None):
	on = '[B][COLOR FF00FF00]ON[/COLOR][/B]'; off = '[B][COLOR FFFF0000]OFF[/COLOR][/B]'
	if wiz.Grab_Log(True) == False: kodilog = 0
	else: kodilog = errorChecking(wiz.Grab_Log(True), True)
	if wiz.Grab_Log(True, True) == False: kodioldlog = 0
	else: kodioldlog = errorChecking(wiz.Grab_Log(True,True), True)
	errorsinlog = int(kodilog) + int(kodioldlog)
	wizlogsize = ': [COLOR red]Not Found[/COLOR]' if not os.path.exists(WIZLOG) else ": [COLOR green]%s[/COLOR]" % wiz.convertSize(os.path.getsize(WIZLOG))
	sizepack   = wiz.getSize(PACKAGES)
	sizethumb  = wiz.getSize(THUMBS)
	sizecache  = wiz.getCacheSize()
	totalsize  = sizepack+sizethumb+sizecache
	addFile('Total Clean Up: [COLOR green][B]%s[/B][/COLOR]' % wiz.convertSize(totalsize)  ,'fullclean',       icon=ICONMAINT, themeit=THEME3)
	addFile('Clear Cache: [COLOR green][B]%s[/B][/COLOR]' % wiz.convertSize(sizecache)     ,'clearcache',      icon=ICONMAINT, themeit=THEME3)
	addFile('Clear Packages: [COLOR green][B]%s[/B][/COLOR]' % wiz.convertSize(sizepack)   ,'clearpackages',   icon=ICONMAINT, themeit=THEME3)
	addFile('Clear Thumbnails: [COLOR green][B]%s[/B][/COLOR]' % wiz.convertSize(sizethumb),'clearthumb',      icon=ICONMAINT, themeit=THEME3)
	addFile('Clear Old Thumbnails', 'oldThumbs',      icon=ICONMAINT, themeit=THEME3)
	addFile('Clear Crash Logs',     'clearcrash',      icon=ICONMAINT, themeit=THEME3)
	addFile('Purge Databases',      'purgedb',         icon=ICONMAINT, themeit=THEME3)
	addDir ('[B]Back up/Restore[/B]'     , 'backup',   icon=ICONMAINT, themeit=THEME1)
	addDir ('[B]Advanced Settings Tool[/B]'     , 'autoconfig',   icon=ICONMAINT, themeit=THEME1)
	addDir ('[B]Addon Tools[/B]', 'addon',  icon=ICONMAINT, themeit=THEME1)
	addDir ('[B]Misc Maintenance[/B]'     , 'misc',   icon=ICONMAINT, themeit=THEME1)
	addDir ('[B]System Tweaks/Fixes[/B]', 'tweaks', icon=ICONMAINT, themeit=THEME1)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	addFile('!!!>>Fresh Start<<!!!',          'freshstart',      icon=ICONMAINT, themeit=THEME6)
def backup():
		addFile('Back Up Location: [COLOR %s]%s[/COLOR]' % (COLOR2, MYBUILDS),'settings', 'Maintenance', icon=ICONMAINT, themeit=THEME3)
		if HIDESPACERS == 'No': addFile(wiz.sep('Backup'), '', themeit=THEME1)
		addFile('[Back Up]: Build',               'backupbuild',     icon=ICONMAINT,   themeit=THEME3)
		addFile('[Back Up]: GuiFix',              'backupgui',       icon=ICONMAINT,   themeit=THEME3)
		addFile('[Back Up]: Theme',               'backuptheme',     icon=ICONMAINT,   themeit=THEME3)
		addFile('[Back Up]: Addon Pack',          'backupaddonpack', icon=ICONMAINT,   themeit=THEME3)
		addFile('[Back Up]: Addon_data',          'backupaddon',     icon=ICONMAINT,   themeit=THEME3)
		if HIDESPACERS == 'No': addFile(wiz.sep('Restore'), '', themeit=THEME1)
		addFile('[Restore]: Local Build',         'restorezip',      icon=ICONMAINT,   themeit=THEME3)
		addFile('[Restore]: Local GuiFix',        'restoregui',      icon=ICONMAINT,   themeit=THEME3)
		addFile('[Restore]: Local Addon_data',    'restoreaddon',    icon=ICONMAINT,   themeit=THEME3)
		addFile('[Restore]: External Build',      'restoreextzip',   icon=ICONMAINT,   themeit=THEME3)
		addFile('[Restore]: External GuiFix',     'restoreextgui',   icon=ICONMAINT,   themeit=THEME3)
		addFile('[Restore]: External Addon_data', 'restoreextaddon', icon=ICONMAINT,   themeit=THEME3)
		if HIDESPACERS == 'No': addFile(wiz.sep('Delete All Backups'), '', themeit=THEME1)
		addFile('Clean Up Back Up Folder',        'clearbackup',     icon=ICONMAINT,   themeit=THEME3)
def addon():
		addFile('Remove Addons',                  'removeaddons',    icon=ICONMAINT, themeit=THEME3)
		addDir ('Remove Addon Data',              'removeaddondata', icon=ICONMAINT, themeit=THEME3)
		addDir ('Enable/Disable Addons',          'enableaddons',    icon=ICONMAINT, themeit=THEME3)
		addFile('Enable/Disable Adult Addons',    'toggleadult',     icon=ICONMAINT, themeit=THEME3)
		addFile('Force Update Addons',            'forceupdate',     icon=ICONMAINT, themeit=THEME3)
		addFile('Hide Passwords On Keyboard Entry',   'hidepassword',   icon=ICONMAINT, themeit=THEME3)
		addFile('Unhide Passwords On Keyboard Entry', 'unhidepassword', icon=ICONMAINT, themeit=THEME3)
def misc():
		errors = int(errorChecking(count=True))
		err = str(errors)
		errorsfound = '[COLOR red]%s[/COLOR] Error(s) Found'  % (err) if errors > 0 else 'None Found'
		wizlogsize = ': [COLOR red]Not Found[/COLOR]' if not os.path.exists(WIZLOG) else ": [COLOR green]%s[/COLOR]" % wiz.convertSize(os.path.getsize(WIZLOG))
		addDir ('Speed Test',                     'speedtest',       icon=ICONMAINT, themeit=THEME3)
		addFile('Enable Unknown Sources',         'unknownsources',  icon=ICONMAINT, themeit=THEME3)
		addFile('Reload Skin',                    'forceskin',       icon=ICONMAINT, themeit=THEME3)
		addFile('Reload Profile',                 'forceprofile',    icon=ICONMAINT, themeit=THEME3)
		addFile('Force Close Kodi',               'forceclose',      icon=ICONMAINT, themeit=THEME3)
		addFile('Upload Log File', 'uploadlog',       icon=ICONMAINT, themeit=THEME3)
		addFile('View Errors in Log: %s' % (errorsfound), 'viewerrorlog', icon=ICONMAINT, themeit=THEME3)
		if errors > 0: addFile('View Last Error In Log', 'viewerrorlast', icon=ICONMAINT, themeit=THEME3)
		addFile('View Log File',                  'viewlog',         icon=ICONMAINT, themeit=THEME3)
		addFile('View Wizard Log File',           'viewwizlog',      icon=ICONMAINT, themeit=THEME3)
		addFile('Clear Wizard Log File%s' % wizlogsize,'clearwizlog',     icon=ICONMAINT, themeit=THEME3)
def autoconfig():
	if os.path.exists(ADVANCED):
		addFile('View Current AdvancedSettings.xml',   'currentsettings', icon=ICONMAINT, themeit=THEME3)
		addFile('Remove Current AdvancedSettings.xml', 'removeadvanced',  icon=ICONMAINT, themeit=THEME3)
	addFile('Quick Configure AdvancedSettings.xml',    'autoadvanced',    icon=ICONMAINT, themeit=THEME3)
	addFile('Full Configure AdvancedSettings.xml',    'autoadvanced1',    icon=ICONMAINT, themeit=THEME3)
def tweaks():
	on = '[B][COLOR FF00FF00]ON[/COLOR][/B]'; off = '[B][COLOR FFFF0000]OFF[/COLOR][/B]'
	autoclean   = 'true' if AUTOCLEANUP    == 'true' else 'false'
	cache       = 'true' if AUTOCACHE      == 'true' else 'false'
	packages    = 'true' if AUTOPACKAGES   == 'true' else 'false'
	thumbs      = 'true' if AUTOTHUMBS     == 'true' else 'false'
	maint       = 'true' if SHOWMAINT      == 'true' else 'false'
	includevid  = 'true' if INCLUDEVIDEO   == 'true' else 'false'
	includeall  = 'true' if INCLUDEALL     == 'true' else 'false'
	addDir ('System Information',             'systeminfo',      icon=ICONMAINT, themeit=THEME1)
	addFile('Scan Sources for broken links',  'checksources',    icon=ICONMAINT, themeit=THEME3)
	addFile('Scan For Broken Repositories',   'checkrepos',      icon=ICONMAINT, themeit=THEME3)
	addFile('Fix Addons Not Updating',        'fixaddonupdate',  icon=ICONMAINT, themeit=THEME3)
	addFile('Remove Non-Ascii filenames',     'asciicheck',      icon=ICONMAINT, themeit=THEME3)
	addFile('Convert Paths to special',       'convertpath',     icon=ICONMAINT, themeit=THEME3)
def net_tools(view=None):
	addDir ('Speed Tester' ,'speedtest', icon=ICONMAINT, themeit=THEME1)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	addDir ('View IP Address & MAC Address',        'viewIP',    icon=ICONMAINT, themeit=THEME1)
	setView('files', 'viewType')
def viewIP():
	infoLabel = ['Network.IPAddress',
				 'Network.MacAddress',]
	data      = []; x = 0
	for info in infoLabel:
		temp = wiz.getInfo(info)
		y = 0
		while temp == "Busy" and y < 10:
			temp = wiz.getInfo(info); y += 1; wiz.log("%s sleep %s" % (info, str(y))); xbmc.sleep(200)
		data.append(temp)
		x += 1
		config    = wiz.getConfig()
		ipfinal   = '%(ip)s' % config['client'] #else 'Unknown'
		provider  = '%(isp)s' % config['client'] #else 'Unknown'
		location  = '%(country)s' % config['client'] #else 'Unknown'
	addFile('[COLOR %s]Local IP:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[0]), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]External IP:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, ipfinal), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Provider:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, provider), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Location:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, location), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]MacAddress:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[1]), '', icon=ICONMAINT, themeit=THEME2)
def clearSpeedTest():
	speedimg = glob.glob(os.path.join(SPEEDTESTFOLD, '*.png'))
	for file in speedimg:
		wiz.removeFile(file)
def viewSpeedTest(img=None):
	img = os.path.join(SPEEDTESTFOLD, img)
	notify.speedTest(img)

def speed():
    try:
        from resources.libs import speedtest  # Import here, only when needed

        # Show the spinning busy dialog
        xbmc.executebuiltin('ActivateWindow(busydialog)')

        # Run the speedtest
        found = speedtest.speedtest()
        if not os.path.exists(SPEEDTESTFOLD):
            os.makedirs(SPEEDTESTFOLD)
        urlsplits = found[0].split('/')
        dest = os.path.join(SPEEDTESTFOLD, urlsplits[-1])
        urllib.request.urlretrieve(found[0], dest)

        # Hide the busy dialog
        xbmc.executebuiltin('Dialog.Close(busydialog)')

        # Show the result image
        viewSpeedTest(urlsplits[-1])

        # Wait a few seconds, then restore speedtest.jpg
        time.sleep(5)
        notify.speedTest(os.path.join(ART, 'speedtest.jpg'))

    except Exception as e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        wiz.log(f"[Speed Test] Error Running Speed Test: {e}")
        notify.speedTest(os.path.join(ART, 'speedtest.jpg'))

def writeAdvanced(name, url):
	ADVANCEDWORKING = wiz.workingURL(url)
	if ADVANCEDWORKING == True:
		if os.path.exists(ADVANCED): choice = DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to overwrite your current Advanced Settings with [COLOR %s]%s[/COLOR]?[/COLOR]" % (COLOR2, COLOR1, name), yeslabel="[B][COLOR FF00FF00]Overwrite[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]Cancel[/COLOR][/B]")
		else: choice = DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to download and install [COLOR %s]%s[/COLOR]?[/COLOR]" % (COLOR2, COLOR1, name), yeslabel="[B][COLOR FF00FF00]Install[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]Cancel[/COLOR][/B]")
		if choice == 1:
			file = wiz.openURL(url)
			f = open(ADVANCED, 'w', encoding='utf-8'); 
			f.write(file)
			f.close()
			DIALOG.ok(ADDONTITLE, '[COLOR %s]AdvancedSettings.xml file has been successfully written.\nOnce you click okay it will force close kodi.[/COLOR]' % COLOR2)
			wiz.killxbmc(True)
		else: wiz.log("[Advanced Settings] install canceled"); wiz.LogNotify('[COLOR %s]%s[/COLOR]' % (COLOR1, ADDONTITLE), "[COLOR %s]Write Cancelled![/COLOR]" % COLOR2); return
	else: wiz.log("[Advanced Settings] URL not working: %s" % ADVANCEDWORKING); wiz.LogNotify('[COLOR %s]%s[/COLOR]' % (COLOR1, ADDONTITLE), "[COLOR %s]URL Not Working[/COLOR]" % COLOR2)
def viewAdvanced():
	if os.path.exists(ADVANCED):
		f = open(ADVANCED, encoding='utf-8')
		a = f.read().replace('\t', '    ')
		wiz.TextBox(ADDONTITLE, a)
		f.close()
	else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]AdvancedSettings.xml not found[/COLOR]")
def removeAdvanced():
	if os.path.exists(ADVANCED):
		wiz.removeFile(ADVANCED)
		wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]AdvancedSettings.xml Removed![/COLOR]" % COLOR2, 3000)
	else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]No AdvancedSettings.xml Found[/COLOR]" % COLOR2, 3000)
def showAutoAdvanced():
	notify.simple_advanced()
def showAutoAdvanced1():
	notify.autoConfig()
def getIP():
		config = wiz.getConfig()
		ipfinal   = '%(ip)s' % config['client']
		provider  = '%(isp)s' % config['client'] 
		location  = '%(country)s]' % config['client']
		return ipfinal, provider, location
def systemInfo():
	infoLabel = ['System.FriendlyName', 
				 'System.BuildVersion', 
				 'System.CpuUsage',
				 'System.ScreenMode',
				 'Network.IPAddress',
				 'Network.MacAddress',
				 'System.Uptime',
				 'System.TotalUptime',
				 'System.FreeSpace',
				 'System.UsedSpace',
				 'System.TotalSpace',
				 'System.Memory(free)',
				 'System.Memory(used)',
				 'System.Memory(total)']
	data      = []; x = 0
	for info in infoLabel:
		temp = wiz.getInfo(info)
		y = 0
		while temp == "Busy" and y < 10:
			temp = wiz.getInfo(info); y += 1; wiz.log("%s sleep %s" % (info, str(y))); xbmc.sleep(200)
		data.append(temp)
		x += 1
	storage_free  = data[8] if 'Una' in data[8] else wiz.convertSize(int(float(data[8][:-8]))*1024*1024)
	storage_used  = data[9] if 'Una' in data[9] else wiz.convertSize(int(float(data[9][:-8]))*1024*1024)
	storage_total = data[10] if 'Una' in data[10] else wiz.convertSize(int(float(data[10][:-8]))*1024*1024)
	ram_free      = wiz.convertSize(int(float(data[11][:-2]))*1024*1024)
	ram_used      = wiz.convertSize(int(float(data[12][:-2]))*1024*1024)
	ram_total     = wiz.convertSize(int(float(data[13][:-2]))*1024*1024)
	exter_ip, provider, location = getIP()
	picture = []; music = []; video = []; programs = []; repos = []; scripts = []; skins = []
	fold = glob.glob(os.path.join(ADDONS, '*/'))
	for folder in sorted(fold, key = lambda x: x):
		foldername = os.path.split(folder[:-1])[1]
		if foldername == 'packages': continue
		xml = os.path.join(folder, 'addon.xml')
		if os.path.exists(xml):
			f      = open(xml, encoding='utf-8')
			a      = f.read()
			prov   = re.compile("<provides>(.+?)</provides>").findall(a)
			if len(prov) == 0:
				if foldername.startswith('skin'): skins.append(foldername)
				elif foldername.startswith('repo'): repos.append(foldername)
				else: scripts.append(foldername)
			elif not (prov[0]).find('executable') == -1: programs.append(foldername)
			elif not (prov[0]).find('video') == -1: video.append(foldername)
			elif not (prov[0]).find('audio') == -1: music.append(foldername)
			elif not (prov[0]).find('image') == -1: picture.append(foldername)
	addFile('[B]Media Center Info:[/B]', '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Name:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[0]), '', icon=ICONMAINT, themeit=THEME3)
	addFile('[COLOR %s]Version:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[1]), '', icon=ICONMAINT, themeit=THEME3)
	addFile('[COLOR %s]Platform:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, wiz.platform().title()), '', icon=ICONMAINT, themeit=THEME3)
	addFile('[COLOR %s]CPU Usage:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[2]), '', icon=ICONMAINT, themeit=THEME3)
	addFile('[COLOR %s]Screen Mode:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[3]), '', icon=ICONMAINT, themeit=THEME3)
	addFile('[B]Uptime:[/B]', '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Current Uptime:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[6]), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Total Uptime:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[7]), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[B]Local Storage:[/B]', '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Used Storage:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, storage_free), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Free Storage:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, storage_used), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Total Storage:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, storage_total), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[B]Ram Usage:[/B]', '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Used Memory:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, ram_free), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Free Memory:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, ram_used), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Total Memory:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, ram_total), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[B]Network:[/B]', '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Local IP:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[4]), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]External IP:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, exter_ip), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Provider:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, provider), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Location:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, location), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]MacAddress:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, data[5]), '', icon=ICONMAINT, themeit=THEME2)
	totalcount = len(picture) + len(music) + len(video) + len(programs) + len(scripts) + len(skins) + len(repos) 
	addFile('[B]Addons([COLOR %s]%s[/COLOR]):[/B]' % (COLOR1, totalcount), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Video Addons:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, str(len(video))), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Program Addons:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, str(len(programs))), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Music Addons:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, str(len(music))), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Picture Addons:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, str(len(picture))), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Repositories:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, str(len(repos))), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Skins:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, str(len(skins))), '', icon=ICONMAINT, themeit=THEME2)
	addFile('[COLOR %s]Scripts/Modules:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, str(len(scripts))), '', icon=ICONMAINT, themeit=THEME2)
def saveMenu():
	on = '[COLOR green]ON[/COLOR]'; off = '[COLOR red]OFF[/COLOR]'
	trakt      = 'true' if KEEPTRAKT      == 'true' else 'false'
	real       = 'true' if KEEPREAL       == 'true' else 'false'
	prem       = 'true' if KEEPPREMIUMIZE == 'true' else 'false'
	login      = 'true' if KEEPLOGIN      == 'true' else 'false'
	sources    = 'true' if KEEPSOURCES    == 'true' else 'false'
	advanced   = 'true' if KEEPADVANCED   == 'true' else 'false'
	profiles   = 'true' if KEEPPROFILES   == 'true' else 'false'
	favourites = 'true' if KEEPFAVS       == 'true' else 'false'
	repos      = 'true' if KEEPREPOS      == 'true' else 'false'
	super      = 'true' if KEEPSUPER      == 'true' else 'false'
	whitelist  = 'true' if KEEPWHITELIST  == 'true' else 'false'
	addFile('Keep My \'WhiteList\': %s' % whitelist.replace('true',on).replace('false',off)        ,'togglesetting', 'keepwhitelist',  icon=ICONSAVE,  themeit=THEME1)
	if whitelist == 'true':
		addFile('    Edit My Whitelist',        'whitelist', 'edit',   icon=ICONSAVE,  themeit=THEME1)
		addFile('    View My Whitelist',        'whitelist', 'view',   icon=ICONSAVE,  themeit=THEME1)
		addFile('    Clear My Whitelist',       'whitelist', 'clear',  icon=ICONSAVE,  themeit=THEME1)
		addFile('    Import My Whitelist',      'whitelist', 'import', icon=ICONSAVE,  themeit=THEME1)
		addFile('    Export My Whitelist',      'whitelist', 'export', icon=ICONSAVE,  themeit=THEME1)
	addDir ('Keep Favourites'              ,'FavsMenu',    icon=ICONREAL, themeit=THEME1)
	addFile('[I]Auth credentials (Trakt, debrid) are auto-saved in the background.[/I]', '', themeit=THEME3)
	addFile('[I]Re-authorization is required after each build install - this is a Kodi limitation.[/I]', '', themeit=THEME3)
	addFile('- Click to toggle settings -', '', themeit=THEME3)
	#addFile('Keep \'Sources.xml\': %s' % sources.replace('true',on).replace('false',off)           ,'togglesetting', 'keepsources',    icon=ICONSAVE,  themeit=THEME1)
	addFile('Keep \'Profiles.xml\': %s' % profiles.replace('true',on).replace('false',off)         ,'togglesetting', 'keepprofiles',   icon=ICONSAVE,  themeit=THEME1)
	addFile('Keep \'Advancedsettings.xml\': %s' % advanced.replace('true',on).replace('false',off) ,'togglesetting', 'keepadvanced',   icon=ICONSAVE,  themeit=THEME1)
	addFile('Keep \'Favourites.xml\': %s' % favourites.replace('true',on).replace('false',off)     ,'togglesetting', 'keepfavourites', icon=ICONSAVE,  themeit=THEME1)
	addFile('Keep Super Favourites: %s' % super.replace('true',on).replace('false',off)            ,'togglesetting', 'keepsuper',      icon=ICONSAVE,  themeit=THEME1)
	addFile('Keep Installed Repo\'s: %s' % repos.replace('true',on).replace('false',off)           ,'togglesetting', 'keeprepos',      icon=ICONSAVE,  themeit=THEME1)
	setView('files', 'viewType')
def FavsMenu():
	on = '[COLOR green]ON[/COLOR]'; off = '[COLOR red]OFF[/COLOR]'
	fav = '[COLOR green]ON[/COLOR]' if KEEPFAVS == 'true' else '[COLOR red]OFF[/COLOR]'
	last = str(FAVSsave) if not FAVSsave == '' else 'Favourites hasnt been saved yet.'
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	addFile('Save Favourites: %s' % fav, 'togglesetting', 'keepfavourites', icon=ICONTRAKT, themeit=THEME3)
	if KEEPFAVS == 'true': addFile('Last Save: %s' % str(last), '', icon=ICONTRAKT, themeit=THEME3)
	if HIDESPACERS == 'No': addFile(wiz.sep('Backs up a copy'), '', themeit=THEME3)
	addFile('Save Favourites',      'savefav',    icon=ICONTRAKT,  themeit=THEME1)
	addFile('Recover Favourites',   'restorefav', icon=ICONTRAKT,  themeit=THEME1)
	addFile('Clear Favourite Backup', 'clearfav', icon=ICONTRAKT,  themeit=THEME1)
	setView('files', 'viewType')
def traktMenu():
	trakt = '[COLOR green]ON[/COLOR]' if KEEPTRAKT == 'true' else '[COLOR red]OFF[/COLOR]'
	last = str(TRAKTSAVE) if not TRAKTSAVE == '' else 'Trakt hasnt been saved yet.'
	addFile('[I]Register FREE Account at https://trakt.tv[/I]', '', icon=ICONTRAKT, themeit=THEME3)
	addFile('Save Trakt Data: %s' % trakt, 'togglesetting', 'keeptrakt', icon=ICONTRAKT, themeit=THEME3)
	if KEEPTRAKT == 'true': addFile('Last Save: %s' % str(last), '', icon=ICONTRAKT, themeit=THEME3)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', icon=ICONTRAKT, themeit=THEME3)
	for trakt in traktit.ORDER:
		name   = TRAKTID[trakt]['name']
		path   = TRAKTID[trakt]['path']
		saved  = TRAKTID[trakt]['saved']
		file   = TRAKTID[trakt]['file']
		user   = wiz.getS(saved)
		auser  = traktit.traktUser(trakt)
		icon   = TRAKTID[trakt]['icon']   if os.path.exists(path) else ICONTRAKT
		fanart = TRAKTID[trakt]['fanart'] if os.path.exists(path) else FANART
		menu = createMenu('saveaddon', 'Trakt', trakt)
		menu2 = createMenu('save', 'Trakt', trakt)
		menu.append((THEME2 % '%s Settings' % name,              'RunPlugin(plugin://%s/?mode=opensettings&name=%s&url=trakt)' %   (ADDON_ID, trakt)))
		addFile('[+]-> %s' % name,     '', icon=icon, fanart=fanart, themeit=THEME3)
		if not os.path.exists(path): addFile('[COLOR red]Addon Data: Not Installed[/COLOR]', '', icon=icon, fanart=fanart, menu=menu)
		elif not auser:              addFile('[COLOR red]Addon Data: Not Registered[/COLOR]','authtrakt', trakt, icon=icon, fanart=fanart, menu=menu)
		else:                        addFile('[COLOR green]Addon Data: %s[/COLOR]' % auser,'authtrakt', trakt, icon=icon, fanart=fanart, menu=menu)
		if user == "":
			if os.path.exists(file): addFile('[COLOR red]Saved Data: Save File Found(Import Data)[/COLOR]','importtrakt', trakt, icon=icon, fanart=fanart, menu=menu2)
			else :                   addFile('[COLOR red]Saved Data: Not Saved[/COLOR]','savetrakt', trakt, icon=icon, fanart=fanart, menu=menu2)
		else:                        addFile('[COLOR green]Saved Data: %s[/COLOR]' % user, '', icon=icon, fanart=fanart, menu=menu2)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	addFile('Save All Trakt Data',          'savetrakt',    'all', icon=ICONTRAKT,  themeit=THEME3)
	addFile('Recover All Saved Trakt Data', 'restoretrakt', 'all', icon=ICONTRAKT,  themeit=THEME3)
	addFile('Import Trakt Data',            'importtrakt',  'all', icon=ICONTRAKT,  themeit=THEME3)
	addFile('Clear All Saved Trakt Data',   'cleartrakt',   'all', icon=ICONTRAKT,  themeit=THEME3)
	addFile('Clear All Addon Data',         'addontrakt',   'all', icon=ICONTRAKT,  themeit=THEME3)
	setView('files', 'viewType')
def realMenu():
	real = '[COLOR green]ON[/COLOR]' if KEEPREAL == 'true' else '[COLOR red]OFF[/COLOR]'
	last = str(REALSAVE) if not REALSAVE == '' else 'Real Debrid hasnt been saved yet.'
	addFile('[I]https://real-debrid.com is a PAID service.[/I]', '', icon=ICONREAL, themeit=THEME3)
	addFile('Save Real Debrid Data: %s' % real, 'togglesetting', 'keepdebrid', icon=ICONREAL, themeit=THEME3)
	if KEEPREAL == 'true': addFile('Last Save: %s' % str(last), '', icon=ICONREAL, themeit=THEME3)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', icon=ICONREAL, themeit=THEME3)
	for debrid in debridit.ORDER:
		name   = DEBRIDID[debrid]['name']
		path   = DEBRIDID[debrid]['path']
		saved  = DEBRIDID[debrid]['saved']
		file   = DEBRIDID[debrid]['file']
		user   = wiz.getS(saved)
		auser  = debridit.debridUser(debrid)
		icon   = DEBRIDID[debrid]['icon']   if os.path.exists(path) else ICONREAL
		fanart = DEBRIDID[debrid]['fanart'] if os.path.exists(path) else FANART
		menu = createMenu('saveaddon', 'Debrid', debrid)
		menu2 = createMenu('save', 'Debrid', debrid)
		menu.append((THEME2 % '%s Settings' % name,              'RunPlugin(plugin://%s/?mode=opensettings&name=%s&url=debrid)' %   (ADDON_ID, debrid)))
		addFile('[+]-> %s' % name,     '', icon=icon, fanart=fanart, themeit=THEME3)
		if not os.path.exists(path): addFile('[COLOR red]Addon Data: Not Installed[/COLOR]', '', icon=icon, fanart=fanart, menu=menu)
		elif not auser:              addFile('[COLOR red]Addon Data: Not Registered[/COLOR]','authdebrid', debrid, icon=icon, fanart=fanart, menu=menu)
		else:                        addFile('[COLOR green]Addon Data: %s[/COLOR]' % auser,'authdebrid', debrid, icon=icon, fanart=fanart, menu=menu)
		if user == "":
			if os.path.exists(file): addFile('[COLOR red]Saved Data: Save File Found(Import Data)[/COLOR]','importdebrid', debrid, icon=icon, fanart=fanart, menu=menu2)
			else :                   addFile('[COLOR red]Saved Data: Not Saved[/COLOR]','savedebrid', debrid, icon=icon, fanart=fanart, menu=menu2)
		else:                        addFile('[COLOR green]Saved Data: %s[/COLOR]' % user, '', icon=icon, fanart=fanart, menu=menu2)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	addFile('Save All Real Debrid Data',          'savedebrid',    'all', icon=ICONREAL,  themeit=THEME3)
	addFile('Recover All Saved Real Debrid Data', 'restoredebrid', 'all', icon=ICONREAL,  themeit=THEME3)
	addFile('Import Real Debrid Data',            'importdebrid',  'all', icon=ICONREAL,  themeit=THEME3)
	addFile('Clear All Saved Real Debrid Data',   'cleardebrid',   'all', icon=ICONREAL,  themeit=THEME3)
	addFile('Clear All Addon Data',               'addondebrid',   'all', icon=ICONREAL,  themeit=THEME3)
	setView('files', 'viewType')
def loginMenu():
	login = '[COLOR green]ON[/COLOR]' if KEEPLOGIN == 'true' else '[COLOR red]OFF[/COLOR]'
	last = str(LOGINSAVE) if not LOGINSAVE == '' else 'Login data hasnt been saved yet.'
	addFile('[I]Several of these addons are PAID services.[/I]', '', icon=ICONLOGIN, themeit=THEME3)
	addFile('Save Login Data: %s' % login, 'togglesetting', 'keeplogin', icon=ICONLOGIN, themeit=THEME3)
	if KEEPLOGIN == 'true': addFile('Last Save: %s' % str(last), '', icon=ICONLOGIN, themeit=THEME3)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', icon=ICONLOGIN, themeit=THEME3)
	for login in loginit.ORDER:
		name   = LOGINID[login]['name']
		path   = LOGINID[login]['path']
		saved  = LOGINID[login]['saved']
		file   = LOGINID[login]['file']
		user   = wiz.getS(saved)
		auser  = loginit.loginUser(login)
		icon   = LOGINID[login]['icon']   if os.path.exists(path) else ICONLOGIN
		fanart = LOGINID[login]['fanart'] if os.path.exists(path) else FANART
		menu = createMenu('saveaddon', 'Login', login)
		menu2 = createMenu('save', 'Login', login)
		menu.append((THEME2 % '%s Settings' % name,              'RunPlugin(plugin://%s/?mode=opensettings&name=%s&url=login)' %   (ADDON_ID, login)))
		addFile('[+]-> %s' % name,     '', icon=icon, fanart=fanart, themeit=THEME3)
		if not os.path.exists(path): addFile('[COLOR red]Addon Data: Not Installed[/COLOR]', '', icon=icon, fanart=fanart, menu=menu)
		elif not auser:              addFile('[COLOR red]Addon Data: Not Registered[/COLOR]','authlogin', login, icon=icon, fanart=fanart, menu=menu)
		else:                        addFile('[COLOR green]Addon Data: %s[/COLOR]' % auser,'authlogin', login, icon=icon, fanart=fanart, menu=menu)
		if user == "":
			if os.path.exists(file): addFile('[COLOR red]Saved Data: Save File Found(Import Data)[/COLOR]','importlogin', login, icon=icon, fanart=fanart, menu=menu2)
			else :                   addFile('[COLOR red]Saved Data: Not Saved[/COLOR]','savelogin', login, icon=icon, fanart=fanart, menu=menu2)
		else:                        addFile('[COLOR green]Saved Data: %s[/COLOR]' % user, '', icon=icon, fanart=fanart, menu=menu2)
	if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
	addFile('Save All Login Data',          'savelogin',    'all', icon=ICONLOGIN,  themeit=THEME3)
	addFile('Recover All Saved Login Data', 'restorelogin', 'all', icon=ICONLOGIN,  themeit=THEME3)
	addFile('Import Login Data',            'importlogin',  'all', icon=ICONLOGIN,  themeit=THEME3)
	addFile('Clear All Saved Login Data',   'clearlogin',   'all', icon=ICONLOGIN,  themeit=THEME3)
	addFile('Clear All Addon Data',         'addonlogin',   'all', icon=ICONLOGIN,  themeit=THEME3)
	setView('files', 'viewType')
def fixUpdate():
	if os.path.exists(os.path.join(USERDATA, 'autoexec.py')):
		temp = os.path.join(USERDATA, 'autoexec_temp.py')
		if os.path.exists(temp): xbmcvfs.delete(temp)
		xbmcvfs.rename(os.path.join(USERDATA, 'autoexec.py'), temp)
	xbmcvfs.copy(os.path.join(PLUGIN, 'resources', 'libs', 'autoexec.py'), os.path.join(USERDATA, 'autoexec.py'))
	dbfile = os.path.join(DATABASE, wiz.latestDB('Addons'))
	try:
		os.remove(dbfile)
	except Exception as e:
		wiz.log("Unable to remove %s, Purging DB" % dbfile)
		wiz.purgeDb(dbfile)
	wiz.killxbmc(True)
def removeAddonMenu():
	fold = glob.glob(os.path.join(ADDONS, '*/'))
	addonnames = []; addonids = []
	for folder in sorted(fold, key = lambda x: x):
		foldername = os.path.split(folder[:-1])[1]
		if foldername in EXCLUDES: continue
		elif foldername in DEFAULTPLUGINS: continue
		elif foldername == 'packages': continue
		xml = os.path.join(folder, 'addon.xml')
		if os.path.exists(xml):
			f      = open(xml, encoding='utf-8')
			a      = f.read()
			match  = wiz.parseDOM(a, 'addon', ret='id')
			addid  = foldername if len(match) == 0 else match[0]
			try: 
				add = xbmcaddon.Addon(id=addid)
				addonnames.append(add.getAddonInfo('name'))
				addonids.append(addid)
			except:
				pass
	if len(addonnames) == 0:
		wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]No Addons To Remove[/COLOR]" % COLOR2)
		return
	selected = DIALOG.multiselect("%s: Select the addons you wish to remove." % ADDONTITLE, addonnames)
	if selected == None: return
	if len(selected) > 0:
		wiz.addonUpdates('set')
		for addon in selected:
			removeAddon(addonids[addon], addonnames[addon], True)
		xbmc.sleep(500)
		if INSTALLMETHOD == 1: todo = 1
		elif INSTALLMETHOD == 2: todo = 0
		else: todo = DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like to [COLOR %s]Force close[/COLOR] kodi or [COLOR %s]Reload Profile[/COLOR]?[/COLOR]" % (COLOR2, COLOR1, COLOR1), yeslabel="[B][COLOR FF00FF00]Reload Profile[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]Force Close[/COLOR][/B]")
		if todo == 1: wiz.reloadFix('remove addon')
		else: wiz.addonUpdates('reset'); wiz.killxbmc(True)
def removeAddonDataMenu():
	if os.path.exists(ADDOND):
		addFile('[COLOR red][B][REMOVE][/B][/COLOR] All Addon_Data', 'removedata', 'all', themeit=THEME2)
		addFile('[COLOR red][B][REMOVE][/B][/COLOR] All Addon_Data for Uninstalled Addons', 'removedata', 'uninstalled', themeit=THEME2)
		addFile('[COLOR red][B][REMOVE][/B][/COLOR] All Empty Folders in Addon_Data', 'removedata', 'empty', themeit=THEME2)
		addFile('[COLOR red][B][REMOVE][/B][/COLOR] %s Addon_Data' % ADDONTITLE, 'resetaddon', themeit=THEME2)
		if HIDESPACERS == 'No': addFile(wiz.sep(), '', themeit=THEME3)
		fold = glob.glob(os.path.join(ADDOND, '*/'))
		for folder in sorted(fold, key = lambda x: x):
			foldername = folder.replace(ADDOND, '').replace('\\', '').replace('/', '')
			icon = os.path.join(folder.replace(ADDOND, ADDONS), 'icon.png')
			fanart = os.path.join(folder.replace(ADDOND, ADDONS), 'fanart.png')
			folderdisplay = foldername
			replace = {'audio.':'[COLOR orange][AUDIO] [/COLOR]', 'metadata.':'[COLOR cyan][METADATA] [/COLOR]', 'module.':'[COLOR orange][MODULE] [/COLOR]', 'plugin.':'[COLOR blue][PLUGIN] [/COLOR]', 'program.':'[COLOR orange][PROGRAM] [/COLOR]', 'repository.':'[COLOR gold][REPO] [/COLOR]', 'script.':'[COLOR green][SCRIPT] [/COLOR]', 'service.':'[COLOR green][SERVICE] [/COLOR]', 'skin.':'[COLOR dodgerblue][SKIN] [/COLOR]', 'video.':'[COLOR orange][VIDEO] [/COLOR]', 'weather.':'[COLOR yellow][WEATHER] [/COLOR]'}
			for rep in replace:
				folderdisplay = folderdisplay.replace(rep, replace[rep])
			if foldername in EXCLUDES: folderdisplay = '[COLOR green][B][PROTECTED][/B][/COLOR] %s' % folderdisplay
			else: folderdisplay = '[COLOR red][B][REMOVE][/B][/COLOR] %s' % folderdisplay
			addFile(' %s' % folderdisplay, 'removedata', foldername, icon=icon, fanart=fanart, themeit=THEME2)
	else:
		addFile('No Addon data folder found.', '', themeit=THEME3)
	#setView('files', 'viewType')
def enableAddons():
	addFile("[I][B][COLOR FFFF0000]!!Notice: Disabling Some Addons Can Cause Issues!![/COLOR][/B][/I]", '', icon=ICONMAINT)
	fold = glob.glob(os.path.join(ADDONS, '*/'))
	x = 0
	for folder in sorted(fold, key = lambda x: x):
		foldername = os.path.split(folder[:-1])[1]
		if foldername in EXCLUDES: continue
		if foldername in DEFAULTPLUGINS: continue
		addonxml = os.path.join(folder, 'addon.xml')
		if os.path.exists(addonxml):
			x += 1
			fold   = folder.replace(ADDONS, '')[1:-1]
			f      = open(addonxml, encoding='utf-8')
			a      = f.read().replace('\n','').replace('\r','').replace('\t','')
			match  = wiz.parseDOM(a, 'addon', ret='id')
			match2 = wiz.parseDOM(a, 'addon', ret='name')
			try:
				pluginid = match[0]
				name = match2[0]
			except:
				continue
			try:
				add    = xbmcaddon.Addon(id=pluginid)
				state  = "[COLOR green][Enabled][/COLOR]"
				goto   = "false"
			except:
				state  = "[COLOR red][Disabled][/COLOR]"
				goto   = "true"
				pass
			icon   = os.path.join(folder, 'icon.png') if os.path.exists(os.path.join(folder, 'icon.png')) else ICON
			fanart = os.path.join(folder, 'fanart.jpg') if os.path.exists(os.path.join(folder, 'fanart.jpg')) else FANART
			addFile("%s %s" % (state, name), 'toggleaddon', fold, goto, icon=icon, fanart=fanart)
			f.close()
	if x == 0:
		addFile("No Addons Found to Enable or Disable.", '', icon=ICONMAINT)
	setView('files', 'viewType')
def changeFeq():
	feq        = ['Every Startup', 'Every Day', 'Every Three Days', 'Every Weekly']
	change     = DIALOG.select("[COLOR %s]How often would you list to Auto Clean on Startup?[/COLOR]" % COLOR2, feq)
	if not change == -1: 
		wiz.setS('autocleanfeq', str(change))
		wiz.LogNotify('[COLOR %s]Auto Clean Up[/COLOR]' % COLOR1, '[COLOR %s]Fequency Now %s[/COLOR]' % (COLOR2, feq[change]))
def developer():
	addFile('Skin Swap Popup',         'sswap',           themeit=THEME1)
	addFile('Create QR Code',                      'createqr',              themeit=THEME1)
	addFile('Test Notifications',                  'testnotify',            themeit=THEME1)
	addFile('Test Update',                         'testupdate',            themeit=THEME1)
	addFile('Test First Run',                      'testfirst',             themeit=THEME1)
	addFile('Test First Run Settings',             'testfirstrun',          themeit=THEME1)
	addFile('Test Auto ADV Settings',             'autoadvanced',          themeit=THEME1)
	setView('files', 'viewType')
###########################
###### Build Install ######
###########################
def buildWizard(name, type, theme=None, over=False):
	if over == False:
		testbuild = wiz.checkBuild(name, 'url')
		if testbuild == False:
			wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Unabled to find build[/COLOR]" % COLOR2)
			return
		testworking = wiz.workingURL(testbuild)
		if testworking == False:
			wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Build Zip Error: %s[/COLOR]" % (COLOR2, testworking))
			return
	if type == 'fresh':
		freshStart(name)
	elif type == 'normal':
		if KEEPTRAKT == 'true':
			traktit.autoUpdate('all')
			wiz.setS('traktlastsave', str(THREEDAYS))
		if KEEPREAL == 'true':
			debridit.autoUpdate('all')
			wiz.setS('debridlastsave', str(THREEDAYS))
		if KEEPLOGIN == 'true':
			loginit.autoUpdate('all')
			wiz.setS('loginlastsave', str(THREEDAYS))
		if KEEPPREMIUMIZE == 'true':
			premiumizeit.autoUpdate('all')
			wiz.setS('premiumizelastsave', str(THREEDAYS))
		if KEEPALLDEBRID == 'true':
			alldebridit.autoUpdate('all')
			wiz.setS('alldebridlastsave', str(THREEDAYS))
		if KEEPTORBOX == 'true':
			torboxit.autoUpdate('all')
			wiz.setS('torboxlastsave', str(THREEDAYS))
		if KEEPLINKSNAPPY == 'true':
			linksnappit.autoUpdate('all')
			wiz.setS('linksnappylastsave', str(THREEDAYS))
		temp_kodiv = int(KODIV); buildv = int(float(wiz.checkBuild(name, 'kodi')))
		if not temp_kodiv == buildv: 
			if temp_kodiv == 16 and buildv <= 15: warning = False
			else: warning = True
		else: warning = False
		if warning == True:
			yes_pressed = DIALOG.yesno("%s - [COLOR red]WARNING!![/COLOR]" % ADDONTITLE, '[COLOR %s]There is a chance that the skin will not appear correctly' % COLOR2 + '\nWhen installing a %s build on a Kodi %s install' % (wiz.checkBuild(name, 'kodi'), KODIV) + '\nWould you still like to install: [COLOR %s]%s v%s[/COLOR]?[/COLOR]' % (COLOR1, name, wiz.checkBuild(name,'version')), nolabel='[B][COLOR FFFF0000]No, Cancel[/COLOR][/B]',yeslabel='[B][COLOR FF00FF00]Yes, Install[/COLOR][/B]')
		else:
			if not over == False: yes_pressed = 1
			else: yes_pressed = DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you like to Download and Install:' % COLOR2 + '\n[COLOR %s]%s v%s[/COLOR]?[/COLOR]' % (COLOR1, name, wiz.checkBuild(name,'version')), nolabel='[B][COLOR FFFF0000]No, Cancel[/COLOR][/B]',yeslabel='[B][COLOR FF00FF00]Yes, Install[/COLOR][/B]')
		if yes_pressed:
			wiz.clearS('build')
			buildzip = wiz.checkBuild(name, 'url')
			zipname = name.replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
			if not wiz.workingURL(buildzip) == True: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), '[COLOR %s]Build Install: Invalid Zip Url![/COLOR]' % COLOR2); return
			if not os.path.exists(PACKAGES): os.makedirs(PACKAGES)
			from resources.libs.ui.install_window import InstallWindow
			_dp = InstallWindow()
			_dp.create(ADDONTITLE,'[COLOR %s][B]Downloading:[/B][/COLOR] [COLOR %s]%s v%s[/COLOR]' % (COLOR2, COLOR1, name, wiz.checkBuild(name,'version')) + '\nPlease Wait')
			lib=os.path.join(PACKAGES, '%s.zip' % zipname)
			try: os.remove(lib)
			except: pass
			downloader.download(buildzip, lib, _dp)
			xbmc.sleep(500)
			title = '[COLOR %s][B]Installing:[/B][/COLOR] [COLOR %s]%s v%s[/COLOR]' % (COLOR2, COLOR1, name, wiz.checkBuild(name,'version'))
			_dp.update(0, title + '\nPlease Wait')
			percent, errors, error = extract.all(lib,HOME,_dp, title=title)
			if int(float(percent)) > 0:
				wiz.fixmetas()
				wiz.lookandFeelData('save')
				wiz.defaultSkin()
				#wiz.addonUpdates('set')
				wiz.setS('buildname', name)
				wiz.setS('buildversion', wiz.checkBuild( name,'version'))
				wiz.setS('buildtheme', '')
				wiz.setS('latestversion', wiz.checkBuild( name,'version'))
				wiz.setS('lastbuildcheck', str(NEXTCHECK))
				wiz.setS('installed', 'true')
				wiz.setS('extract', str(percent))
				wiz.setS('errors', str(errors))
				wiz.log('INSTALLED %s: [ERRORS:%s]' % (percent, errors))
				try: os.remove(lib)
				except: pass
				if int(float(errors)) > 0:
					yes=DIALOG.yesno(ADDONTITLE, '[COLOR %s][COLOR %s]%s v%s[/COLOR]' % (COLOR2, COLOR1, name, wiz.checkBuild(name,'version')) + '\nCompleted: [COLOR %s]%s%s[/COLOR] [Errors:[COLOR %s]%s[/COLOR]]' % (COLOR1, percent, '%', COLOR1, errors) + '\nWould you like to view the errors?[/COLOR]', nolabel='[B][COLOR FFFF0000]No Thanks[/COLOR][/B]', yeslabel='[B][COLOR FF00FF00]View Errors[/COLOR][/B]')
					if yes:
						if isinstance(errors, str):
							error = error.encode('utf-8')
						wiz.TextBox(ADDONTITLE, error)
				_dp.close()
				wiz.addonDatabase(ADDON_ID, 1)
				DIALOG.ok(ADDONTITLE, "[COLOR %s]To save changes you now need to force close Kodi, Press OK to force close Kodi[/COLOR]" % COLOR2); wiz.killxbmc('true')
			else:
				if isinstance(errors, str):
					error = error.encode('utf-8')
				wiz.TextBox("%s: Error Installing Build" % ADDONTITLE, error)
		else:
			wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), '[COLOR %s]Build Install: Cancelled![/COLOR]' % COLOR2)
def testTheme(path):
	zfile = zipfile.ZipFile(path)
	for item in zfile.infolist():
		wiz.log(str(item.filename))
		if '/settings.xml' in item.filename:
			return True
	return False
def testGui(path):
	zfile = zipfile.ZipFile(path)
	for item in zfile.infolist():
		if '/guisettings.xml' in item.filename:
			return True
	return False
###########################
###### Misc Functions######
###########################
def createMenu(_type, add, name):
	if   _type == 'saveaddon':
		menu_items=[]
		add2  = urllib.parse.quote_plus(add.lower().replace(' ', ''))
		add3  = add.replace('Debrid', 'Real Debrid')
		name2 = urllib.parse.quote_plus(name.lower().replace(' ', ''))
		name = name.replace('url', 'URL Resolver')
		menu_items.append((THEME2 % name.title(),             ' '))
		menu_items.append((THEME3 % 'Save %s Data' % add3,               'RunPlugin(plugin://%s/?mode=save%s&name=%s)' %    (ADDON_ID, add2, name2)))
		menu_items.append((THEME3 % 'Restore %s Data' % add3,            'RunPlugin(plugin://%s/?mode=restore%s&name=%s)' % (ADDON_ID, add2, name2)))
		menu_items.append((THEME3 % 'Clear %s Data' % add3,              'RunPlugin(plugin://%s/?mode=clear%s&name=%s)' %   (ADDON_ID, add2, name2)))
	elif _type == 'save'    :
		menu_items=[]
		add2  = urllib.parse.quote_plus(add.lower().replace(' ', ''))
		add3  = add.replace('Debrid', 'Real Debrid')
		name2 = urllib.parse.quote_plus(name.lower().replace(' ', ''))
		name = name.replace('url', 'URL Resolver')
		menu_items.append((THEME2 % name.title(),             ' '))
		menu_items.append((THEME3 % 'Register %s' % add3,                'RunPlugin(plugin://%s/?mode=auth%s&name=%s)' %    (ADDON_ID, add2, name2)))
		menu_items.append((THEME3 % 'Save %s Data' % add3,               'RunPlugin(plugin://%s/?mode=save%s&name=%s)' %    (ADDON_ID, add2, name2)))
		menu_items.append((THEME3 % 'Restore %s Data' % add3,            'RunPlugin(plugin://%s/?mode=restore%s&name=%s)' % (ADDON_ID, add2, name2)))
		menu_items.append((THEME3 % 'Import %s Data' % add3,             'RunPlugin(plugin://%s/?mode=import%s&name=%s)' %  (ADDON_ID, add2, name2)))
		menu_items.append((THEME3 % 'Clear Addon %s Data' % add3,        'RunPlugin(plugin://%s/?mode=addon%s&name=%s)' %   (ADDON_ID, add2, name2)))
	elif _type == 'install'  :
		menu_items=[]
		name2 = urllib.parse.quote_plus(name)
		menu_items.append((THEME2 % name,                                'RunAddon(%s, ?mode=viewbuild&name=%s)'  % (ADDON_ID, name2)))
		menu_items.append((THEME3 % 'Fresh Install',                     'RunPlugin(plugin://%s/?mode=install&name=%s&url=fresh)'  % (ADDON_ID, name2)))
		menu_items.append((THEME3 % 'Normal Install',                    'RunPlugin(plugin://%s/?mode=install&name=%s&url=normal)' % (ADDON_ID, name2)))
		menu_items.append((THEME3 % 'Apply guiFix',                      'RunPlugin(plugin://%s/?mode=install&name=%s&url=gui)'    % (ADDON_ID, name2)))
		menu_items.append((THEME3 % 'Build Information',                 'RunPlugin(plugin://%s/?mode=buildinfo&name=%s)'  % (ADDON_ID, name2)))
	menu_items.append((THEME2 % '%s Settings' % ADDONTITLE,              'RunPlugin(plugin://%s/?mode=settings)' % ADDON_ID))
	return menu_items
def toggleCache(state):
	cachelist = ['includevideo', 'includeall']
	titlelist = ['Include Video Addons', 'Include All Addons']
	if state in ['true', 'false']:
		for item in cachelist:
			wiz.setS(item, state)
	else:
		if not state in ['includevideo', 'includeall'] and wiz.getS('includeall') == 'true':
			try:
				item = titlelist[cachelist.index(state)]
				DIALOG.ok(ADDONTITLE, "[COLOR %s]You will need to turn off [COLOR %s]Include All Addons[/COLOR] to disable[/COLOR] [COLOR %s]%s[/COLOR]" % (COLOR2, COLOR1, COLOR1, item))
			except:
				wiz.LogNotify("[COLOR %s]Toggle Cache[/COLOR]" % COLOR1, "[COLOR %s]Invalid id: %s[/COLOR]" % (COLOR2, state))
		else:
			new = 'true' if wiz.getS(state) == 'false' else 'false'
			wiz.setS(state, new)

def viewLogFile():
	mainlog = wiz.Grab_Log(True)
	oldlog  = wiz.Grab_Log(True, True)
	which = 0; logtype = mainlog
	if not oldlog == False and not mainlog == False:
		which = DIALOG.select(ADDONTITLE, ["View %s" % mainlog.replace(LOG, ""), "View %s" % oldlog.replace(LOG, "")])
		if which == -1: wiz.LogNotify('[COLOR %s]View Log[/COLOR]' % COLOR1, '[COLOR %s]View Log Cancelled![/COLOR]' % COLOR2); return
	elif mainlog == False and oldlog == False:
		wiz.LogNotify('[COLOR %s]View Log[/COLOR]' % COLOR1, '[COLOR %s]No Log File Found![/COLOR]' % COLOR2)
		return
	elif not mainlog == False: which = 0
	elif not oldlog == False: which = 1
	logtype = mainlog if which == 0 else oldlog
	msg     = wiz.Grab_Log(False) if which == 0 else wiz.Grab_Log(False, True)
	wiz.TextBox("%s - %s" % (ADDONTITLE, logtype), msg)
def errorList(file):
	errors = []
	a=open(file, encoding='utf-8').read()
	b=a.replace('\n','[CR]').replace('\r','')
	match = re.compile("-->Python callback/script returned the following error<--(.+?)-->End of Python script error report<--").findall(b)
	for item in match:
		errors.append(item)
	return errors
def errorChecking(log=None, count=None, last=None):
	errors = []; error1 = []; error2 = [];
	if log == None:
		curr = wiz.Grab_Log(True, False)
		old = wiz.Grab_Log(True, True)
		if old == False and curr == False:
			if count == None: 
				wiz.LogNotify('[COLOR %s]View Error Log[/COLOR]' % COLOR1, '[COLOR %s]No Log File Found![/COLOR]' % COLOR2)
				return
			else:
				return 0
		if not curr == False: 
			error1 = errorList(curr)
		if not old == False: 
			error2 = errorList(old)
		if len(error2) > 0: 
			for item in error2: errors = [item] + errors
		if len(error1) > 0: 
			for item in error1: errors = [item] + errors
	else:
		error1 = errorList(log)
		if len(error1) > 0:
			for item in error1: errors = [item] + errors
	if not count == None:
		return len(errors)
	elif len(errors) > 0:
		if last == None:
			i = 0; string = ''
			for item in errors:
				i += 1
				string += "[B][COLOR FFFF0000]ERROR NUMBER %s:[/B][/COLOR]%s\n" % (str(i), item.replace(HOME, '/').replace('                                        ', ''))
		else:
			string = "[B][COLOR FFFF0000]Last Error in Log:[/B][/COLOR]%s\n" % (errors[0].replace(HOME, '/').replace('                                        ', ''))
		wiz.TextBox("%s: Errors in Log" % ADDONTITLE, string)
	else:
		wiz.LogNotify('[COLOR %s]View Error Log[/COLOR]' % COLOR1, '[COLOR %s]No Errors Found![/COLOR]' % COLOR2)
		
def log_tools():
	errors = int(errorChecking(count=True))
	err = str(errors)
	errorsfound = '[COLOR red]%s[/COLOR] Found'  % (err) if errors > 0 else 'None Found'
	on = '[B][COLOR FF00FF00]ON[/COLOR][/B]'; off = '[B][COLOR FFFF0000]OFF[/COLOR][/B]'
	if wiz.Grab_Log(True) == False: kodilog = 0
	else: kodilog = errorChecking(wiz.Grab_Log(True), True)
	if wiz.Grab_Log(True, True) == False: kodioldlog = 0
	else: kodioldlog = errorChecking(wiz.Grab_Log(True,True), True)
	errorsinlog = int(kodilog) + int(kodioldlog)
	wizlogsize = ': [COLOR red]Not Found[/COLOR]' if not os.path.exists(WIZLOG) else ": [COLOR green]%s[/COLOR]" % wiz.convertSize(os.path.getsize(WIZLOG))
	return errorsfound
		
		

ACTION_PREVIOUS_MENU 			=  10	## ESC action
ACTION_NAV_BACK 				=  92	## Backspace action
ACTION_MOVE_LEFT				=   1	## Left arrow key
ACTION_MOVE_RIGHT 				=   2	## Right arrow key
ACTION_MOVE_UP 					=   3	## Up arrow key
ACTION_MOVE_DOWN 				=   4	## Down arrow key
ACTION_MOUSE_WHEEL_UP 			= 104	## Mouse wheel up
ACTION_MOUSE_WHEEL_DOWN			= 105	## Mouse wheel down
ACTION_MOVE_MOUSE 				= 107	## Down arrow key
ACTION_SELECT_ITEM				=   7	## Number Pad Enter
ACTION_BACKSPACE				= 110	## ?
ACTION_MOUSE_LEFT_CLICK 		= 100
ACTION_MOUSE_LONG_CLICK 		= 108
def LogViewer(default=None):
	class LogViewer(xbmcgui.WindowXMLDialog):
		def __init__(self,*args,**kwargs):
			self.default = kwargs['default']
		def onInit(self):
			self.title      = 101
			self.msg        = 102
			self.scrollbar  = 103
			self.upload     = 201
			self.kodi       = 202
			self.kodiold    = 203
			self.wizard     = 204 
			self.okbutton   = 205 
			f = open(self.default, 'r', encoding='utf-8')
			self.logmsg = f.read()
			f.close()
			self.titlemsg = "%s: %s" % (ADDONTITLE, self.default.replace(LOG, '').replace(ADDONDATA, ''))
			self.showdialog()
		def showdialog(self):
			self.getControl(self.title).setLabel(self.titlemsg)
			self.getControl(self.msg).setText(wiz.highlightText(self.logmsg))
			self.setFocusId(self.scrollbar)
		def onClick(self, controlId):
			if   controlId == self.okbutton: self.close()
			elif controlId == self.upload: self.close(); uploadLog.Main()
			elif controlId == self.kodi:
				newmsg = wiz.Grab_Log(False)
				filename = wiz.Grab_Log(True)
				if newmsg == False:
					self.titlemsg = "%s: View Log Error" % ADDONTITLE
					self.getControl(self.msg).setText("Log File Does Not Exists!")
				else:
					self.titlemsg = "%s: %s" % (ADDONTITLE, filename.replace(LOG, ''))
					self.getControl(self.title).setLabel(self.titlemsg)
					self.getControl(self.msg).setText(wiz.highlightText(newmsg))
					self.setFocusId(self.scrollbar)
			elif controlId == self.kodiold:  
				newmsg = wiz.Grab_Log(False, True)
				filename = wiz.Grab_Log(True, True)
				if newmsg == False:
					self.titlemsg = "%s: View Log Error" % ADDONTITLE
					self.getControl(self.msg).setText("Log File Does Not Exists!")
				else:
					self.titlemsg = "%s: %s" % (ADDONTITLE, filename.replace(LOG, ''))
					self.getControl(self.title).setLabel(self.titlemsg)
					self.getControl(self.msg).setText(wiz.highlightText(newmsg))
					self.setFocusId(self.scrollbar)
			elif controlId == self.wizard:
				newmsg = wiz.Grab_Log(False, False, True)
				filename = wiz.Grab_Log(True, False, True)
				if newmsg == False:
					self.titlemsg = "%s: View Log Error" % ADDONTITLE
					self.getControl(self.msg).setText("Log File Does Not Exists!")
				else:
					self.titlemsg = "%s: %s" % (ADDONTITLE, filename.replace(ADDONDATA, ''))
					self.getControl(self.title).setLabel(self.titlemsg)
					self.getControl(self.msg).setText(wiz.highlightText(newmsg))
					self.setFocusId(self.scrollbar)
		def onAction(self, action):
			if   action == ACTION_PREVIOUS_MENU: self.close()
			elif action == ACTION_NAV_BACK: self.close()
	if default == None: default = wiz.Grab_Log(True)
	lv = LogViewer( "LogViewer.xml" , ADDON.getAddonInfo('path'), 'DefaultSkin', default=default)
	lv.doModal()
	del lv
##########################################
#  `7MM"""YMM MMP""MM""YMM   .g8"""bgd   #
#    MM    `7 P'   MM   `7 .dP'     `M   #
#    MM   d        MM      dM'       `   #
#    MM""MM        MM      MM            #
#    MM   Y        MM      MM.    `7MMF' #
#    MM            MM      `Mb.     MM   #
#  .JMML.        .JMML.      `"bmmmdPY   #
########################################## 
def removeAddon(addon, name, over=False):
	if not over == False:
		yes = 1
	else: 
		yes = DIALOG.yesno(ADDONTITLE, '[COLOR %s]Are you sure you want to delete the addon:'% COLOR2 + '\nName: [COLOR %s]%s[/COLOR]' % (COLOR1, name) + '\nID: [COLOR %s]%s[/COLOR][/COLOR]' % (COLOR1, addon), yeslabel='[B][COLOR FF00FF00]Remove Addon[/COLOR][/B]', nolabel='[B][COLOR FFFF0000]Don\'t Remove[/COLOR][/B]')
	if yes == 1:
		folder = os.path.join(ADDONS, addon)
		wiz.log("Removing Addon %s" % addon)
		wiz.cleanHouse(folder)
		xbmc.sleep(200)
		try: shutil.rmtree(folder)
		except Exception as e: wiz.log("Error removing %s" % addon, xbmc.LOGINFO)
		removeAddonData(addon, name, over)
	if over == False:
		wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]%s Removed[/COLOR]" % (COLOR2, name))
def removeAddonData(addon, name=None, over=False):
	if addon == 'all':
		if DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you like to remove [COLOR %s]ALL[/COLOR] addon data stored in you Userdata folder?[/COLOR]' % (COLOR2, COLOR1), yeslabel='[B][COLOR FF00FF00]Remove Data[/COLOR][/B]', nolabel='[B][COLOR FFFF0000]Don\'t Remove[/COLOR][/B]'):
			wiz.cleanHouse(ADDOND)
		else: wiz.LogNotify('[COLOR %s]Remove Addon Data[/COLOR]' % COLOR1, '[COLOR %s]Cancelled![/COLOR]' % COLOR2)
	elif addon == 'uninstalled':
		if DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you like to remove [COLOR %s]ALL[/COLOR] addon data stored in you Userdata folder for uninstalled addons?[/COLOR]' % (COLOR2, COLOR1), yeslabel='[B][COLOR FF00FF00]Remove Data[/COLOR][/B]', nolabel='[B][COLOR FFFF0000]Don\'t Remove[/COLOR][/B]'):
			total = 0
			for folder in glob.glob(os.path.join(ADDOND, '*')):
				foldername = folder.replace(ADDOND, '').replace('\\', '').replace('/', '')
				if foldername in EXCLUDES: pass
				elif os.path.exists(os.path.join(ADDONS, foldername)): pass
				else: wiz.cleanHouse(folder); total += 1; wiz.log(folder); shutil.rmtree(folder)
			wiz.LogNotify('[COLOR %s]Clean up Uninstalled[/COLOR]' % COLOR1, '[COLOR %s]%s Folders(s) Removed[/COLOR]' % (COLOR2, total))
		else: wiz.LogNotify('[COLOR %s]Remove Addon Data[/COLOR]' % COLOR1, '[COLOR %s]Cancelled![/COLOR]' % COLOR2)
	elif addon == 'empty':
		if DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you like to remove [COLOR %s]ALL[/COLOR] empty addon data folders in you Userdata folder?[/COLOR]' % (COLOR2, COLOR1), yeslabel='[B][COLOR FF00FF00]Remove Data[/COLOR][/B]', nolabel='[B][COLOR FFFF0000]Don\'t Remove[/COLOR][/B]'):
			total = wiz.emptyfolder(ADDOND)
			wiz.LogNotify('[COLOR %s]Remove Empty Folders[/COLOR]' % COLOR1, '[COLOR %s]%s Folders(s) Removed[/COLOR]' % (COLOR2, total))
		else: wiz.LogNotify('[COLOR %s]Remove Empty Folders[/COLOR]' % COLOR1, '[COLOR %s]Cancelled![/COLOR]' % COLOR2)
	else:
		addon_data = os.path.join(USERDATA, 'addon_data', addon)
		if addon in EXCLUDES:
			wiz.LogNotify("[COLOR %s]Protected Plugin[/COLOR]" % COLOR1, "[COLOR %s]Not allowed to remove Addon_Data[/COLOR]" % COLOR2)
		elif os.path.exists(addon_data):  
			if DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you also like to remove the addon data for:[/COLOR]' % COLOR2 + '\n[COLOR %s]%s[/COLOR]' % (COLOR1, addon), yeslabel='[B][COLOR FF00FF00]Remove Data[/COLOR][/B]', nolabel='[B][COLOR FFFF0000]Don\'t Remove[/COLOR][/B]'):
				wiz.cleanHouse(addon_data)
				try:
					shutil.rmtree(addon_data)
				except:
					wiz.log("Error deleting: %s" % addon_data)
			else: 
				wiz.log('Addon data for %s was not removed' % addon)
	wiz.refresh()
def restoreit(type):
	if type == 'build':
		x = freshStart('restore')
		if x == False: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Local Restore Cancelled[/COLOR]" % COLOR2); return
	if not wiz.currSkin() in ['skin.estuary']:
		wiz.skinToDefault('Restore Backup')
	wiz.restoreLocal(type)
def restoreextit(type):
	if type == 'build':
		x = freshStart('restore')
		if x == False: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]External Restore Cancelled[/COLOR]" % COLOR2); return
	wiz.restoreExternal(type)
def buildInfo(name):
	if wiz.workingURL(BUILDFILE) == True:
		if wiz.checkBuild(name, 'url'):
			name, version, url, kodi, icon, fanart, adult, description = wiz.checkBuild(name, 'all')
			adult = 'Yes' if adult.lower() == 'yes' else 'No'
			msg  = "[COLOR %s]Build Name:[/COLOR] [COLOR %s]%s[/COLOR][CR]" % (COLOR2, COLOR1, name)
			msg += "[COLOR %s]Build Version:[/COLOR] [COLOR %s]%s[/COLOR][CR]" % (COLOR2, COLOR1, version)
			msg += "[COLOR %s]Kodi Version:[/COLOR] [COLOR %s]%s[/COLOR][CR]" % (COLOR2, COLOR1, kodi)
			msg += "[COLOR %s]Adult Content:[/COLOR] [COLOR %s]%s[/COLOR][CR]" % (COLOR2, COLOR1, adult)
			msg += "[COLOR %s]Description:[/COLOR] [COLOR %s]%s[/COLOR][CR]" % (COLOR2, COLOR1, description)
			wiz.TextBox(ADDONTITLE, msg)
		else: wiz.log("Invalid Build Name!")
	else: wiz.log("Build text file not working: %s" % BUILDFILE)
def dependsList(plugin):
	addonxml = os.path.join(ADDONS, plugin, 'addon.xml')
	if os.path.exists(addonxml):
		source = open(addonxml,mode='r', encoding='utf-8'); link = source.read(); source.close(); 
		match  = wiz.parseDOM(link, 'import', ret='addon')
		items  = []
		for depends in match:
			if not 'xbmc.python' in depends:
				items.append(depends)
		return items
	return []
def manageSaveData(do):
	if do == 'import':
		TEMP = os.path.join(ADDONDATA, 'temp')
		if not os.path.exists(TEMP): os.makedirs(TEMP)
		source = DIALOG.browse(1, '[COLOR %s]Select the location of the SaveData.zip[/COLOR]' % COLOR2, 'files', '.zip', False, False, HOME)
		if not source.endswith('.zip'):
			wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Import Data Error![/COLOR]" % (COLOR2))
			return
		tempfile = os.path.join(MYBUILDS, 'SaveData.zip')
		goto = xbmcvfs.copy(source, tempfile)
		wiz.log("%s" % str(goto))
		extract.all(xbmcvfs.translatePath(tempfile), TEMP)
		trakt  = os.path.join(TEMP, 'trakt')
		login  = os.path.join(TEMP, 'login')
		debrid = os.path.join(TEMP, 'debrid')
		premiumize = os.path.join(TEMP, 'premiumize')
		alldebrid  = os.path.join(TEMP, 'alldebrid')
		torbox     = os.path.join(TEMP, 'torbox')
		linksnappy = os.path.join(TEMP, 'linksnappy')
		x = 0
		if os.path.exists(trakt):
			x += 1
			files = os.listdir(trakt)
			if not os.path.exists(traktit.TRAKTFOLD): os.makedirs(traktit.TRAKTFOLD)
			for item in files:
				old  = os.path.join(traktit.TRAKTFOLD, item)
				temp = os.path.join(trakt, item)
				if os.path.exists(old):
					if not DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like replace the current [COLOR %s]%s[/COLOR] file?" % (COLOR2, COLOR1, item), yeslabel="[B][COLOR FF00FF00]Yes Replace[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]No Skip[/COLOR][/B]"): continue
					else: os.remove(old)
				shutil.copy(temp, old)
			traktit.importlist('all')
			traktit.traktIt('restore', 'all')
		if os.path.exists(login):
			x += 1
			files = os.listdir(login)
			if not os.path.exists(loginit.LOGINFOLD): os.makedirs(loginit.LOGINFOLD)
			for item in files:
				old  = os.path.join(loginit.LOGINFOLD, item)
				temp = os.path.join(login, item)
				if os.path.exists(old):
					if not DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like replace the current [COLOR %s]%s[/COLOR] file?" % (COLOR2, COLOR1, item), yeslabel="[B][COLOR FF00FF00]Yes Replace[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]No Skip[/COLOR][/B]"): continue
					else: os.remove(old)
				shutil.copy(temp, old)
			loginit.importlist('all')
			loginit.loginIt('restore', 'all')
		if os.path.exists(debrid):
			x += 1
			files = os.listdir(debrid)
			if not os.path.exists(debridit.REALFOLD): os.makedirs(debridit.REALFOLD)
			for item in files:
				old  = os.path.join(debridit.REALFOLD, item)
				temp = os.path.join(debrid, item)
				if os.path.exists(old):
					if not DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like replace the current [COLOR %s]%s[/COLOR] file?" % (COLOR2, COLOR1, item), yeslabel="[B][COLOR FF00FF00]Yes Replace[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]No Skip[/COLOR][/B]"): continue
					else: os.remove(old)
				shutil.copy(temp, old)
			debridit.importlist('all')
			debridit.debridIt('restore', 'all')
		if os.path.exists(premiumize):
			x += 1
			files = os.listdir(premiumize)
			if not os.path.exists(premiumizeit.PREMFOLD): os.makedirs(premiumizeit.PREMFOLD)
			for item in files:
				old  = os.path.join(premiumizeit.PREMFOLD, item)
				temp = os.path.join(premiumize, item)
				if os.path.exists(old):
					if not DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like replace the current [COLOR %s]%s[/COLOR] file?" % (COLOR2, COLOR1, item), yeslabel="[B][COLOR FF00FF00]Yes Replace[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]No Skip[/COLOR][/B]"): continue
					else: os.remove(old)
				shutil.copy(temp, old)
			premiumizeit.importlist('all')
			premiumizeit.premiumizeIt('restore', 'all')
		if os.path.exists(alldebrid):
			x += 1
			files = os.listdir(alldebrid)
			if not os.path.exists(alldebridit.ALLDEBRFOLD): os.makedirs(alldebridit.ALLDEBRFOLD)
			for item in files:
				old  = os.path.join(alldebridit.ALLDEBRFOLD, item)
				temp = os.path.join(alldebrid, item)
				if os.path.exists(old):
					if not DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like replace the current [COLOR %s]%s[/COLOR] file?" % (COLOR2, COLOR1, item), yeslabel="[B][COLOR FF00FF00]Yes Replace[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]No Skip[/COLOR][/B]"): continue
					else: os.remove(old)
				shutil.copy(temp, old)
			alldebridit.importlist('all')
			alldebridit.alldebridIt('restore', 'all')
		if os.path.exists(torbox):
			x += 1
			files = os.listdir(torbox)
			if not os.path.exists(torboxit.TORBOXFOLD): os.makedirs(torboxit.TORBOXFOLD)
			for item in files:
				old  = os.path.join(torboxit.TORBOXFOLD, item)
				temp = os.path.join(torbox, item)
				if os.path.exists(old):
					if not DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like replace the current [COLOR %s]%s[/COLOR] file?" % (COLOR2, COLOR1, item), yeslabel="[B][COLOR FF00FF00]Yes Replace[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]No Skip[/COLOR][/B]"): continue
					else: os.remove(old)
				shutil.copy(temp, old)
			torboxit.importlist('all')
			torboxit.torboxIt('restore', 'all')
		if os.path.exists(linksnappy):
			x += 1
			files = os.listdir(linksnappy)
			if not os.path.exists(linksnappit.LINKSNAPPYFOLD): os.makedirs(linksnappit.LINKSNAPPYFOLD)
			for item in files:
				old  = os.path.join(linksnappit.LINKSNAPPYFOLD, item)
				temp = os.path.join(linksnappy, item)
				if os.path.exists(old):
					if not DIALOG.yesno(ADDONTITLE, "[COLOR %s]Would you like replace the current [COLOR %s]%s[/COLOR] file?" % (COLOR2, COLOR1, item), yeslabel="[B][COLOR FF00FF00]Yes Replace[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]No Skip[/COLOR][/B]"): continue
					else: os.remove(old)
				shutil.copy(temp, old)
			linksnappit.importlist('all')
			linksnappit.linksnappyIt('restore', 'all')
		wiz.cleanHouse(TEMP)
		wiz.removeFolder(TEMP)
		os.remove(tempfile)
		if x == 0: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Save Data Import Failed[/COLOR]" % COLOR2)
		else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Save Data Import Complete[/COLOR]" % COLOR2)
	elif do == 'export':
		mybuilds = xbmcvfs.translatePath(MYBUILDS)
		dir = [traktit.TRAKTFOLD, debridit.REALFOLD, loginit.LOGINFOLD, premiumizeit.PREMFOLD, alldebridit.ALLDEBRFOLD, torboxit.TORBOXFOLD, linksnappit.LINKSNAPPYFOLD]
		traktit.traktIt('update', 'all')
		loginit.loginIt('update', 'all')
		debridit.debridIt('update', 'all')
		premiumizeit.premiumizeIt('update', 'all')
		alldebridit.alldebridIt('update', 'all')
		torboxit.torboxIt('update', 'all')
		linksnappit.linksnappyIt('update', 'all')
		source = DIALOG.browse(3, '[COLOR %s]Select where you wish to export the savedata zip?[/COLOR]' % COLOR2, 'files', '', False, True, HOME)
		source = xbmcvfs.translatePath(source)
		tempzip = os.path.join(mybuilds, 'SaveData.zip')
		zipf = zipfile.ZipFile(tempzip, mode='w')
		for fold in dir:
			if os.path.exists(fold):
				files = os.listdir(fold)
				for file in files:
					zipf.write(os.path.join(fold, file), os.path.join(fold, file).replace(ADDONDATA, ''), zipfile.ZIP_DEFLATED)
		zipf.close()
		if source == mybuilds:
			DIALOG.ok(ADDONTITLE, "[COLOR %s]Save data has been backed up to:[/COLOR]" % (COLOR2) + "\n[COLOR %s]%s[/COLOR]" % (COLOR1, tempzip))
		else:
			try:
				xbmcvfs.copy(tempzip, os.path.join(source, 'SaveData.zip'))
				DIALOG.ok(ADDONTITLE, "[COLOR %s]Save data has been backed up to:[/COLOR]" % (COLOR2) + "\n[COLOR %s]%s[/COLOR]" % (COLOR1, os.path.join(source, 'SaveData.zip')))
			except:
				DIALOG.ok(ADDONTITLE, "[COLOR %s]Save data has been backed up to:[/COLOR]" % (COLOR2) + "\n[COLOR %s]%s[/COLOR]" % (COLOR1, tempzip))
###########################
###### Fresh Install ######
###########################
def freshStart(install=None, over=False):
	if KEEPTRAKT == 'true':
		traktit.autoUpdate('all')
		wiz.setS('traktlastsave', str(THREEDAYS))
	if KEEPREAL == 'true':
		debridit.autoUpdate('all')
		wiz.setS('debridlastsave', str(THREEDAYS))
	if KEEPLOGIN == 'true':
		loginit.autoUpdate('all')
		wiz.setS('loginlastsave', str(THREEDAYS))
	if KEEPPREMIUMIZE == 'true':
		premiumizeit.autoUpdate('all')
		wiz.setS('premiumizelastsave', str(THREEDAYS))
	if KEEPALLDEBRID == 'true':
		alldebridit.autoUpdate('all')
		wiz.setS('alldebridlastsave', str(THREEDAYS))
	if KEEPTORBOX == 'true':
		torboxit.autoUpdate('all')
		wiz.setS('torboxlastsave', str(THREEDAYS))
	if KEEPLINKSNAPPY == 'true':
		linksnappit.autoUpdate('all')
		wiz.setS('linksnappylastsave', str(THREEDAYS))
	if over == True: yes_pressed = 1
	elif install == 'restore': yes_pressed=DIALOG.yesno(ADDONTITLE, "[COLOR %s]Click [B][COLOR springgreen] - Yes - [/COLOR][/B]" % COLOR2 + "\nTo Erase Your Current Build, \r\nThen Install a Local or External Stored Build Back Up[/COLOR]", nolabel='[B][COLOR FFFF0000]No, Cancel[/COLOR][/B]', yeslabel='[B][COLOR springgreen]Yes[/COLOR][/B]')
	elif install: yes_pressed=DIALOG.yesno(ADDONTITLE, "[COLOR %s]Click [B][COLOR springgreen] - Yes - [/COLOR][/B]" % COLOR2 + "\nTo Erase Your Current Build, \r\nThen Fresh Install [COLOR %s]%s[/COLOR]!!" % (COLOR1, install), nolabel='[B][COLOR FFFF0000]No, Cancel[/COLOR][/B]', yeslabel='[B][COLOR springgreen]Yes[/COLOR][/B]')
	else: yes_pressed=DIALOG.yesno(ADDONTITLE, "[COLOR %s]Do you wish to restore your" % COLOR2 + "\nConfiguration to default settings?[/COLOR]", nolabel='[B][COLOR FFFF0000]No, Cancel[/COLOR][/B]', yeslabel='[B][COLOR springgreen]Yes[/COLOR][/B]')
	if yes_pressed:
		if not wiz.currSkin() in ['skin.estuary']:
			skin = 'skin.estuary'
			#yes=DIALOG.yesno(ADDONTITLE, "[COLOR %s]The skin needs to be set back to [COLOR %s]%s[/COLOR]" % (COLOR2, COLOR1, skin[5:]), "Before doing a fresh install to clear all Texture files,", "Would you like us to do that for you?[/COLOR]", yeslabel="[B][COLOR springgreen]Switch Skins[/COLOR][/B]", nolabel="[B][COLOR FFFF0000]I'll Do It[/COLOR][/B]";
			#if yes:
			
			'''
			skinSwitch.swapSkins(skin)
			xbmc.log('swapskin= ' + str(install), xbmc.LOGINFO)
			x = 0
			xbmc.sleep(1000)
			while not xbmc.getCondVisibility("Window.isVisible(yesnodialog)") and x < 150:
				x += 1
				xbmc.sleep(200)
				#wiz.ebi('SendAction(Select)')
			if xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
				wiz.ebi('SendClick(11)')
			else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), '[COLOR %s]Fresh Install: Skin Swap Timed Out![/COLOR]' % COLOR2); return False
			xbmc.sleep(1000)
		if not wiz.currSkin() in ['skin.estuary']:
			wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), '[COLOR %s]Fresh Install: Skin Swap Failed![/COLOR]' % COLOR2)
			return
		'''
			
		wiz.addonUpdates('set')
		xbmcPath=os.path.abspath(HOME)
		DP.create(ADDONTITLE,"[COLOR %s]Calculating files and folders" % COLOR2 + '\n' + 'Please Wait![/COLOR]')
		total_files = sum([len(files) for r, d, files in os.walk(xbmcPath)]); del_file = 0
		DP.update(0, "[COLOR %s]Gathering Excludes list." % COLOR2)
		EXCLUDES.append('My_Builds')
		EXCLUDES.append('archive_cache')
		if KEEPREPOS == 'true':
			repos = glob.glob(os.path.join(ADDONS, 'repo*/'))
			for item in repos:
				repofolder = os.path.split(item[:-1])[1]
				if not repofolder == EXCLUDES:
					EXCLUDES.append(repofolder)
		if KEEPSUPER == 'true':
			EXCLUDES.append('plugin.program.super.favourites')
		if KEEPWHITELIST == 'true':
			pvr = ''
			whitelist = wiz.whiteList('read')
			if len(whitelist) > 0:
				for item in whitelist:
					try: name, id, fold = item
					except: pass
					if fold.startswith('pvr'): pvr = id 
					depends = dependsList(fold)
					for plug in depends:
						if not plug in EXCLUDES:
							EXCLUDES.append(plug)
						depends2 = dependsList(plug)
						for plug2 in depends2:
							if not plug2 in EXCLUDES:
								EXCLUDES.append(plug2)
					if not fold in EXCLUDES:
						EXCLUDES.append(fold)
				if not pvr == '': wiz.setS('pvrclient', fold)
		if wiz.getS('pvrclient') == '':
			for item in EXCLUDES:
				if item.startswith('pvr'):
					wiz.setS('pvrclient', item)
		DP.update(0, "[COLOR %s]Clearing out files and folders:" % COLOR2)
		latestAddonDB = wiz.latestDB('Addons')
		for root, dirs, files in os.walk(xbmcPath,topdown=True):
			dirs[:] = [d for d in dirs if d not in EXCLUDES]
			for name in files:
				del_file += 1
				fold = root.replace('/','\\').split('\\')
				x = len(fold)-1
				if name == 'sources.xml' and fold[-1] == 'userdata' and KEEPSOURCES == 'true': wiz.log("Keep Sources: %s" % os.path.join(root, name), xbmc.LOGINFO)
				elif name == 'favourites.xml' and fold[-1] == 'userdata' and KEEPFAVS == 'true': wiz.log("Keep Favourites: %s" % os.path.join(root, name), xbmc.LOGINFO)
				elif name == 'profiles.xml' and fold[-1] == 'userdata' and KEEPPROFILES == 'true': wiz.log("Keep Profiles: %s" % os.path.join(root, name), xbmc.LOGINFO)
				elif name == 'advancedsettings.xml' and fold[-1] == 'userdata' and KEEPADVANCED == 'true':  wiz.log("Keep Advanced Settings: %s" % os.path.join(root, name), xbmc.LOGINFO)
				elif name in LOGFILES: wiz.log("Keep Log File: %s" % name, xbmc.LOGINFO)
				elif name.endswith('.db'):
					try:
						if name == latestAddonDB: wiz.log("Ignoring %s on v%s" % (name, KODIV), xbmc.LOGINFO)
						else: os.remove(os.path.join(root,name))
					except Exception as e: 
						if not name.startswith('Textures13'):
							wiz.log('Failed to delete, Purging DB', xbmc.LOGINFO)
							wiz.log("-> %s" % (str(e)), xbmc.LOGINFO)
							wiz.purgeDb(os.path.join(root,name))
				else:
					DP.update(int(wiz.percentage(del_file, total_files)), '[COLOR %s]File: [/COLOR][COLOR %s]%s[/COLOR]' % (COLOR2, COLOR1, name))
					try: os.remove(os.path.join(root,name))
					except Exception as e: 
						wiz.log("Error removing %s" % os.path.join(root, name), xbmc.LOGINFO)
						wiz.log("-> / %s" % (str(e)), xbmc.LOGINFO)
			if DP.iscanceled(): 
				DP.close()
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Fresh Start Cancelled[/COLOR]" % COLOR2)
				return False
		for root, dirs, files in os.walk(xbmcPath,topdown=True):
			dirs[:] = [d for d in dirs if d not in EXCLUDES]
			for name in dirs:
				DP.update(100, 'Cleaning Up Empty Folder: [COLOR %s]%s[/COLOR]' % (COLOR1, name))
				if name not in ["Database","userdata","temp","addons","addon_data"]:
					shutil.rmtree(os.path.join(root,name),ignore_errors=True, onerror=None)
			if DP.iscanceled(): 
				DP.close()
				wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Fresh Start Cancelled[/COLOR]" % COLOR2)
				return False
		DP.close()
		wiz.clearS('build')
		if over == True:
			return True
		elif install == 'restore': 
			return True
		elif install: 
			buildWizard(install, 'normal', over=True)
		else:
			if INSTALLMETHOD == 1: todo = 1
			elif INSTALLMETHOD == 2: todo = 0
			else: todo = DIALOG.yesno(ADDONTITLE, "[COLOR %s]You Need To [COLOR %s]Force close[/COLOR] This App [COLOR %s]And[/COLOR] Then Restart It Again[/COLOR]" % (COLOR2, COLOR1, COLOR1), yeslabel="[B][COLOR white]>>>>>>[/COLOR][/B]", nolabel="[B][COLOR springgreen]Force Close[/COLOR][/B]")
			if todo == 1: wiz.reloadFix('fresh')
			else: wiz.addonUpdates('reset'); wiz.killxbmc(True)
	else: 
		if not install == 'restore':
			wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), '[COLOR %s]Fresh Install: Cancelled![/COLOR]' % COLOR2)
			wiz.refresh()
#############################
###DELETE CACHE##############
####THANKS GUYS @ NaN #######


def clearCache(shortcut=False):
	if DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you like to clear cache?[/COLOR]' % COLOR2, nolabel='[B][COLOR FFFF0000]No, Cancel[/COLOR][/B]', yeslabel='[B][COLOR FF00FF00]Clear Cache[/COLOR][/B]'):
		wiz.clearCache()
		wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Cache Cleared![/COLOR]" % COLOR2, 3000)
		if shortcut is False:
			DC.setLabel('Size: [B][COLOR lime]0.0 B[/B][/COLOR]')

def clearArchive():
	if DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you like to clear the \'Archive_Cache\' folder?[/COLOR]' % COLOR2, nolabel='[B][COLOR FFFF0000]No, Cancel[/COLOR][/B]', yeslabel='[B][COLOR FF00FF00]Yes Clear[/COLOR][/B]'):
		wiz.clearArchive()

def clearPackages(shortcut=False):
	if DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you like to delete Packages?[/COLOR]' % COLOR2, nolabel='[B][COLOR FFFF0000]No, Cancel[/COLOR][/B]', yeslabel='[B][COLOR FF00FF00]Delete[/COLOR][/B]'):
		wiz.clearPackages('total')
		wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Packages Cleared![/COLOR]" % COLOR2, 3000)
		if shortcut is False:
			DPK.setLabel('Size: [B][COLOR lime]0.0 B[/B][/COLOR]')
			TPK.setLabel('Files: [B][COLOR lime]0[/B][/COLOR]')

def totalClean(shortcut=False):
	if DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you like to clear cache, packages and thumbnails?[/COLOR]' % COLOR2, nolabel='[B][COLOR FFFF0000]Cancel Process[/COLOR][/B]',yeslabel='[B][COLOR FF00FF00]Clean All[/COLOR][/B]'):
		wiz.clearCache()
		wiz.clearPackages('total')
		clearThumb('total', shortcut=True)
		if shortcut is False:
			TC.setLabel('Size: [B][COLOR lime]0.0 B[/B][/COLOR]')
			DC.setLabel('Size: [B][COLOR lime]0.0 B[/B][/COLOR]')
			DPK.setLabel('Size: [B][COLOR lime]0.0 B[/B][/COLOR]')
			TPK.setLabel('Files: [B][COLOR lime]0[/B][/COLOR]')
			DTH.setLabel('Size: [B][COLOR lime]0.0 B[/B][/COLOR]')
			TTH.setLabel('Files: [B][COLOR lime]0[/B][/COLOR]')
		wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Total Clean-Up Complete![/COLOR]" % COLOR2, 3000)
def clearThumb(type=None, shortcut=False):
	latest = wiz.latestDB('Textures')
	if not type == None: choice = 1
	else: choice = DIALOG.yesno(ADDONTITLE, '[COLOR %s]Would you like to delete the %s and Thumbnails folder?' % (COLOR2, latest) + "\nThey will repopulate on the next startup[/COLOR]", nolabel='[B][COLOR FFFF0000]Don\'t Delete[/COLOR][/B]', yeslabel='[B][COLOR FF00FF00]Delete Thumbs[/COLOR][/B]')
	if choice == 1:
		try: wiz.removeFile(os.path.join(DATABASE, latest))
		except: wiz.log('Failed to delete, Purging DB.'); wiz.purgeDb(latest)
		wiz.removeFolder(THUMBS)
		if shortcut is False:
			xbmcgui.Dialog().notification(ADDONTITLE, '[COLOR %s]Clear Thumbnails: Success![/COLOR]' % COLOR2, ICON, 7000, sound=False)
			DTH.setLabel('Size: [B][COLOR lime]0.0 B[/B][/COLOR]')
			TTH.setLabel('Files: [B][COLOR lime]0[/B][/COLOR]')
	else: wiz.log('Clear thumbnames cancelled')
	wiz.redoThumbs()
def purgeDb():
	DB = []; display = []
	for dirpath, dirnames, files in os.walk(HOME):
		for f in fnmatch.filter(files, '*.db'):
			if f != 'Thumbs.db':
				found = os.path.join(dirpath, f)
				DB.append(found)
				dir = found.replace('\\', '/').split('/')
				display.append('(%s) %s' % (dir[len(dir)-2], dir[len(dir)-1]))
	choice = DIALOG.multiselect("[COLOR %s]Select DB File to Purge[/COLOR]" % COLOR2, display)
	if choice == None: wiz.LogNotify("[COLOR %s]Purge Database[/COLOR]" % COLOR1, "[COLOR %s]Cancelled[/COLOR]" % COLOR2)
	elif len(choice) == 0: wiz.LogNotify("[COLOR %s]Purge Database[/COLOR]" % COLOR1, "[COLOR %s]Cancelled[/COLOR]" % COLOR2)
	else: 
		for purge in choice: wiz.purgeDb(DB[purge])
##########################
### DEVELOPER MENU #######
##########################
def testnotify():
	url = wiz.workingURL(NOTIFICATION)
	if url == True:
		try:
			id, msg = wiz.splitNotify(NOTIFICATION)
			if id == False: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Notification: Not Formated Correctly[/COLOR]" % COLOR2); return
			notify.notification(msg, True)
		except Exception as e:
			wiz.log("Error on Notifications Window: %s" % str(e), xbmc.LOGERROR)
	else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Invalid URL for Notification[/COLOR]" % COLOR2)
def testupdate():
	if BUILDNAME == "":
		notify.updateWindow()
	else:
		notify.updateWindow(BUILDNAME, BUILDVERSION, BUILDLATEST, wiz.checkBuild(BUILDNAME, 'icon'), wiz.checkBuild(BUILDNAME, 'fanart'))
def testfirst():
	notify.firstRun()
def testfirstRun():
	notify.firstRunSettings()
	
	

###########################
## Making the Directory####
###########################
def Add_Directory_Item(handle, url, listitem, isFolder):
	xbmcplugin.addDirectoryItem(handle, url, listitem, isFolder)
def addDir2(name,url,mode,iconimage,fanart):
		u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&iconimage="+urllib.parse.quote_plus(iconimage)
		ok=True
		liz=xbmcgui.ListItem(name)
		liz.setArt({'thumb': 'DefaultFolder.png', 'icon': iconimage, 'fanart': fanart})
		liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": name } )
		liz.setProperty('fanart_image', fanart)
		return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)

def addFolder(type,name,url,mode,iconimage = '',FanArt = '',video = '',description = ''):
	if type != 'folder2' and type != 'addon':
		if len(iconimage) > 0:
			iconimage = Images + iconimage
		else:##F#T#G##
			iconimage = 'DefaultFolder.png'
	if type == 'addon':
		if len(iconimage) > 0:
			iconimage = iconimage
		else:
			iconimage = 'none'
	if FanArt == '':
		FanArt = FanArt
	u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&FanArt="+urllib.parse.quote_plus(FanArt)+"&video="+urllib.parse.quote_plus(video)+"&description="+urllib.parse.quote_plus(description)
	ok=True
	liz=xbmcgui.ListItem(name)
	liz.setArt({'thumb': 'DefaultFolder.png', 'icon': iconimage, 'fanart': FanArt})
	liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": description } )
	liz.setProperty( "FanArt_Image", FanArt )
	liz.setProperty( "Build.Video", video )
	if (type=='folder') or (type=='folder2') or (type=='tutorial_folder') or (type=='news_folder'):
		return Add_Directory_Item(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
	else:
		return Add_Directory_Item(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
	return ok
def addDir(display, mode=None, name=None, url=None, menu=None, description=ADDONTITLE, overwrite=True, fanart=FANART, icon=ICON, themeit=None):
	u = sys.argv[0]
	if not mode == None: u += "?mode=%s" % urllib.parse.quote_plus(mode)
	if not name == None: u += "&name="+urllib.parse.quote_plus(name)
	if not url == None: u += "&url="+urllib.parse.quote_plus(url)
	ok=True
	if themeit: display = themeit % display
	liz=xbmcgui.ListItem(display)
	liz.setArt({'thumb': 'DefaultFolder.png', 'icon': icon, 'fanart': fanart})
	liz.setInfo( type="Video", infoLabels={ "Title": display, "Plot": description} )
	liz.setProperty( "Fanart_Image", fanart )
	if not menu == None: liz.addContextMenuItems(menu, replaceItems=overwrite)
	ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
	return ok
def addFile(display, mode=None, name=None, url=None, menu=None, description=ADDONTITLE, overwrite=True, fanart=FANART, icon=ICON, themeit=None):
	u = sys.argv[0]
	if not mode == None: u += "?mode=%s" % urllib.parse.quote_plus(mode)
	if not name == None: u += "&name="+urllib.parse.quote_plus(name)
	if not url == None: u += "&url="+urllib.parse.quote_plus(url)
	ok=True
	if themeit: display = themeit % display
	liz=xbmcgui.ListItem(display)
	liz.setArt({'icon': 'DefaultFolder.png', 'thumb': icon, 'fanart': fanart})
	liz.setInfo( type="Video", infoLabels={ "Title": display, "Plot": description} )
	liz.setProperty( "Fanart_Image", fanart )
	if not menu == None: liz.addContextMenuItems(menu, replaceItems=overwrite)
	ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
	return ok
def get_params():
	param=[]
	paramstring=sys.argv[2]
	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')
		if (params[len(params)-1]=='/'):
			params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]
		return param
'''
params=get_params()
url=None
name=None
Bname=''
mode=None
try:     mode=urllib.parse.unquote_plus(params["mode"])
except:  pass
try:     name=urllib.parse.unquote_plus(params["name"])
except:  pass
try:     url=urllib.parse.unquote_plus(params["url"])
except:  pass
'''

Bname = ''

def setView(content, viewType):
	if wiz.getS('auto-view')=='true':
		views = wiz.getS(viewType)
		if views == '50' and SKIN == 'skin.estuary': views = '55'
		if views == '500' and SKIN == 'skin.estuary': views = '50'
		wiz.ebi("Container.SetViewMode(%s)" %  views)



wiz.wizlog('[OmegaWiz] Omega GUI Wizard: Phoenix')
FOCUS_BUTTON_COLOR = uservar.FOCUS_BUTTON_COLOR
DESCOLOR           = uservar.DESCOLOR
DES_T_COLOR        = uservar.DES_T_COLOR
MAIN_BUTTONS_TEXT  = uservar.MAIN_BUTTONS_TEXT
OTHER_BUTTONS_TEXT = uservar.OTHER_BUTTONS_TEXT
LIST_TEXT          = uservar.LIST_TEXT
HIGHLIGHT_LIST     = uservar.HIGHLIGHT_LIST
HIGHLIGHT_LIST2     = uservar.HIGHLIGHT_LIST2
net = net.Net()
#window = pyxbmct.AddonDialogWindow('')
EXIT     = os.path.join(ART , '%s.png' % uservar.EXIT_BUTTON_COLOR)
FBUTTON  = os.path.join(ART , 'button_focus.png') 
LBUTTON  = os.path.join(ART , '%s.png' %  HIGHLIGHT_LIST)
BUTTON   = os.path.join(ART , 'button.png')
LISTBG   = os.path.join(ART , 'listbg.png')
SPLASH   = os.path.join(ART , 'splash.jpg')
SpeedBG  = os.path.join(ART , 'speedtest.jpg')
MAINBG   = os.path.join(ART , 'main.jpg')
NOTXT    = os.path.join(ART , '%s.gif'% uservar.NO_TXT_FILE)


#####################################################
#################  GUI LAYOUT  ######################
######  Dont be an ASSHOLE and claim this  ##########
###########  like you created it!!  #################
#####################################################


class Guiwiz(pyxbmct.AddonDialogWindow):
	
	def __init__(self, title=''):
		super(Guiwiz, self).__init__(title)
		self.window()
		self.main_buttons()
		self.set_navigation()
		self.foreground()
		self.connectEventList(
			[pyxbmct.ACTION_MOVE_DOWN,
			pyxbmct.ACTION_MOVE_UP,
			pyxbmct.ACTION_MOUSE_WHEEL_DOWN,
			pyxbmct.ACTION_MOUSE_WHEEL_UP,
			pyxbmct.ACTION_MOUSE_MOVE],
			self.list_update)
		self.connect(pyxbmct.ACTION_NAV_BACK, self.close)
		self.setFocus(self.BuildsButton)
		self.HIDEALL()
		self.splash.setVisible(True)
	
	def window(self):
		self.setGeometry(1280, 720, 100, 50)# Create Window (width,height,rows,cols)
		self.fan=pyxbmct.Image(MAINBG)
		self.placeControl(self.fan, -10, -6, 125, 62)
		wiz.wizlog('Window Opened')
	
	def foreground(self):
		self.listbg = pyxbmct.Image(LISTBG)
		self.placeControl(self.listbg, 10, 0, 80, 17)

		self.buildbg = pyxbmct.Image(LISTBG)
		self.placeControl(self.buildbg, 10, 16, 80, 35)

		self.buildinfobg = pyxbmct.Image(LISTBG)
		self.placeControl(self.buildinfobg, 88, 0, 23, 50)

		self.listbgA = pyxbmct.Image(LISTBG)
		self.placeControl(self.listbgA, 20, 0, 80, 17)

		self.buildbgA = pyxbmct.Image(LISTBG)
		self.placeControl(self.buildbgA, 20, 16, 80, 35)

		self.maintbg = pyxbmct.Image(LISTBG)
		self.placeControl(self.maintbg, 70, 19, 40, 32)

		self.sysinfobg = pyxbmct.Image(LISTBG)
		self.placeControl(self.sysinfobg, 10, 19, 60, 32)

		self.netinfobg = pyxbmct.Image(LISTBG)
		self.placeControl(self.netinfobg, 10, 0, 60, 20)

		self.speedthumb = pyxbmct.Image(SpeedBG)
		self.placeControl(self.speedthumb, 70, 0, 40, 20)

		self.splash = pyxbmct.Image(SPLASH)
		self.placeControl(self.splash , 10, 1, 100, 48)

		self.bakresbg = pyxbmct.Image(LISTBG)
		self.placeControl(self.bakresbg , 10, 1, 100, 48)

		self.toolsbg = pyxbmct.Image(LISTBG)
		self.placeControl(self.toolsbg , 10, 1, 100, 48)

		self.wizinfogb = pyxbmct.Image(LISTBG)
		self.placeControl(self.wizinfogb, -8, 9, 9, 32)

		self.wiz_title =  pyxbmct.Label('[COLOR %s][B]%s[/B][/COLOR]' % (uservar.WIZTITLE_COLOR ,uservar.WIZTITLE))
		self.placeControl(self.wiz_title, -6, 11, 7, 20)

		self.wiz_ver =  pyxbmct.Label('[COLOR %s]Version: [COLOR %s][B]%s[/B][/COLOR]' % (uservar.VERTITLE_COLOR,uservar.VER_NUMBER_COLOR,VERSION))
		self.placeControl(self.wiz_ver, -6, 31, 7, 10)

		self.no_txt = pyxbmct.Image(NOTXT)
		self.placeControl(self.no_txt, 23, 8, 80, 35)
		
	def main_buttons(self):
		self.BuildsButton= pyxbmct.Button('[COLOR %s][B]Builds[/B][/COLOR]' % MAIN_BUTTONS_TEXT, focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(self.BuildsButton, -2, 1, 13, 8)
		self.connect(self.BuildsButton, lambda: self.BuildList())

		self.MaintButton = pyxbmct.Button('[COLOR %s][B]Maintenance[/B][/COLOR]' % MAIN_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(self.MaintButton, 2, 11, 9, 8)
		self.connect(self.MaintButton, lambda: self.Maint())

		self.BackResButton = pyxbmct.Button('[COLOR %s][B]Backup/Restore[/B][/COLOR]' % MAIN_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(self.BackResButton, 2, 21, 9, 8)
		self.connect(self.BackResButton, lambda: self.BackRes())

		self.ToolsButton = pyxbmct.Button('[COLOR %s][B]Tools[/B][/COLOR]' % MAIN_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(self.ToolsButton, 2, 31, 9, 8)
		self.connect(self.ToolsButton, lambda: self.Tools())

		self.CloseButton = pyxbmct.Button('[COLOR %s][B]Close[/B][/COLOR]' % MAIN_BUTTONS_TEXT,focusTexture=EXIT,noFocusTexture=BUTTON)
		self.placeControl(self.CloseButton, -2, 41, 13, 8)
		self.connect(self.CloseButton, self.close)
	
	def set_navigation(self):
		self.BuildsButton.controlRight(self.MaintButton)
		self.BuildsButton.controlLeft(self.CloseButton)

		self.MaintButton.controlRight(self.BackResButton)
		self.MaintButton.controlLeft(self.BuildsButton)

		self.BackResButton.controlRight(self.ToolsButton)
		self.BackResButton.controlLeft(self.MaintButton)

		self.ToolsButton.controlRight(self.CloseButton)
		self.ToolsButton.controlLeft(self.BackResButton)

		self.CloseButton.controlRight(self.BuildsButton)
		self.CloseButton.controlLeft(self.ToolsButton)
	
	def HIDEALL(self):
		try: Bname.setVisible(False)
		except:pass
		try: buildnamelabel.setVisible(False)
		except:pass
		try: buildversionlabel.setVisible(False)
		except:pass
		try: InstallButtonROM.setVisible(False)
		except:pass
		try: InstallButtonEMU.setVisible(False)
		except:pass
		try: self.no_txt.setVisible(False)
		except:pass
		try: self.splash.setVisible(False)
		except:pass
		try: InstallButton.setVisible(False)
		except:pass
		try: FreshStartButton.setVisible(False)
		except:pass
		try: self.listbg.setVisible(False)
		except:pass
		try: self.no_txt.setVisible(False)
		except:pass
		try: self.speedthumb.setVisible(False)
		except:pass
		try: buildlistmenu.setVisible(False)
		except:pass
		#try: PreviewButton.setVisible(False)
		#except:pass
		#try: ThemeButton.setVisible(False)
		#except:pass
		try: self.buildinfobg.setVisible(False)
		except:pass
		try: self.buildbg.setVisible(False)
		except:pass
		try: buildthumb.setVisible(False)
		except:pass
		try: buildtextbox.setVisible(False)
		except:pass
		try: vertextbox .setVisible(False)
		except:pass
		try: koditextbox.setVisible(False)
		except:pass
		try: desctextbox.setVisible(False)
		except:pass
		try: self.listbgA.setVisible(False)
		except:pass
		try: self.buildbgA.setVisible(False)
		except:pass
		try: self.maintbg.setVisible(False)
		except:pass
		try: total_clean_button.setVisible(False)
		except:pass
		try: total_cache_button.setVisible(False)
		except:pass
		try: total_packages_button.setVisible(False)
		except:pass
		try: total_thumbnails_button.setVisible(False)
		except:pass
		try: TC.setVisible(False)
		except:pass
		try: DC.setVisible(False)
		except:pass
		try: DPK.setVisible(False)
		except:pass
		try: DTH.setVisible(False)
		except:pass
		try: TPK.setVisible(False)
		except:pass
		try: TTH.setVisible(False)
		except:pass
		try: self.sysinfobg.setVisible(False)
		except:pass
		try: speedtest_button.setVisible(False)
		except:pass
		try: sysinfo_title.setVisible(False)
		except:pass
		try: version1.setVisible(False)
		except:pass
		try: store.setVisible(False)
		except:pass
		try: rom_used.setVisible(False)
		except:pass
		try: rom_free.setVisible(False)
		except:pass
		try: rom_total.setVisible(False)
		except:pass
		try: mem.setVisible(False)
		except:pass
		try: ram_used.setVisible(False)
		except:pass
		try: ram_free.setVisible(False)
		except:pass
		try: ram_total.setVisible(False)
		except:pass
		try: kodi.setVisible(False)
		except:pass
		try: total.setVisible(False)
		except:pass
		try: video.setVisible(False)
		except:pass
		try: program.setVisible(False)
		except:pass
		try: music.setVisible(False)
		except:pass
		try: picture.setVisible(False)
		except:pass
		try: repos.setVisible(False)
		except:pass
		try: skins.setVisible(False)
		except:pass
		try: scripts.setVisible(False)
		except:pass
		try: self.netinfobg.setVisible(False)
		except:pass
		try: netinfo_title.setVisible(False)
		except:pass
		try: un_hide_net.setVisible(False)
		except:pass
		try: settings_button1.setVisible(False)
		except:pass
		try: MAC.setVisible(False)
		except:pass
		try: INTER_IP.setVisible(False)
		except:pass
		try: IP.setVisible(False)
		except:pass
		try: ISP.setVisible(False)
		except:pass
		try: CITY.setVisible(False)
		except:pass
		try: STATE.setVisible(False)
		except:pass
		try: COUNTRY.setVisible(False)
		except:pass
		try: self.bakresbg.setVisible(False)
		except:pass
		try: favs.setVisible(False)
		except:pass
		try: backuploc.setVisible(False)
		except:pass
		try: Backup.setVisible(False)
		except:pass
		try: backup_build_button.setVisible(False)
		except:pass
		try: backup_gui_button.setVisible(False)
		except:pass
		try: backup_addondata_button.setVisible(False)
		except:pass
		try: restore_build_button.setVisible(False)
		except:pass
		try: restore_gui_button.setVisible(False)
		except:pass
		try: restore_addondata_button.setVisible(False)
		except:pass
		try: clear_backup_button.setVisible(False)
		except:pass
		try: savefav_button.setVisible(False)
		except:pass
		try: restorefav_button.setVisible(False)
		except:pass
		try: clearfav_button.setVisible(False)
		except:pass
		try: backupaddonpack_button.setVisible(False)
		except:pass
		try: restore_title.setVisible(False)
		except:pass
		try: delete_title.setVisible(False)
		except:pass
		try: set_title.setVisible(False)
		except:pass
		try: settings_button.setVisible(False)
		except:pass
		try: view_error_button.setVisible(False)
		except:pass
		try: full_log_button.setVisible(False)
		except:pass
		try: upload_log_button.setVisible(False)
		except:pass
		try: removeaddons_button.setVisible(False)
		except:pass
		try: removeaddondata_all_button.setVisible(False)
		except:pass
		try: removeaddondata_u_button.setVisible(False)
		except:pass
		try: removeaddondata_e_button.setVisible(False)
		except:pass
		try: checksources_button.setVisible(False)
		except:pass
		try: checkrepos_button.setVisible(False)
		except:pass
		try: forceupdate_button.setVisible(False)
		except:pass
		try: fixaddonupdate_button.setVisible(False)
		except:pass
		try: Addon.setVisible(False)
		except:pass
		try: scan.setVisible(False)
		except:pass
		try: fix.setVisible(False)
		except:pass
		try: delet.setVisible(False)
		except:pass
		try: delet1.setVisible(False)
		except:pass
		try: Log_title.setVisible(False)
		except:pass
		try: self.toolsbg.setVisible(False)
		except:pass
		try: Log_errors.setVisible(False)
		except:pass
		try: WhiteList.setVisible(False)
		except:pass
		try: whitelist_edit_button.setVisible(False)
		except:pass
		try: whitelist_view_button.setVisible(False)
		except:pass
		try: whitelist_clear_button.setVisible(False)
		except:pass
		try: whitelist_import_button.setVisible(False)
		except:pass
		try: whitelist_export_button.setVisible(False)
		except:pass
		try: Advan.setVisible(False)
		except:pass
		try: autoadvanced_buttonQ.setVisible(False)
		except:pass
		try: autoadvanced_button.setVisible(False)
		except:pass
		try: currentsettings_button.setVisible(False)
		except:pass
		try: removeadvanced_button.setVisible(False)
		except:pass
		try: self.buildversionlabel.setVisible(False)
		except:pass
		try: buildthemelabel.setVisible(False)
		except:pass
		try: skinname.setVisible(False)
		except:pass
		try: errorinstall.setVisible(False)
		except:pass
		try: lastupdatchk.setVisible(False)
		except:pass
	
	def runspeedtest(self):
		from resources.libs import speedtest
		speed = speedtest.speedtest()
		self.speedthumb.setImage(speed[0])

	def list_update(self):
		global Bname
		global url
		global name
		global plugin
		global build_data_list
		try:
			if self.getFocus() == buildlistmenu:
				pos = buildlistmenu.getSelectedPosition()
				if pos < len(build_data_list):
					entry = build_data_list[pos]
					buildpic = entry['icon'] if entry['icon'] else ICON
					Bversion = entry['version']
					kodivers = entry['kodi']
					description = entry['description']
					n = entry['name']
					buildthumb.setImage(buildpic)
					desctextbox.setText('[COLOR %s]%s[/COLOR]' % (DESCOLOR, description))
					if entry.get('is_header'):
						buildtextbox.setLabel('')
						vertextbox.setLabel('')
						koditextbox.setLabel('')
						return
					url = entry['url']
					name = n
					buildtextbox.setLabel('[COLOR %s]Build Selected: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, name))
					vertextbox.setLabel('[COLOR %s]Version: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, Bversion))
					koditextbox.setLabel('[COLOR %s]Kodi Version: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, kodivers))
					Bname = wiz.stripcolortags(name) or name
		except:
			pass


	def BuildList(self):
		global InstallButton
		global FreshStartButton
		global buildlist
		global buildlistmenu
		global buildthumb
		global buildtextbox
		global vertextbox 
		global koditextbox
		global desctextbox
		global no_txt
		global buildnamelabel
		global buildversionlabel
		global buildthemelabel
		global skinname
		global errorinstall
		global lastupdatchk
		global Bname
		global build_data_list
		#global PreviewButton
		#global ThemeButton
		
		self.HIDEALL()
		if not BUILDFILE == 'https://' and not BUILDFILE == '':
			self.listbg.setVisible(True)
			self.buildbg.setVisible(True)
			self.buildinfobg.setVisible(True)
		
		
			InstallButton = pyxbmct.Button('[COLOR %s][B]Install[/B][/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
			self.placeControl(InstallButton,28 , 20, 8, 8)
			self.connect(InstallButton, lambda: buildWizard(Bname,'normal'))
		
			FreshStartButton = pyxbmct.Button('[COLOR %s][B]Fresh Install[/B][/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
			self.placeControl(FreshStartButton,36 , 20, 8, 8)
			self.connect(FreshStartButton,lambda: buildWizard(Bname,'fresh'))
		
			#ThemeButton = pyxbmct.Button('[COLOR %s][B]Install Themes[/B][/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
			#self.placeControl(ThemeButton,44 , 20, 8, 8)
			#self.connect(ThemeButton,lambda: buildWizard(Bname,'theme'))
		
			buildthumb = pyxbmct.Image(ICON)
			self.placeControl(buildthumb, 21, 30, 45, 19)
		
			buildlistmenu = pyxbmct.List(buttonFocusTexture=os.path.join(ART , '%s.png' %  HIGHLIGHT_LIST2))
			self.placeControl(buildlistmenu, 14, 1, 79, 15)
		
			buildtextbox = pyxbmct.Label('',textColor='0xFFFFFFFF')
			self.placeControl(buildtextbox, 13, 20, 10, 25)
		
			vertextbox   = pyxbmct.Label('',textColor='0xFFFFFFFF')
			self.placeControl(vertextbox, 60, 20, 10, 15)
		
			koditextbox  = pyxbmct.Label('',textColor='0xFFFFFFFF')
			self.placeControl(koditextbox, 65, 20, 10, 15)
		
			desctextbox = pyxbmct.TextBox()
			self.placeControl(desctextbox, 70, 20, 17, 30)
			desctextbox.autoScroll(1100, 1100, 1100)
		
			buildname1 = ADDON.getSetting('buildname')
			buildversion1 = ADDON.getSetting('buildversion')
			defaultskinname1 = ADDON.getSetting('defaultskinname')
			buildtheme1 = ADDON.getSetting('buildtheme')
			errors1 = ADDON.getSetting('errors')
			lastbuildcheck1 = ADDON.getSetting('lastbuildcheck')
		
			if buildname1 == '' : buildname = None 
			else:buildname = ADDON.getSetting('buildname')
		
			if buildversion1 == '' : buildversion = None 
			else:buildversion = ADDON.getSetting('buildversion')
		
			if defaultskinname1 == '' : defaultskinname = None 
			else:defaultskinname = ADDON.getSetting('defaultskinname')
		
			if buildtheme1 == '' : buildtheme = None 
			else:buildtheme = ADDON.getSetting('buildtheme')
		
			if errors1 == '' : errors = None 
			else:errors = ADDON.getSetting('errors')
		
			if lastbuildcheck1 == '' : lastbuildcheck = None 
			else:lastbuildcheck = ADDON.getSetting('lastbuildcheck')
		
			buildnamelabel  = pyxbmct.Label('[COLOR %s]Current Build Name: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR,DESCOLOR,buildname))
			self.placeControl(buildnamelabel, 90, 2, 8, 25)
		
			buildversionlabel  = pyxbmct.Label('[COLOR %s]Current Build Version: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR,DESCOLOR,buildversion))
			self.placeControl(buildversionlabel, 95, 2, 8, 20)
		
			skinname  = pyxbmct.Label('[COLOR %s]Build Skin Name: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR,DESCOLOR,defaultskinname))
			self.placeControl(skinname, 100, 2, 11, 20)
		
			buildthemelabel  = pyxbmct.Label('[COLOR %s]Build Theme: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR,DESCOLOR,buildtheme))
			self.placeControl(buildthemelabel, 90, 28, 8, 21)
		
			errorinstall  = pyxbmct.Label('[COLOR %s]Errors During Install: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR,DESCOLOR,errors))
			self.placeControl(errorinstall, 95, 28, 8, 20)
		
			lastupdatchk  = pyxbmct.Label('[COLOR %s]Last Update Check: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR,DESCOLOR,lastbuildcheck))
			self.placeControl(lastupdatchk, 100, 28, 8, 20)
		
			buildlistmenu.reset()
			buildlistmenu.setVisible(True)
			buildthumb.setVisible(True)

			InstallButton.setVisible(True)
			FreshStartButton.setVisible(True)
			buildtextbox.setVisible(True)
			vertextbox.setVisible(True)
			koditextbox.setVisible(True)
			desctextbox.setVisible(True)
		
			buildnamelabel.setVisible(True)
			buildversionlabel.setVisible(True)
			buildthemelabel.setVisible(True)
			skinname.setVisible(True)
			errorinstall.setVisible(True)
			lastupdatchk.setVisible(True)
		
			buildthumb.setImage(ICON)
			build_data_list = []
			try:
				link = net.http_GET(BUILDFILE).content.replace('\n','').replace('\r','')
			except http.client.InvalidURL:
				link = ''
			for part in re.split(r'(?=name=")', link):
				name_m = re.compile('name="(.+?)"').findall(part)
				if not name_m: continue
				n      = name_m[0]
				url_m  = re.compile('url="(.*?)"').findall(part)
				icon_m = re.compile('icon="(.*?)"').findall(part)
				ver_m  = re.compile('version="(.*?)"').findall(part)
				kodi_m = re.compile('kodi="(.*?)"').findall(part)
				desc_m = re.compile('description="(.*?)"').findall(part)
				entry_url = url_m[0] if url_m else ''
				is_header = not entry_url or entry_url in ('http://', 'https://')
				build_data_list.append({
					'name':        n,
					'url':         entry_url,
					'icon':        icon_m[0] if icon_m else ICON,
					'version':     ver_m[0]  if ver_m  else '',
					'kodi':        kodi_m[0] if kodi_m else '',
					'description': desc_m[0] if desc_m else '',
					'is_header':   is_header,
				})
				if is_header:
					buildlistmenu.addItem(n)
				else:
					buildlistmenu.addItem('[COLOR %s]%s[/COLOR]' % (LIST_TEXT, n))
	
			self.BuildsButton.controlUp(buildlistmenu)
			self.BuildsButton.controlDown(buildlistmenu)
		
			buildlistmenu.controlRight(InstallButton)  # PreviewButton when fixed
			buildlistmenu.controlUp(self.BuildsButton)
		
			#PreviewButton.controlDown(InstallButton)
			#PreviewButton.controlUp(self.BuildsButton)
			#PreviewButton.controlLeft(buildlistmenu)
		
			InstallButton.controlDown(FreshStartButton)
			InstallButton.controlUp(self.BuildsButton)  # PreviewButton when fixed
			InstallButton.controlLeft(buildlistmenu)
		
			#FreshStartButton.controlDown(ThemeButton)
			FreshStartButton.controlUp(InstallButton)
			FreshStartButton.controlLeft(buildlistmenu)
			#ThemeButton.controlUp(FreshStartButton)
			#ThemeButton.controlLeft(buildlistmenu)
	
		else:
			self.no_txt.setVisible(True)
			wiz.wizlog('No Build txt')


	def Un_Hide_Net(self):
		mac,inter_ip,ip,city,state,country,isp = wiz.net_info()
		MAC.setLabel('[COLOR %s]Mac:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, mac))
		INTER_IP.setLabel('[COLOR %s]Internal IP: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,inter_ip))
		IP.setLabel('[COLOR %s]External IP:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,ip))
		CITY.setLabel('[COLOR %s]City:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,city))
		STATE.setLabel('[COLOR %s]State:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,state))
		COUNTRY.setLabel('[COLOR %s]Country:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,country))
		ISP.setLabel('[COLOR %s]ISP:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,isp))

	def Maint(self):
		self.HIDEALL()
		global total_clean_button
		global total_cache_button
		global total_packages_button
		global total_thumbnails_button
		global TC
		global DC
		global DPK
		global DTH
		global TPK
		global TTH
		global speedtest_button
		global sysinfo_title
		global version1
		global store
		global rom_used
		global rom_free
		global rom_total
		global mem
		global ram_used
		global ram_free
		global ram_total
		global kodi
		global total
		global video
		global program
		global music
		global picture
		global repos
		global skins
		global scripts
	
		self.sysinfobg.setVisible(True)
		self.maintbg.setVisible(True)
		self.speedthumb.setVisible(True)
		self.netinfobg.setVisible(True)
		sizepack   = wiz.getSize(PACKAGES)
		totalpack   = wiz.getTotal(PACKAGES)
		sizethumb  = wiz.getSize(THUMBS)
		totalthumb   = wiz.getTotal(THUMBS)
		sizecache  = wiz.getCacheSize()
		totalsize  = sizepack+sizethumb+sizecache
		picture, music, video, programs, repos, scripts, skins, codename, version, name,storage_free ,storage_used, storage_total, ram_free, ram_used, ram_total = wiz.SYSINFO()
	
		##sysinfo
	
		sysinfo_title =  pyxbmct.Label('[COLOR %s][B]SYSTEM INFO[/B][/COLOR]' % DES_T_COLOR)
		self.placeControl(sysinfo_title, 12, 31, 10, 15)
		version1 =  pyxbmct.Label('[COLOR %s]Version:[/COLOR] [COLOR %s]%s[/COLOR] - [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, codename, DESCOLOR, version))
		self.placeControl(version1, 18, 37, 10, 15)
		store = pyxbmct.Label('[B][COLOR %s]Storage[/COLOR][/B]'% DESCOLOR)
		self.placeControl(store, 23, 39, 10, 10)
		rom_used=pyxbmct.Label('[COLOR %s]Used:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, storage_free))
		self.placeControl(rom_used, 28, 39, 10, 10)
		rom_free=pyxbmct.Label('[COLOR %s]Free:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, storage_used))
		self.placeControl(rom_free, 32, 39, 10, 10)
		rom_total=pyxbmct.Label('[COLOR %s]Total:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, storage_total))
		self.placeControl(rom_total, 37, 39, 10, 10)
		mem = pyxbmct.Label('[B][COLOR %s]Memory[/COLOR][/B]' % DESCOLOR)
		self.placeControl(mem, 43, 39, 10, 10)
		### Hello, how are you
		ram_used=pyxbmct.Label('[COLOR %s]Used:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, ram_used))
		self.placeControl(ram_used, 48, 39, 10, 10)
		ram_free=pyxbmct.Label('[COLOR %s]Free:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, ram_free))
		self.placeControl(ram_free, 53, 39, 10, 10)
		ram_total=pyxbmct.Label('[COLOR %s]Total:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, ram_total))
		self.placeControl(ram_total, 58, 39, 10, 10)
	
		##addon info
	
		kodi = pyxbmct.Label('[COLOR %s]Name:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, name))
		self.placeControl(kodi, 17, 22, 10, 15)
		totalcount = len(picture) + len(music) + len(video) + len(programs) + len(scripts) + len(skins) + len(repos) 
		total = pyxbmct.Label('[COLOR %s]Addons Total: [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, totalcount))
		self.placeControl(total, 22, 22, 10, 10)
		video=pyxbmct.Label('[COLOR %s]Video Addons:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, str(len(video))))
		self.placeControl(video, 27, 22, 10, 10)
		program=pyxbmct.Label('[COLOR %s]Program Addons:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, str(len(programs))))
		self.placeControl(program, 33, 22, 10, 10)
		music=pyxbmct.Label('[COLOR %s]Music Addons:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, str(len(music))))
		self.placeControl(music, 37, 22, 10, 10)
		picture=pyxbmct.Label('[COLOR %s]Picture Addons:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, str(len(picture))))
		self.placeControl(picture, 42, 22, 10, 10)
		repos=pyxbmct.Label('[COLOR %s]Repositories:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, str(len(repos))))
		self.placeControl(repos, 47, 22, 10, 10)
		skins=pyxbmct.Label('[COLOR %s]Skins: [/COLOR][COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, str(len(skins))))
		self.placeControl(skins, 52, 22, 10, 10)
		scripts=pyxbmct.Label('[COLOR %s]Scripts/Modules:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR, str(len(scripts))))
		self.placeControl(scripts, 57, 22, 10, 10)
	
		global MAC
		global INTER_IP
		global IP
		global CITY
		global STATE
		global COUNTRY
		global ISP
		global netinfo_title
		global un_hide_net
		global settings_button1
	
		###NET INFO
	
		netinfo_title =  pyxbmct.Label('[COLOR %s][B]NETWORK INFO[/B][/COLOR]'% DES_T_COLOR)
		self.placeControl(netinfo_title, 12, 7, 10, 20)
		MAC = pyxbmct.Label('[COLOR %s]Mac:[/COLOR] [COLOR %s]Hidden[/COLOR]' % (DES_T_COLOR, DESCOLOR))
		self.placeControl(MAC, 18 , 1 ,  10, 18)
		INTER_IP = pyxbmct.Label('[COLOR %s]Internal IP: [COLOR %s]Hidden[/COLOR]' % (DES_T_COLOR, DESCOLOR))
		self.placeControl(INTER_IP, 23 , 1 ,  10, 18)
		IP = pyxbmct.Label('[COLOR %s]External IP:[/COLOR] [COLOR %s]Hidden[/COLOR]' % (DES_T_COLOR, DESCOLOR))
		self.placeControl(IP, 28 , 1 ,  10, 18)
		CITY = pyxbmct.Label('[COLOR %s]City:[/COLOR] [COLOR %s]Hidden[/COLOR]' % (DES_T_COLOR, DESCOLOR))
		self.placeControl(CITY, 33 , 1 ,  10, 18)
		STATE = pyxbmct.Label('[COLOR %s]State:[/COLOR] [COLOR %s]Hidden[/COLOR]' % (DES_T_COLOR, DESCOLOR))
		self.placeControl(STATE, 38 , 1 ,  10, 18)
		COUNTRY = pyxbmct.Label('[COLOR %s]Country:[/COLOR] [COLOR %s]Hidden[/COLOR]' % (DES_T_COLOR, DESCOLOR))
		self.placeControl(COUNTRY, 43 , 1 ,  10, 18)
		ISP = pyxbmct.Label('[COLOR %s]ISP:[/COLOR] [COLOR %s]Hidden[/COLOR]' % (DES_T_COLOR, DESCOLOR))
		self.placeControl(ISP, 48 , 1 ,  10, 18)
	
		#maint lables#
		TC = pyxbmct.Label('[COLOR %s]Size:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,wiz.convertSize(totalsize)))
		self.placeControl(TC, 80 , 21 ,  10, 9)
		DC = pyxbmct.Label('[COLOR %s]Size:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,wiz.convertSize(sizecache)))
		self.placeControl(DC, 96 , 21 ,  10, 9)
		DPK = pyxbmct.Label('[COLOR %s]Size:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,wiz.convertSize(sizepack)))
		self.placeControl(DPK, 96 , 31 ,  10, 9)
		TPK = pyxbmct.Label('[COLOR %s]Files:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,totalpack))
		self.placeControl(TPK, 101 , 31 ,  10, 9)
		DTH = pyxbmct.Label('[COLOR %s]Size:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,wiz.convertSize(sizethumb)))
		self.placeControl(DTH, 96 , 41 ,  10, 9)
		TTH = pyxbmct.Label('[COLOR %s]Files:[/COLOR] [COLOR %s]%s[/COLOR]' % (DES_T_COLOR, DESCOLOR,totalthumb))
		self.placeControl(TTH, 101 , 41 ,  10, 9)
	
		#buttons#
		total_clean_button = pyxbmct.Button('[COLOR %s]Total Clean Up[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(total_clean_button, 72 , 21 ,  9, 8)
		self.connect(total_clean_button,lambda: totalClean())
		### I'm good, u?
		total_cache_button = pyxbmct.Button('[COLOR %s]Delete Cache[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(total_cache_button, 87 , 21 ,  9, 9)
		self.connect(total_cache_button,lambda: clearCache())
	
		total_packages_button = pyxbmct.Button('[COLOR %s]Delete Packages[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(total_packages_button, 87 , 31 ,  9, 9)
		self.connect(total_packages_button,lambda: clearPackages())
	
		total_thumbnails_button = pyxbmct.Button('[COLOR %s]Delete Thumbnails[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(total_thumbnails_button, 87 , 41 ,  9, 9)
		self.connect(total_thumbnails_button, lambda: clearThumb(type=None))
	
		speedtest_button = pyxbmct.Button('[COLOR %s]Speed Test[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(speedtest_button, 58 , 1 ,  9, 8)
		self.connect(speedtest_button, lambda: self.runspeedtest())
	
		un_hide_net = pyxbmct.Button('[COLOR %s]Show Net Info[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(un_hide_net, 58, 10, 9, 8)
		self.connect(un_hide_net, lambda: self.Un_Hide_Net())
	
		settings_button1 = pyxbmct.Button('[COLOR %s]Settings[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(settings_button1, 72 , 41 ,  9, 8)
		self.connect(settings_button1, lambda: wiz.openS('Maintenance'))

		#self.HIDEALL()
		self.splash.setVisible(False)
		total_clean_button.setVisible(True)
		total_cache_button.setVisible(True)
		total_packages_button.setVisible(True)
		total_thumbnails_button.setVisible(True)
		TC.setVisible(True)
		DC.setVisible(True)
		DPK.setVisible(True)
		DTH.setVisible(True)
		TPK.setVisible(True)
		TTH.setVisible(True)
		speedtest_button.setVisible(True)
		sysinfo_title.setVisible(True)
		version1.setVisible(True)
		store.setVisible(True)
		rom_used.setVisible(True)
		rom_free.setVisible(True)
		rom_total.setVisible(True)
		mem.setVisible(True)
		ram_used.setVisible(True)
		ram_free.setVisible(True)
		ram_total.setVisible(True)
		kodi.setVisible(True)
		total.setVisible(True)
		video.setVisible(True)
		program.setVisible(True)
		music.setVisible(True)
		picture.setVisible(True)
		repos.setVisible(True)
		skins.setVisible(True)
		scripts.setVisible(True)
		netinfo_title.setVisible(True)
		MAC.setVisible(True)
		un_hide_net.setVisible(True)
		INTER_IP.setVisible(True)
		IP.setVisible(True)
		ISP.setVisible(True)
		CITY.setVisible(True)
		STATE.setVisible(True)
		COUNTRY.setVisible(True)
		settings_button1.setVisible(True)
	
		self.MaintButton.controlDown(speedtest_button)
	
		speedtest_button.controlUp(self.MaintButton)
		speedtest_button.controlDown(total_clean_button)
		speedtest_button.controlRight(un_hide_net)
	
		un_hide_net.controlUp(self.MaintButton)
		un_hide_net.controlDown(total_clean_button)
		un_hide_net.controlRight(total_clean_button)
		un_hide_net.controlLeft(speedtest_button)
	
		total_clean_button.controlUp(self.MaintButton)
		total_clean_button.controlDown(total_cache_button)
		total_clean_button.controlRight(settings_button1)
		total_clean_button.controlLeft(un_hide_net)
	
		total_cache_button.controlUp(total_clean_button)
		total_cache_button.controlRight(total_packages_button)
		total_cache_button.controlLeft(un_hide_net)
	
		total_packages_button.controlUp(settings_button1)
		total_packages_button.controlRight(total_thumbnails_button)
		total_packages_button.controlLeft(total_cache_button)
	
		total_thumbnails_button.controlUp(settings_button1)
		total_thumbnails_button.controlLeft(total_packages_button)
	
		settings_button1.controlUp(self.MaintButton)
		settings_button1.controlDown(total_thumbnails_button)
		settings_button1.controlLeft(total_clean_button)

	def BackRes(self):
		self.HIDEALL()
		global favs
		global backuploc
		global Backup
		global backup_build_button
		global backup_gui_button
		global backup_addondata_button
		global restore_build_button
		global restore_gui_button
		global restore_addondata_button
		global clear_backup_button
		global savefav_button
		global restorefav_button
		global clearfav_button
		global backupaddonpack_button
		global restore_title
		global delete_title
		global set_title
		global settings_button
	
		self.bakresbg.setVisible(True)
	
		last = str(FAVSsave) if not FAVSsave == '' else 'Favourites hasnt been saved yet.'
		#loc info#
	
		favs = pyxbmct.Label('[B][COLOR %s]Last Save:[/COLOR] [COLOR %s]%s[/COLOR][/B]' % (DES_T_COLOR, DESCOLOR,str(last)))
		self.placeControl(favs, 14, 3, 10, 30)
	
		backuploc = pyxbmct.Label('[B][COLOR %s]Back-Up Location: [COLOR %s]%s[/COLOR][/B]' % (DES_T_COLOR, DESCOLOR, MYBUILDS))
		self.placeControl(backuploc, 22, 3, 10, 30)
	
		#backup#
		Backup = pyxbmct.Label('[B][COLOR %s]Backup Tools:[/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(Backup, 32, 3, 10, 10)
	
		backup_build_button = pyxbmct.Button('[COLOR %s] Build[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(backup_build_button, 42, 3, 10, 10)
		self.connect(backup_build_button,lambda: wiz.backUpOptions('build'))
	
		backup_gui_button = pyxbmct.Button('[COLOR %s] GUI[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(backup_gui_button, 52, 3, 10, 10)
		self.connect(backup_gui_button,lambda: wiz.backUpOptions('guifix'))
		
		backupaddonpack_button = pyxbmct.Button('[COLOR %s] Addon Pack[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(backupaddonpack_button, 62, 3, 10, 10)
		self.connect(backupaddonpack_button,lambda: wiz.backUpOptions('addon pack'))
		# I'm ok, thanks for asking
		backup_addondata_button = pyxbmct.Button('[COLOR %s] Addon Data[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(backup_addondata_button, 72, 3, 10, 10)
		self.connect(backup_addondata_button,lambda: wiz.backUpOptions('addondata'))
	
		savefav_button = pyxbmct.Button('[COLOR %s] Favourites[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(savefav_button, 82, 3, 10, 10)
		self.connect(savefav_button,lambda: wiz.BACKUPFAV())
	
		#restore#
		restore_title = pyxbmct.Label('[B][COLOR %s]Restore Tools:[/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(restore_title, 32, 20, 10, 10)
	
		restore_build_button = pyxbmct.Button('[COLOR %s]Build/Pack[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(restore_build_button, 42, 20, 10, 10)
		self.connect(restore_build_button,lambda: restoreit('build'))
	
		restore_gui_button = pyxbmct.Button('[COLOR %s]GUI[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(restore_gui_button, 52, 20, 10, 10)
		self.connect(restore_gui_button,lambda: restoreit('gui'))
		### Nope not here
		restore_addondata_button = pyxbmct.Button('[COLOR %s]Addon Data[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(restore_addondata_button, 62, 20, 10, 10)
		self.connect(restore_addondata_button,lambda: restoreit('addondata'))
	
		restorefav_button = pyxbmct.Button('[COLOR %s]Favourites[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(restorefav_button, 72, 20, 10, 10)
		self.connect(restorefav_button,lambda: wiz.RESTOREFAV())
	
		#clear backups#
		delete_title = pyxbmct.Label('[B][COLOR FFFF0000]Delete Tools:[/COLOR][/B]')
		self.placeControl(delete_title, 54, 37, 10, 10)
	
		clearfav_button = pyxbmct.Button('[COLOR %s]Clear Favourites[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(clearfav_button, 64, 37, 10, 10)
		self.connect(clearfav_button,lambda: wiz.DELFAV())
	
		clear_backup_button = pyxbmct.Button('[COLOR %s]Clear Back-ups[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(clear_backup_button, 74, 37, 10, 10)
		self.connect(clear_backup_button,lambda: wiz.cleanupBackup())
	
		#settings
		set_title = pyxbmct.Label('[B][COLOR %s]Settings:[/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(set_title, 32, 37, 10, 10)
	
		settings_button = pyxbmct.Button('[COLOR %s]Settings[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(settings_button, 42, 37, 10, 10)
		self.connect(settings_button, lambda: wiz.openS('Maintenance'))
	
		favs.setVisible(True)
		backuploc.setVisible(True)
		Backup.setVisible(True)
		backup_build_button.setVisible(True)
		backup_gui_button.setVisible(True)
		backup_addondata_button.setVisible(True)
		restore_build_button.setVisible(True)
		restore_gui_button.setVisible(True)
		restore_addondata_button.setVisible(True)
		clear_backup_button.setVisible(True)
		savefav_button.setVisible(True)
		restorefav_button.setVisible(True)
		clearfav_button.setVisible(True)
		backupaddonpack_button.setVisible(True)
		restore_title.setVisible(True)
		delete_title.setVisible(True)
		set_title.setVisible(True)
		settings_button.setVisible(True)
	
		self.BackResButton.controlDown(backup_build_button)

		backup_build_button.controlUp(self.BackResButton)
		backup_build_button.controlDown(backup_gui_button)
		backup_build_button.controlRight(restore_build_button)

		backup_gui_button.controlUp(backup_build_button)
		backup_gui_button.controlDown(backupaddonpack_button)
		backup_gui_button.controlRight(restore_gui_button)
	
		backupaddonpack_button.controlUp(backup_gui_button)
		backupaddonpack_button.controlDown(backup_addondata_button)
		backupaddonpack_button.controlRight(restore_addondata_button)
	
		backup_addondata_button.controlUp(backupaddonpack_button)
		backup_addondata_button.controlDown(savefav_button)
		backup_addondata_button.controlRight(restorefav_button)
		
		savefav_button.controlUp(backup_addondata_button)
		savefav_button.controlRight(restorefav_button)

		restore_build_button.controlUp(self.BackResButton)
		restore_build_button.controlDown(restore_gui_button)
		restore_build_button.controlRight(settings_button)
		restore_build_button.controlLeft(backup_build_button)

		restore_gui_button.controlUp(restore_build_button)
		restore_gui_button.controlDown(restore_addondata_button)
		restore_gui_button.controlRight(settings_button)
		restore_gui_button.controlLeft(backup_gui_button)

		restore_addondata_button.controlUp(restore_gui_button)
		restore_addondata_button.controlDown(restorefav_button)
		restore_addondata_button.controlRight(clearfav_button)
		restore_addondata_button.controlLeft(backupaddonpack_button)

		restorefav_button.controlUp(restore_addondata_button)
		restorefav_button.controlRight(clear_backup_button)
		restorefav_button.controlLeft(backup_addondata_button)

		settings_button.controlUp(self.BackResButton)
		settings_button.controlDown(clearfav_button)
		settings_button.controlLeft(restore_build_button)

		clearfav_button.controlUp(settings_button)
		clearfav_button.controlDown(clear_backup_button)
		clearfav_button.controlLeft(restore_addondata_button)

		clear_backup_button.controlUp(clearfav_button)
		clear_backup_button.controlLeft(restorefav_button)

	def Tools(self):
		self.HIDEALL()
	
		global view_error_button
		global full_log_button
		global upload_log_button
		global Log_title
		global Log_errors
	
		self.toolsbg.setVisible(True)
	
		Log_title = pyxbmct.Label('[B][COLOR %s]Logging Tools[/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(Log_title, 15, 4, 10, 10)
	
		Log_errors = pyxbmct.Label('[COLOR %s][B]Errors in Log:[/B][/COLOR] %s' % (OTHER_BUTTONS_TEXT, log_tools()))
		self.placeControl(Log_errors, 22, 4, 10, 15)
		## uhhh not here
		view_error_button = pyxbmct.Button('[COLOR %s]View Errors[/COLOR]'% OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(view_error_button, 31, 4, 9, 9)
		self.connect(view_error_button, lambda: errorChecking(log=None, count=None, last=None))
	
		full_log_button = pyxbmct.Button('[COLOR %s]View Full Log[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(full_log_button, 40, 4, 9, 9)
		self.connect(full_log_button,lambda : LogViewer())
	
		upload_log_button = pyxbmct.Button('[COLOR %s]Upload Full Log[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(upload_log_button, 49, 4, 9, 9)
		self.connect(upload_log_button,lambda : uploadLog.Main())
	
		#Addon#
	
		global removeaddons_button
		global removeaddondata_u_button
		global removeaddondata_e_button
		global checksources_button
		global checkrepos_button
		global forceupdate_button
		global fixaddonupdate_button
		global removeaddondata_all_button
		global scan
		global fix
		global delet
		global delet1
		global Addon
	
		Addon = pyxbmct.Label('[B][COLOR %s]Addon Tools[/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(Addon, 69, 21, 9, 9)
		#buttons#
		scan = pyxbmct.Label('[B][COLOR %s]Scan For:[/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(scan, 75, 4, 9, 10)
	
		checksources_button = pyxbmct.Button('[COLOR %s]Broken Sources[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(checksources_button, 82, 3, 9, 10)
		self.connect(checksources_button,lambda: wiz.checkSources())
	
		checkrepos_button = pyxbmct.Button('[COLOR %s]Broken Repositories[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(checkrepos_button, 92, 3, 9, 10)
		self.connect(checkrepos_button,lambda: wiz.checkRepos())
	
		fix = pyxbmct.Label('[B][COLOR %s]Force / Fix:[/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(fix, 75, 16, 9, 10)
	
		forceupdate_button = pyxbmct.Button('[COLOR %s]Update Addons[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(forceupdate_button, 82, 15, 9, 9)
		self.connect(forceupdate_button,lambda: wiz.forceUpdate())
	
		fixaddonupdate_button = pyxbmct.Button('[COLOR %s]Enable Disabled Addons[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(fixaddonupdate_button, 92, 15, 9, 9)
		from resources.libs import addons_enable
		self.connect(fixaddonupdate_button,lambda: addons_enable.enable_addons())
		### I see you looking
		delet = pyxbmct.Label('[B][COLOR %s]Delete: [/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(delet, 75, 28, 9, 10)
	
		removeaddons_button = pyxbmct.Button('[COLOR %s]Delete Selected Addons[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(removeaddons_button, 82, 26, 9, 9)
		self.connect(removeaddons_button,lambda: removeAddonMenu())
	
		removeaddondata_all_button = pyxbmct.Button('[COLOR %s]All Addon Data[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(removeaddondata_all_button, 92, 26, 9, 9)
		self.connect(removeaddondata_all_button,lambda: removeAddonData('all'))
	
		delet1 = pyxbmct.Label('[B][COLOR %s]Delete: [/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(delet1, 75, 39, 9, 10)
	
		removeaddondata_u_button = pyxbmct.Button('[COLOR %s]Uninstalled Folders[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(removeaddondata_u_button, 82, 37, 9, 9)
		self.connect(removeaddondata_u_button,lambda: removeAddonData('uninstalled'))
	
		removeaddondata_e_button = pyxbmct.Button('[COLOR %s]Empty Folders[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(removeaddondata_e_button, 92, 37, 9, 9)
		self.connect(removeaddondata_e_button,lambda: removeAddonData('empty'))
	
		####White List###
		global WhiteList
		global whitelist_edit_button
		global whitelist_view_button
		global whitelist_clear_button
		global whitelist_import_button
		global whitelist_export_button
	
	
		WhiteList = pyxbmct.Label('[B][COLOR %s]White List Tools: [/COLOR][/B]' % DES_T_COLOR)
		self.placeControl(WhiteList, 15, 36, 9, 9)
	
		whitelist_edit_button = pyxbmct.Button('[COLOR %s]WhiteList: Edit[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(whitelist_edit_button, 22, 36, 9, 9)
		self.connect(whitelist_edit_button,lambda: wiz.whiteList('edit'))
	
		whitelist_view_button = pyxbmct.Button('[COLOR %s]WhiteList: View[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(whitelist_view_button, 31, 36, 9, 9)
		self.connect(whitelist_view_button,lambda: wiz.whiteList('view'))
	
		whitelist_clear_button = pyxbmct.Button('[COLOR %s]WhiteList: Clear[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(whitelist_clear_button, 40, 36, 9, 9)
		self.connect(whitelist_clear_button,lambda: wiz.whiteList('clear'))
		### It's not here
		whitelist_import_button = pyxbmct.Button('[COLOR %s]WhiteList: Import[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(whitelist_import_button, 49, 36, 9, 9)
		self.connect(whitelist_import_button,lambda: wiz.whiteList('import'))
	
		whitelist_export_button = pyxbmct.Button('[COLOR %s]WhiteList: Export[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(whitelist_export_button, 58, 36, 9, 9)
		self.connect(whitelist_export_button,lambda: wiz.whiteList('export'))
	
		########  Advanced ########
		global Advan
		global autoadvanced_buttonQ
		global autoadvanced_button
		global currentsettings_button
		global removeadvanced_button
	
		Advan = pyxbmct.Label('[B][COLOR %s]Advanced Settings Tools[/COLOR][/B]'% DES_T_COLOR)
		self.placeControl(Advan, 15, 20, 9, 13)
		#buttons#
		autoadvanced_buttonQ = pyxbmct.Button('[COLOR %s]Quick Config[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(autoadvanced_buttonQ, 22, 21, 9, 9)
		self.connect(autoadvanced_buttonQ,lambda: notify.simple_advanced())
	
		autoadvanced_button = pyxbmct.Button('[COLOR %s]Full Config[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(autoadvanced_button, 31, 21, 9, 9)
		self.connect(autoadvanced_button,lambda: notify.autoConfig())
		##Wait it's here!!
		currentsettings_button = pyxbmct.Button('[COLOR %s]Current Settings[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(currentsettings_button, 40, 21, 9, 9)
		self.connect(currentsettings_button,lambda: viewAdvanced())
	
		removeadvanced_button = pyxbmct.Button('[COLOR %s]Delete Settings[/COLOR]' % OTHER_BUTTONS_TEXT,focusTexture=FBUTTON,noFocusTexture=BUTTON)
		self.placeControl(removeadvanced_button, 49, 21, 9, 9)
		self.connect(removeadvanced_button,lambda: removeAdvanced())

		view_error_button.setVisible(True)
		full_log_button.setVisible(True)
		upload_log_button.setVisible(True)
		
		removeaddons_button.setVisible(True)
		removeaddondata_all_button.setVisible(True)
		removeaddondata_u_button.setVisible(True)
		removeaddondata_e_button.setVisible(True)
	
		checksources_button.setVisible(True)
		checkrepos_button.setVisible(True)
		forceupdate_button.setVisible(True)
		fixaddonupdate_button.setVisible(True)
	
		Log_title.setVisible(True)
		Log_errors.setVisible(True)
	
		Addon.setVisible(True)
		scan.setVisible(True)
		fix.setVisible(True)
		delet.setVisible(True)
		delet1.setVisible(True)
		WhiteList.setVisible(True)
	
		whitelist_edit_button.setVisible(True)
		whitelist_view_button.setVisible(True)
		whitelist_clear_button.setVisible(True)
		whitelist_import_button.setVisible(True)
		whitelist_export_button.setVisible(True)
	
		Advan.setVisible(True)
		autoadvanced_buttonQ.setVisible(True)
		autoadvanced_button.setVisible(True)
		currentsettings_button.setVisible(True)
		removeadvanced_button.setVisible(True)
	
		self.ToolsButton.controlDown(view_error_button)
	
		view_error_button.controlUp(self.ToolsButton)
		view_error_button.controlDown(full_log_button)
		view_error_button.controlRight(autoadvanced_button)

		full_log_button.controlUp(view_error_button)
		full_log_button.controlDown(upload_log_button)
		full_log_button.controlRight(currentsettings_button)

		upload_log_button.controlUp(full_log_button)
		upload_log_button.controlDown(checksources_button)
		upload_log_button.controlRight(removeadvanced_button)

		autoadvanced_buttonQ.controlUp(self.ToolsButton)
		autoadvanced_buttonQ.controlLeft(view_error_button)
		autoadvanced_buttonQ.controlDown(autoadvanced_button)
		autoadvanced_buttonQ.controlRight(whitelist_edit_button)

		autoadvanced_button.controlUp(autoadvanced_buttonQ)
		autoadvanced_button.controlLeft(view_error_button)
		autoadvanced_button.controlDown(currentsettings_button)
		autoadvanced_button.controlRight(whitelist_view_button)

		currentsettings_button.controlUp(autoadvanced_button)
		currentsettings_button.controlLeft(full_log_button)
		currentsettings_button.controlDown(removeadvanced_button)
		currentsettings_button.controlRight(whitelist_clear_button)

		removeadvanced_button.controlUp(currentsettings_button)
		removeadvanced_button.controlLeft(upload_log_button)
		removeadvanced_button.controlDown(forceupdate_button)
		removeadvanced_button.controlRight(whitelist_import_button)

		whitelist_edit_button.controlUp(self.ToolsButton)
		whitelist_edit_button.controlLeft(autoadvanced_buttonQ)
		whitelist_edit_button.controlDown(whitelist_view_button)

		whitelist_view_button.controlUp(whitelist_edit_button)
		whitelist_view_button.controlLeft(autoadvanced_button)
		whitelist_view_button.controlDown(whitelist_clear_button)

		whitelist_clear_button.controlUp(whitelist_view_button)
		whitelist_clear_button.controlLeft(currentsettings_button)
		whitelist_clear_button.controlDown(whitelist_import_button)

		whitelist_import_button.controlUp(whitelist_clear_button)
		whitelist_import_button.controlLeft(removeadvanced_button)
		whitelist_import_button.controlDown(whitelist_export_button)

		whitelist_export_button.controlUp(whitelist_import_button)
		whitelist_export_button.controlLeft(removeadvanced_button)
		whitelist_export_button.controlDown(removeaddondata_u_button)

		checksources_button.controlUp(upload_log_button)
		checksources_button.controlDown(checkrepos_button)
		checksources_button.controlRight(forceupdate_button)

		checkrepos_button.controlUp(checksources_button)
		checkrepos_button.controlRight(fixaddonupdate_button)

		forceupdate_button.controlUp(removeadvanced_button)
		forceupdate_button.controlLeft(checksources_button)
		forceupdate_button.controlDown(fixaddonupdate_button)
		forceupdate_button.controlRight(removeaddons_button)

		fixaddonupdate_button.controlUp(forceupdate_button)
		fixaddonupdate_button.controlLeft(checkrepos_button)
		fixaddonupdate_button.controlRight(removeaddondata_all_button)

		removeaddons_button.controlUp(removeadvanced_button)
		removeaddons_button.controlLeft(forceupdate_button)
		removeaddons_button.controlDown(removeaddondata_all_button)
		removeaddons_button.controlRight(removeaddondata_u_button)

		removeaddondata_all_button.controlUp(removeaddons_button)
		removeaddondata_all_button.controlLeft(fixaddonupdate_button)
		removeaddondata_all_button.controlRight(removeaddondata_e_button)

		removeaddondata_u_button.controlUp(whitelist_export_button)
		removeaddondata_u_button.controlLeft(removeaddons_button)
		removeaddondata_u_button.controlDown(removeaddondata_e_button)

		removeaddondata_e_button.controlUp(removeaddondata_u_button)
		removeaddondata_e_button.controlLeft(removeaddondata_all_button)

##globals
global ver
global fan
global listbg
global buildbg
global maintbg
global speedthumb
global sysinfobg
global netinfobg
global splash
global bakresbg
global toolsbg
global wizinfogb
global listbgA  
global buildbgA
global buildinfobg

##################window##########################


##########Foreground Leave here####################




################################################################################
#######################################
##############Main Buttons#############
##globals
global MaintButton
global BackResButton
global ToolsButton
global BuildsButton

############# SOP ###############
#     button.controlUp(button)
#     button.controlLeft(button)
#     button.controlRight(button)
#     button.controlDown(button)
##################################

p = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
name = p.get('name', '')
url = p.get('url', '')
mode = p.get('mode', None)
iconimage = p.get('iconimage', ICON)
fanart = p.get('fanart', FANART)
description = p.get('description', '')
    
if mode is None:
    gui = Guiwiz()
    gui.doModal()
    del gui

elif mode == 'clearthumbs':
	clearThumb(shortcut=True)

elif mode == 'clearpackages':
	clearPackages(shortcut=True)

elif mode == 'clearcache':
	clearCache(shortcut=True)

elif mode == 'totalclean':
	totalClean(shortcut=True)

elif mode == 'forceclose':
	os._exit(1)

elif mode == 'install':
    buildWizard(name, url)

elif mode == 'speedtest':
    speed()

elif mode == 'savepremiumize'    : premiumizeit.premiumizeIt('update',     name)
elif mode == 'restorepremiumize' : premiumizeit.premiumizeIt('restore',    name)
elif mode == 'addonpremiumize'   : premiumizeit.premiumizeIt('clearaddon', name)
elif mode == 'clearpremiumize'   : premiumizeit.clearSaved(name)
elif mode == 'authpremiumize'    : premiumizeit.activatePremiumize(name); wiz.refresh()
elif mode == 'updatepremiumize'  : premiumizeit.autoUpdate('all')
elif mode == 'importpremiumize'  : premiumizeit.importlist(name); wiz.refresh()
elif mode == 'savealldebrid'     : alldebridit.alldebridIt('update',     name)
elif mode == 'restorealldebrid'  : alldebridit.alldebridIt('restore',    name)
elif mode == 'addonalldebrid'    : alldebridit.alldebridIt('clearaddon', name)
elif mode == 'clearalldebrid'    : alldebridit.clearSaved(name)
elif mode == 'authalldebrid'     : alldebridit.activateAllDebrid(name); wiz.refresh()
elif mode == 'updatealldebrid'   : alldebridit.autoUpdate('all')
elif mode == 'importalldebrid'   : alldebridit.importlist(name); wiz.refresh()
elif mode == 'savetorbox'        : torboxit.torboxIt('update',     name)
elif mode == 'restoretorbox'     : torboxit.torboxIt('restore',    name)
elif mode == 'addontorbox'       : torboxit.torboxIt('clearaddon', name)
elif mode == 'cleartorbox'       : torboxit.clearSaved(name)
elif mode == 'authtorbox'        : torboxit.activateTorBox(name); wiz.refresh()
elif mode == 'updatetorbox'      : torboxit.autoUpdate('all')
elif mode == 'importtorbox'      : torboxit.importlist(name); wiz.refresh()
elif mode == 'savelinksnappy'    : linksnappit.linksnappyIt('update',     name)
elif mode == 'restorelinksnappy' : linksnappit.linksnappyIt('restore',    name)
elif mode == 'addonlinksnappy'   : linksnappit.linksnappyIt('clearaddon', name)
elif mode == 'clearlinksnappy'   : linksnappit.clearSaved(name)
elif mode == 'authlinksnappy'    : linksnappit.activateLinkSnappy(name); wiz.refresh()
elif mode == 'updatelinksnappy'  : linksnappit.autoUpdate('all')
elif mode == 'importlinksnappy'  : linksnappit.importlist(name); wiz.refresh()
