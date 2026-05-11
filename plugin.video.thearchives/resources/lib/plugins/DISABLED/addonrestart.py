import sys
import xbmc
import xbmcaddon
import time 


class AddonRestart(object):

	def __init__(self):
		self.execu         = xbmc.executebuiltin
		self.addon         = xbmcaddon.Addon(sys.argv[1])
		self.message       = sys.argv[2]
		self.addoninfo     = self.addon.getAddonInfo
		self.addon_id      = self.addoninfo('id')
		self.addon_name    = self.addoninfo('name')
		self.addon_version = self.addoninfo('version')
		self.addon_icon    = self.addoninfo('icon')
		self.setting       = self.addon.getSetting
		self.setting_true  = lambda x: bool(True if self.setting(str(x)) == "true" else False)
		self.Run()

	def Run(self):
		self.Notify(message=self.message)
		self.StopAddon()
		self.StartAddon()

	def StopAddon(self):
		self.execu("ActivateWindow(Home)")

	def StartAddon(self):
		self.execu(f"RunAddon({self.addon_id})")

	def Notify(self,title='',message='',times='',icon=''):
		if title == '':
			title = self.addon_name
		if times == '':
			times = '10000'
		if icon == '':
			icon = self.addon_icon
		Notification = f'Notification({title},{message},{times},{icon})'
		self.execu(str(Notification))

if __name__ == '__main__':
	AddonRestart()