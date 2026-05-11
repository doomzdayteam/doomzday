import abc
import xbmcgui
from resources.lib.DI import DI

from typing import List, Tuple, Any, Optional, Union, Dict

abstractstaticmethod = abc.abstractmethod


class abstractclassmethod(classmethod):
    __isabstractmethod__ = True

    def __init__(self, callable):
        callable.__isabstractmethod__ = True
        super(abstractclassmethod, self).__init__(callable)


class Plugin:
    __metaclass__ = abc.ABCMeta
    name = "Plugin"
    description = ""
    priority = 100
    subclasses = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.subclasses.append(cls)

    def get_list(self, url: str) -> Optional[str]:
        pass

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        pass

    def process_item(
        self, item: Dict[str, str]
    ) -> Optional[Dict[str, Union[str, xbmcgui.ListItem]]]:
        pass

    def get_metadata(
        self, item: Dict[str, Union[str, xbmcgui.ListItem]]
    ) -> Optional[Dict[str, Union[str, xbmcgui.ListItem]]]:
        pass

    def display_list(
        self, jen_list: List[Optional[Dict[str, Union[str, xbmcgui.ListItem]]]]
    ) -> Optional[bool]:
        pass

    def play_video(self, video: str) -> Optional[bool]:
        pass

    def pre_play(self, video: str) -> Optional[bool]:
        pass


plugin_cache = {}


def get_plugins() -> List[Plugin]:
    from . import plugins

    klasses = Plugin.subclasses
    plugins = []
    for klass in klasses:
        if klass in plugin_cache:
            plugins.append(plugin_cache[klass])
        else:
            plugin_cache[klass] = klass()
            plugins.append(plugin_cache[klass])
    return plugins

def register_routes(plugin_route):
    plugins = get_plugins()
    for plugin in plugins:
        if hasattr(plugin, "routes"): plugin.routes(plugin_route)


def run_hook(*args: Tuple[str, ...], return_item_on_failure=False) -> Any:
    plugins = get_plugins()
    function_name = args[0]
    other_args = args[1:]
    plugins = sorted(plugins, key=lambda plugin: plugin.priority, reverse=True)
    for plugin in plugins:
        result = getattr(plugin, function_name)(*other_args)
        if result:
            return result
    if return_item_on_failure:
        if len(other_args) == 1:
            return other_args[0]
        else:
            return other_args
    return False
