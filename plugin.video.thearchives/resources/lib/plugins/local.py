import os
import re
import xbmcaddon
import xbmcvfs

from ..plugin import Plugin

PATH = xbmcaddon.Addon().getAddonInfo("path")


def _translate_path(path):
    if path.startswith("special://") and hasattr(xbmcvfs, "translatePath"):
        return xbmcvfs.translatePath(path)
    return path


def _local_file_path(url):
    if not url.startswith("file://"):
        return ""

    path = url.replace("file://", "", 1)
    path = re.sub(r"^/([A-Za-z]:[\\/])", r"\1", path)
    path = _translate_path(path)

    if os.path.isabs(path) or path.startswith("\\\\"):
        return path
    return os.path.join(PATH, "xml", path)


class Local(Plugin):
    name = "local"

    def get_list(self, url):
        file_path = _local_file_path(url)
        if file_path:
            input_file = xbmcvfs.File(file_path)
            return input_file.read()
