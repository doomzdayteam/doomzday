from ..plugin import Plugin
from ..DI import DI
import requests, xbmcgui
from resources.lib.plugin import run_hook

class stirr(Plugin):
    name = "plex"
    priority = 100
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'

    def process_item(self, item):
        if self.name in item:
            link = item.get(self.name, "")
            if link == "groups":
                item["link"] = f"{self.name}/groups"
                item["is_dir"] = True
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")))
                return item
            else:
                item["link"] = f"{self.name}/group/{link}"
                item["is_dir"] = True
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")))
                return item
                

    def routes(self, plugin):
        @plugin.route(f"/{self.name}/groups")
        def groups():
            r = requests.get("https://i.mjh.nz/Plex/app.json").json()
            jen_list = []
            for group in sorted(set([channel["regions"][0] for channel in r["channels"].values()])):
                jen_data = {
                    "title": group,
                    self.name: group,
                    "type": "dir"
                }
                jen_list.append(jen_data)

            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list]
            run_hook("display_list", jen_list)
        
        @plugin.route(f"/{self.name}/group/<group>")
        def group_channels(group):
            r = requests.get("https://i.mjh.nz/Plex/app.json").json()
            jen_list = []
            for channel in r["channels"].values():
                if group not in channel["regions"]:
                    continue
                guidedata = []
                for i, program in enumerate(channel["programs"]):
                    program_timestamp = program[0]
                    program_duration = (channel["programs"][i + 1][0] - program_timestamp) if i != len(channel["programs"]) - 1 else (60 * 60 * 2)
                    program_name = program[1].replace('"', "").replace("'", "")
                    guidedata.append({
                        'url': "",
                        'fanart': channel["logo"],
                        'mediatype': 'show',
                        'genre': [channel["regions"][0]],
                        'starttime': program_timestamp,
                        'duration': program_duration, 
                        'label': program_name, 
                        'label2': 'HD',
                        'channelname': channel["name"].replace('"', "").replace("'", ""), 
                        'art': {
                            'thumb': channel["logo"],
                            'fanart': channel["logo"], 
                            'poster': '', 
                            'logo': '', 
                            'clearart': '',
                            'icon': channel["logo"]
                        } 
                    })
                jen_data = {
                    "title": channel["name"].replace('"', "").replace("'", ""),
                    "thumbnail": channel["logo"],
                    "fanart": channel["logo"],
                    "link": channel["url"],
                    "guidedata": guidedata,
                    "type": "item"
                }
                jen_list.append(jen_data)
            
            jen_list = list(sorted(jen_list, key=lambda x: x["title"]))
            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list]
            run_hook("display_list", jen_list)
