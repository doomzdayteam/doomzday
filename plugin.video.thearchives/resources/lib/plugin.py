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
sorted_plugin_cache = None
hook_plugin_cache = {}


def load_plugins_for_hook(function_name: str, other_args: Tuple[str, ...]) -> None:
    global sorted_plugin_cache
    try:
        from . import plugins
    except ImportError:
        return

    loader = getattr(plugins, "load_for_hook", None)
    if not loader:
        return

    if loader(function_name, *other_args):
        sorted_plugin_cache = None
        hook_plugin_cache.clear()


def get_plugins() -> List[Plugin]:
    global sorted_plugin_cache
    try:
        from . import plugins
    except ImportError:
        pass

    klasses = Plugin.subclasses
    plugins = []
    for klass in klasses:
        if klass in plugin_cache:
            plugins.append(plugin_cache[klass])
        else:
            plugin_cache[klass] = klass()
            plugins.append(plugin_cache[klass])
            sorted_plugin_cache = None
            hook_plugin_cache.clear()
    return plugins


def get_sorted_plugins() -> List[Plugin]:
    global sorted_plugin_cache
    if sorted_plugin_cache is None:
        sorted_plugin_cache = sorted(
            get_plugins(),
            key=lambda plugin: plugin.priority,
            reverse=True,
        )
    return sorted_plugin_cache


def get_hook_plugins(function_name: str) -> List[Plugin]:
    if function_name not in hook_plugin_cache:
        base_method = getattr(Plugin, function_name, None)
        hook_plugin_cache[function_name] = [
            plugin
            for plugin in get_sorted_plugins()
            if getattr(type(plugin), function_name, None) is not base_method
        ]
    return hook_plugin_cache[function_name]


def register_routes(plugin_route):
    plugins = get_plugins()
    for plugin in plugins:
        if hasattr(plugin, "routes"): plugin.routes(plugin_route)


def run_hook(*args: Tuple[str, ...], return_item_on_failure=False) -> Any:
    function_name = args[0]
    other_args = args[1:]
    load_plugins_for_hook(function_name, other_args)
    for plugin in get_hook_plugins(function_name):
        result = getattr(plugin, function_name)(*other_args)
        if result:
            return result
    if return_item_on_failure:
        if len(other_args) == 1:
            return other_args[0]
        else:
            return other_args
    return False
