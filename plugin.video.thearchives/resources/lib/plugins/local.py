import os
import xbmcaddon
import xbmcvfs

from ..plugin import Plugin

PATH = xbmcaddon.Addon().getAddonInfo("path")


class Local(Plugin):
    name = "local"

    def get_list(self, url):
        if url.startswith("file://"):
            url = url.replace("file://", "")
            input_file = xbmcvfs.File(os.path.join(PATH, "xml", url))
            return input_file.read()
