#######
# Example for  adding items
# 
# "contextmenu":[
#                {"label":"Dialog OK","action":"RunScript(special://home/addons/plugin.video.microjen/resources/lib/scripts/dialogok.py)"},
#                {"label":"AddonRestart","action":"RunPlugin(plugin://plugin.video.microjen/run_script/script%3Fscript%3Dspecial%3A%2F%2Fhome%2Faddons%2Fplugin.video.microjen%2Fresources%2Flib%2Fscripts%2Faddonrestart.py%26args%3Dplugin.video.microjen%26args%3DAddon+Restarting+please+wait)"},
#                {"label":"DailyMotion Settings","action":"Addon.OpenSettings(plugin.video.dailymotion_com)"}
#                           ]
#######
# Any of  of the built in functions can be called as the action
# https://codedocs.xyz/AlwinEsch/kodi/page__list_of_built_in_functions.html 
#######

from ..plugin import Plugin


class ContextMenu(Plugin):

	name = 'contextmenu'
	description = 'ContextMenu support'
	priority = 200

	def get_metadata(self, item):
		menu = []
		if 'contextmenu' in item:
			contextmenu = item.get('contextmenu')
			for c in contextmenu:
				action = c.get('action')
				menu.append((c.get('label'),action))
		item["list_item"].addContextMenuItems(menu)
		return item