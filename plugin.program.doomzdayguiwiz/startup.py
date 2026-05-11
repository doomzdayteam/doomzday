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

import xbmc
import xbmcaddon
import xbmcgui
import os
import xbmcvfs
import glob
import re
import urllib.parse
import uservar
from datetime import date, datetime, timedelta
from resources.libs import notify, loginit, debridit, traktit, premiumizeit, alldebridit, torboxit, linksnappit, skinSwitch, uploadLog, wizard as wiz

ADDON_ID       = uservar.ADDON_ID
ADDONTITLE     = uservar.ADDONTITLE
ADDON          = wiz.addonId(ADDON_ID)
VERSION        = wiz.addonInfo(ADDON_ID,'version')
ADDONPATH      = wiz.addonInfo(ADDON_ID,'path')
ADDONID        = wiz.addonInfo(ADDON_ID,'id')
DIALOG         = xbmcgui.Dialog()
HOME           = xbmcvfs.translatePath('special://home/')
PROFILE        = xbmcvfs.translatePath('special://profile/')
ADDONS         = os.path.join(HOME,     'addons')
USERDATA       = os.path.join(HOME,     'userdata')
PLUGIN         = os.path.join(ADDONS,   ADDON_ID)
PACKAGES       = os.path.join(ADDONS,   'packages')
ADDONDATA      = os.path.join(USERDATA, 'addon_data', ADDON_ID)
TEXTCACHE      = os.path.join(ADDONDATA, 'Cache')
FANART         = os.path.join(ADDONPATH,'fanart.jpg')
ICON           = os.path.join(ADDONPATH,'icon.png')
ART            = os.path.join(ADDONPATH,'resources', 'art')
SKIN           = xbmc.getSkinDir()
THUMBS         = os.path.join(USERDATA,  'Thumbnails')
BUILDNAME      = wiz.getS('buildname')
DEFAULTSKIN    = wiz.getS('defaultskin')
DEFAULTNAME    = wiz.getS('defaultskinname')
DEFAULTIGNORE  = wiz.getS('defaultskinignore')
BUILDVERSION   = wiz.getS('buildversion')
BUILDLATEST    = wiz.getS('latestversion')
BUILDCHECK     = wiz.getS('lastbuildcheck')
DISABLEUPDATE  = wiz.getS('disableupdate')
AUTOCLEANUP    = wiz.getS('autoclean')
AUTOCACHE      = wiz.getS('clearcache')
AUTOPACKAGES   = wiz.getS('clearpackages')
AUTOTHUMBS     = wiz.getS('clearthumbs')
AUTOFEQ        = wiz.getS('autocleanfeq')
AUTONEXTRUN    = wiz.getS('nextautocleanup')
TRAKTSAVE      = wiz.getS('traktlastsave')
REALSAVE       = wiz.getS('debridlastsave')
LOGINSAVE      = wiz.getS('loginlastsave')
PREMIUMIZESAVE = wiz.getS('premiumizelastsave')
ALLDEBRIDSAVE  = wiz.getS('alldebridlastsave')
TORBOXSAVE     = wiz.getS('torboxlastsave')
LINKSNAPPYSAVE = wiz.getS('linksnappylastsave')
KEEPTRAKT      = wiz.getS('keeptrakt')
KEEPREAL       = wiz.getS('keepdebrid')
KEEPLOGIN      = wiz.getS('keeplogin')
KEEPPREMIUMIZE = wiz.getS('keeppremiumize')
KEEPALLDEBRID  = wiz.getS('keepalldebrid')
KEEPTORBOX     = wiz.getS('keeptorbox')
KEEPLINKSNAPPY = wiz.getS('keeplinksnappy')
INSTALLED      = wiz.getS('installed')
EXTRACT        = wiz.getS('extract')
EXTERROR       = wiz.getS('errors')
NOTIFY         = wiz.getS('notify')
NOTEDISMISS    = wiz.getS('notedismiss')
NOTEID         = wiz.getS('noteid')
BACKUPLOCATION = ADDON.getSetting('path') if not ADDON.getSetting('path') == '' else HOME
MYBUILDS       = os.path.join(BACKUPLOCATION, 'My_Builds', '')
NOTEID         = 0 if NOTEID == "" else int(NOTEID)
AUTOFEQ        = int(AUTOFEQ) if AUTOFEQ.isdigit() else 0
TODAY          = date.today()
TOMORROW       = TODAY + timedelta(days=1)
TWODAYS        = TODAY + timedelta(days=2)
THREEDAYS      = TODAY + timedelta(days=3)
ONEWEEK        = TODAY + timedelta(days=7)
from resources.libs.system_info import kodi_version_major as _kodi_major
KODIV          = _kodi_major()
EXCLUDES       = uservar.EXCLUDES
BUILDFILE      = uservar.BUILDFILE
UPDATECHECK    = uservar.UPDATECHECK if str(uservar.UPDATECHECK).isdigit() else 1
NEXTCHECK      = TODAY + timedelta(days=UPDATECHECK)
NOTIFICATION   = uservar.NOTIFICATION
ENABLE         = uservar.ENABLE
HEADERMESSAGE  = uservar.HEADERMESSAGE
COLOR1         = uservar.COLOR1
COLOR2         = uservar.COLOR2
WORKING        = True if wiz.workingURL(BUILDFILE) == True else False
FAILED         = False





###########################
#### Check Updates   ######
###########################
def checkUpdate():
	BUILDNAME      = wiz.getS('buildname')
	BUILDVERSION   = wiz.getS('buildversion')
	link           = wiz.openURL(BUILDFILE).replace('\n','').replace('\r','').replace('\t','')
	match          = re.compile('name="%s".+?ersion="(.+?)".+?con="(.+?)".+?anart="(.+?)"' % BUILDNAME).findall(link)
	if len(match) > 0:
		version = match[0][0]
		icon    = match[0][1]
		fanart  = match[0][2]
		wiz.setS('latestversion', version)
		if version > BUILDVERSION:
			if DISABLEUPDATE == 'false':
				wiz.log("[Check Updates] [Installed Version: %s] [Current Version: %s] Opening Update Window" % (BUILDVERSION, version), xbmc.LOGINFO)
				notify.updateWindow(BUILDNAME, BUILDVERSION, version, icon, fanart)
			else: wiz.log("[Check Updates] [Installed Version: %s] [Current Version: %s] Update Window Disabled" % (BUILDVERSION, version), xbmc.LOGINFO)
		else: wiz.log("[Check Updates] [Installed Version: %s] [Current Version: %s]" % (BUILDVERSION, version), xbmc.LOGINFO)
	else: wiz.log("[Check Updates] ERROR: Unable to find build version in build text file", xbmc.LOGERROR)

def checkSkin():
	wiz.log("[Build Check] Invalid Skin Check Start")
	DEFAULTSKIN   = wiz.getS('defaultskin')
	DEFAULTNAME   = wiz.getS('defaultskinname')
	DEFAULTIGNORE = wiz.getS('defaultskinignore')
	gotoskin = False
	if not DEFAULTSKIN == '':
		if os.path.exists(os.path.join(ADDONS, DEFAULTSKIN)):
			if DIALOG.yesno(ADDONTITLE, "[COLOR %s]It seems that the skin has been set back to [COLOR %s]%s[/COLOR]" % (COLOR2, COLOR1, SKIN[5:].title()) + "\nWould you like to set the skin back to:[/COLOR]" + '[\nCOLOR %s]%s[/COLOR]' % (COLOR1, DEFAULTNAME)):
				gotoskin = DEFAULTSKIN
				gotoname = DEFAULTNAME
			else: wiz.log("Skin was not reset", xbmc.LOGINFO); wiz.setS('defaultskinignore', 'true'); gotoskin = False
		else: wiz.setS('defaultskin', ''); wiz.setS('defaultskinname', ''); DEFAULTSKIN = ''; DEFAULTNAME = ''
	if DEFAULTSKIN == '':
		skinname = []
		skinlist = []
		for folder in glob.glob(os.path.join(ADDONS, 'skin.*/')):
			xml = "%s/addon.xml" % folder
			if os.path.exists(xml):
				f  = open(xml,mode='r', encoding='utf-8'); g = f.read().replace('\n','').replace('\r','').replace('\t',''); f.close();
				match  = wiz.parseDOM(g, 'addon', ret='id')
				match2 = wiz.parseDOM(g, 'addon', ret='name')
				wiz.log("%s: %s" % (folder, str(match[0])), xbmc.LOGINFO)
				if len(match) > 0: skinlist.append(str(match[0])); skinname.append(str(match2[0]))
				else: wiz.log("ID not found for %s" % folder, xbmc.LOGINFO)
			else: wiz.log("ID not found for %s" % folder, xbmc.LOGINFO)
		if len(skinlist) > 0:
			if len(skinlist) > 1:
				if DIALOG.yesno(ADDONTITLE, "[COLOR %s]It seems that the skin has been set back to [COLOR %s]%s[/COLOR]" % (COLOR2, COLOR1, SKIN[5:].title()) + "\nWould you like to view a list of avaliable skins?[/COLOR]"):
					choice = DIALOG.select("Select skin to switch to!", skinname)
					if choice == -1: wiz.log("Skin was not reset", xbmc.LOGINFO); wiz.setS('defaultskinignore', 'true')
					else: 
						gotoskin = skinlist[choice]
						gotoname = skinname[choice]
				else: wiz.log("Skin was not reset", xbmc.LOGINFO); wiz.setS('defaultskinignore', 'true')
			else:
				if DIALOG.yesno(ADDONTITLE, "[COLOR %s]It seems that the skin has been set back to [COLOR %s]%s[/COLOR]" % (COLOR2, COLOR1, SKIN[5:].title()) + "\nWould you like to set the skin back to:[/COLOR]" + '\n[COLOR %s]%s[/COLOR]' % (COLOR1, skinname[0])):
					gotoskin = skinlist[0]
					gotoname = skinname[0]
				else: wiz.log("Skin was not reset", xbmc.LOGINFO); wiz.setS('defaultskinignore', 'true')
		else: wiz.log("No skins found in addons folder.", xbmc.LOGINFO); wiz.setS('defaultskinignore', 'true'); gotoskin = False
	if gotoskin:
		skinSwitch.swapSkins(gotoskin)
		x = 0
		xbmc.sleep(1000)
		while not xbmc.getCondVisibility("Window.isVisible(yesnodialog)") and x < 150:
			x += 1
			xbmc.sleep(200)

		if xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
			wiz.ebi('SendClick(11)')
			wiz.lookandFeelData('restore')
		else: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE),'[COLOR %s]Skin Swap Timed Out![/COLOR]' % COLOR2)
	wiz.log("[Build Check] Invalid Skin Check End", xbmc.LOGINFO)

while xbmc.Player().isPlayingVideo():
	xbmc.sleep(1000)

try:
	mybuilds = xbmcvfs.translatePath(MYBUILDS)
	if not os.path.exists(mybuilds): xbmcvfs.mkdirs(mybuilds)
except Exception:
	pass

wiz.log("[Notifications] Started", xbmc.LOGINFO)
if ENABLE == 'Yes':
	if not NOTIFY == 'true':
		url = wiz.workingURL(NOTIFICATION)
		if url == True:
			id, msg = wiz.splitNotify(NOTIFICATION)
			if not id == False:
				try:
					id = int(id); NOTEID = int(NOTEID)
					if id == NOTEID:
						if NOTEDISMISS == 'false':
							notify.notification(msg)
						else: wiz.log("[Notifications] id[%s] Dismissed" % int(id), xbmc.LOGINFO)
					elif id > NOTEID:
						wiz.log("[Notifications] id: %s" % str(id), xbmc.LOGINFO)
						wiz.setS('noteid', str(id))
						wiz.setS('notedismiss', 'false')
						notify.notification(msg=msg)
						wiz.log("[Notifications] Complete", xbmc.LOGINFO)
				except Exception as e:
					wiz.log("Error on Notifications Window: %s" % str(e), xbmc.LOGERROR)
			else: wiz.log("[Notifications] Text File not formated Correctly")
		else: wiz.log("[Notifications] URL(%s): %s" % (NOTIFICATION, url), xbmc.LOGINFO)
	else: wiz.log("[Notifications] Turned Off", xbmc.LOGINFO)
else: wiz.log("[Notifications] Not Enabled", xbmc.LOGINFO)

# ── First-run: seed favourites.xml if userdata has none yet ──────────────────
_favdest = os.path.join(USERDATA, 'favourites.xml')
_favsrc  = os.path.join(ADDONPATH, 'resources', 'text examples', 'favourites.xml')
if not os.path.exists(_favdest) and os.path.exists(_favsrc):
    import shutil
    shutil.copy2(_favsrc, _favdest)
    wiz.log("[First Run] Seeded favourites.xml into userdata", xbmc.LOGINFO)
# ─────────────────────────────────────────────────────────────────────────────

wiz.log("[Installed Check] Started", xbmc.LOGINFO)
if INSTALLED == 'true':
	wiz.kodi17Fix()
	if SKIN in ['skin.estuary']:
		checkSkin()
		FAILED = True
	elif not EXTRACT == '100' and not BUILDNAME == "":
		wiz.log("[Installed Check] Build was extracted %s/100 with [ERRORS: %s]" % (EXTRACT, EXTERROR), xbmc.LOGINFO)
		yes=DIALOG.yesno(ADDONTITLE, '[COLOR %s]%s[/COLOR] [COLOR %s]was not installed correctly!' % (COLOR1, COLOR2, BUILDNAME) + '\nInstalled: [COLOR %s]%s[/COLOR] / Error Count: [COLOR %s]%s[/COLOR]' % (COLOR1, EXTRACT, COLOR1, EXTERROR) + '\nWould you like to try again?[/COLOR]', nolabel='[B]No Thanks![/B]', yeslabel='[B]Retry Install[/B]')
		wiz.clearS('build')
		FAILED = True
		if yes: 
			wiz.ebi("PlayMedia(plugin://%s/?mode=install&name=%s&url=fresh)" % (ADDON_ID, urllib.parse.quote_plus(BUILDNAME)))
			wiz.log("[Installed Check] Fresh Install Re-activated", xbmc.LOGINFO)
		else: wiz.log("[Installed Check] Reinstall Ignored")
	elif SKIN in ['skin.estuary']:
		wiz.log("[Installed Check] Incorrect skin: %s" % SKIN, xbmc.LOGINFO)
		defaults = wiz.getS('defaultskin')
		if not defaults == '':
			if os.path.exists(os.path.join(ADDONS, defaults)):
				skinSwitch.swapSkins(defaults)
				x = 0
				xbmc.sleep(1000)
				while not xbmc.getCondVisibility("Window.isVisible(yesnodialog)") and x < 150:
					x += 1
					xbmc.sleep(200)

				if xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
					wiz.ebi('SendClick(11)')
					wiz.lookandFeelData('restore')
		if not wiz.currSkin() == defaults and not BUILDNAME == "":
			FAILED = True
			wiz.log('[Installed Check] Skin mismatch — reinstall build to restore skin settings', xbmc.LOGINFO)
	else:
		wiz.log('[Installed Check] Install seems to be completed correctly', xbmc.LOGINFO)
	if not wiz.getS('pvrclient') == "":
		wiz.toggleAddon(wiz.getS('pvrclient'), 1)
		wiz.ebi('StartPVRManager')
	wiz.addonUpdates('reset')
	if KEEPTRAKT == 'true': traktit.traktIt('restore', 'all'); wiz.log('[Installed Check] Restoring Trakt Data', xbmc.LOGINFO)
	if KEEPREAL  == 'true': debridit.debridIt('restore', 'all'); wiz.log('[Installed Check] Restoring Real Debrid Data', xbmc.LOGINFO)
	if KEEPLOGIN == 'true': loginit.loginIt('restore', 'all'); wiz.log('[Installed Check] Restoring Login Data', xbmc.LOGINFO)
	if KEEPPREMIUMIZE == 'true': premiumizeit.premiumizeIt('restore', 'all'); wiz.log('[Installed Check] Restoring Premiumize Data', xbmc.LOGINFO)
	if KEEPALLDEBRID  == 'true': alldebridit.alldebridIt('restore', 'all'); wiz.log('[Installed Check] Restoring AllDebrid Data', xbmc.LOGINFO)
	if KEEPTORBOX     == 'true': torboxit.torboxIt('restore', 'all'); wiz.log('[Installed Check] Restoring TorBox Data', xbmc.LOGINFO)
	if KEEPLINKSNAPPY == 'true': linksnappit.linksnappyIt('restore', 'all'); wiz.log('[Installed Check] Restoring LinkSnappy Data', xbmc.LOGINFO)
	wiz.clearS('install')
else: wiz.log("[Installed Check] Not Enabled", xbmc.LOGINFO)

if FAILED == False:
	wiz.log("[Build Check] Started", xbmc.LOGINFO)
	if not WORKING:
		wiz.log("[Build Check] Not a valid URL for Build File: %s" % BUILDFILE, xbmc.LOGINFO)
	elif BUILDCHECK == '' and BUILDNAME == '':
		wiz.log("[Build Check] First Run", xbmc.LOGINFO)
		notify.firstRunSettings()
		xbmc.sleep(500)
		notify.firstRun()
		xbmc.sleep(500)
		wiz.setS('lastbuildcheck', str(NEXTCHECK))
	elif not BUILDNAME == '':
		wiz.log("[Build Check] Build Installed", xbmc.LOGINFO)
		if SKIN in ['skin.estuary'] and not DEFAULTIGNORE == 'true':
			checkSkin()
			wiz.log("[Build Check] Build Installed: Checking Updates", xbmc.LOGINFO)
			wiz.setS('lastbuildcheck', str(NEXTCHECK))
			checkUpdate()
		elif BUILDCHECK <= str(TODAY):
			wiz.log("[Build Check] Build Installed: Checking Updates", xbmc.LOGINFO)
			wiz.setS('lastbuildcheck', str(NEXTCHECK))
			checkUpdate()
		else: 
			wiz.log("[Build Check] Build Installed: Next check isnt until: %s / TODAY is: %s" % (BUILDCHECK, str(TODAY)), xbmc.LOGINFO)

wiz.log("[Trakt Data] Started", xbmc.LOGINFO)
if KEEPTRAKT == 'true':
	if TRAKTSAVE <= str(TODAY):
		wiz.log("[Trakt Data] Saving all Data", xbmc.LOGINFO)
		traktit.autoUpdate('all')
		wiz.setS('traktlastsave', str(THREEDAYS))
	else: 
		wiz.log("[Trakt Data] Next Auto Save isnt until: %s / TODAY is: %s" % (TRAKTSAVE, str(TODAY)), xbmc.LOGINFO)
else: wiz.log("[Trakt Data] Not Enabled", xbmc.LOGINFO)

wiz.log("[Real Debrid Data] Started", xbmc.LOGINFO)
if KEEPREAL == 'true':
	if REALSAVE <= str(TODAY):
		wiz.log("[Real Debrid Data] Saving all Data", xbmc.LOGINFO)
		debridit.autoUpdate('all')
		wiz.setS('debridlastsave', str(THREEDAYS))
	else: 
		wiz.log("[Real Debrid Data] Next Auto Save isnt until: %s / TODAY is: %s" % (REALSAVE, str(TODAY)), xbmc.LOGINFO)
else: wiz.log("[Real Debrid Data] Not Enabled", xbmc.LOGINFO)

wiz.log("[Login Data] Started", xbmc.LOGINFO)
if KEEPLOGIN == 'true':
	if LOGINSAVE <= str(TODAY):
		wiz.log("[Login Data] Saving all Data", xbmc.LOGINFO)
		loginit.autoUpdate('all')
		wiz.setS('loginlastsave', str(THREEDAYS))
	else: 
		wiz.log("[Login Data] Next Auto Save isnt until: %s / TODAY is: %s" % (LOGINSAVE, str(TODAY)), xbmc.LOGINFO)
else: wiz.log("[Login Data] Not Enabled", xbmc.LOGINFO)

wiz.log("[Premiumize Data] Started", xbmc.LOGINFO)
if KEEPPREMIUMIZE == 'true':
	if PREMIUMIZESAVE <= str(TODAY):
		wiz.log("[Premiumize Data] Saving all Data", xbmc.LOGINFO)
		premiumizeit.autoUpdate('all')
		wiz.setS('premiumizelastsave', str(THREEDAYS))
	else: 
		wiz.log("[Premiumize Data] Next Auto Save isnt until: %s / TODAY is: %s" % (PREMIUMIZESAVE, str(TODAY)), xbmc.LOGINFO)
else: wiz.log("[Premiumize Data] Not Enabled", xbmc.LOGINFO)

wiz.log("[AllDebrid Data] Started", xbmc.LOGINFO)
if KEEPALLDEBRID == 'true':
	if ALLDEBRIDSAVE <= str(TODAY):
		wiz.log("[AllDebrid Data] Saving all Data", xbmc.LOGINFO)
		alldebridit.autoUpdate('all')
		wiz.setS('alldebridlastsave', str(THREEDAYS))
	else:
		wiz.log("[AllDebrid Data] Next Auto Save isnt until: %s / TODAY is: %s" % (ALLDEBRIDSAVE, str(TODAY)), xbmc.LOGINFO)
else: wiz.log("[AllDebrid Data] Not Enabled", xbmc.LOGINFO)

wiz.log("[TorBox Data] Started", xbmc.LOGINFO)
if KEEPTORBOX == 'true':
	if TORBOXSAVE <= str(TODAY):
		wiz.log("[TorBox Data] Saving all Data", xbmc.LOGINFO)
		torboxit.autoUpdate('all')
		wiz.setS('torboxlastsave', str(THREEDAYS))
	else:
		wiz.log("[TorBox Data] Next Auto Save isnt until: %s / TODAY is: %s" % (TORBOXSAVE, str(TODAY)), xbmc.LOGINFO)
else: wiz.log("[TorBox Data] Not Enabled", xbmc.LOGINFO)

wiz.log("[LinkSnappy Data] Started", xbmc.LOGINFO)
if KEEPLINKSNAPPY == 'true':
	if LINKSNAPPYSAVE <= str(TODAY):
		wiz.log("[LinkSnappy Data] Saving all Data", xbmc.LOGINFO)
		linksnappit.autoUpdate('all')
		wiz.setS('linksnappylastsave', str(THREEDAYS))
	else:
		wiz.log("[LinkSnappy Data] Next Auto Save isnt until: %s / TODAY is: %s" % (LINKSNAPPYSAVE, str(TODAY)), xbmc.LOGINFO)
else: wiz.log("[LinkSnappy Data] Not Enabled", xbmc.LOGINFO)
filesize = int(wiz.getS('filesize_alert'))
filesize_thumb = int(wiz.getS('filesizethumb_alert'))
total_size2 = 0
total_size = 0
count = 0
total_sizetext2 = "%.0f" % (total_size2/1024000.0)

for dirpath, dirnames, filenames in os.walk(PACKAGES):
	count = 0
	for f in filenames:
		count += 1
		fp = os.path.join(dirpath, f)
		total_size += os.path.getsize(fp)
total_sizetext = "%.0f" % (total_size/1024000.0)
	
if int(total_sizetext) > filesize:
	wiz.clearPackagesStart(); wiz.refresh()
	wiz.log("[Auto Cleaner] Package Cleaner Triggered", xbmc.LOGINFO)
	
for dirpath2, dirnames2, filenames2 in os.walk(THUMBS):
	for f2 in filenames2:
		fp2 = os.path.join(dirpath2, f2)
		total_size2 += os.path.getsize(fp2)
total_sizetext2 = "%.0f" % (total_size2/1024000.0)

if int(total_sizetext2) > filesize_thumb:
	wiz.clearThumb(); wiz.refresh()
	wiz.log("[Auto Cleaner] Thumbs Cleaner Triggered", xbmc.LOGINFO)

if wiz.getS('clearcache') == 'true':
	wiz.clearCache(); wiz.refresh()
	wiz.log("[Auto Cleaner] Thumbs Cleaner Triggered", xbmc.LOGINFO)
