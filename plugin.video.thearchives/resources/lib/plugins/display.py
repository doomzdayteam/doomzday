from ..plugin import Plugin
from xbmcplugin import addDirectoryItems, endOfDirectory, setContent
from ..DI import DI
import sys

route_plugin = DI.plugin


class display(Plugin):
    name = "display"

    def display_list(self, jen_list):
        display_list = [(route_plugin.url_for_path(item["link"]), item["list_item"], item["is_dir"]) for item in jen_list]    	
        addDirectoryItems(route_plugin.handle, display_list, len(display_list))
        content = { item.get("content") for item in jen_list }
        category = "movies"
        if content == { "video" }:
            category = "videos"
        elif content == { "tvshow"} or content == {"season"}:
            category = "tvshows"
        elif content == { "episode"}:
            category = "episodes"
        setContent(int(sys.argv[1]),  category) 
        endOfDirectory(route_plugin.handle)
        return True
