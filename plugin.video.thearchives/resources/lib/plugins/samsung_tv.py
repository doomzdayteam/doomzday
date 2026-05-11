from ..plugin import Plugin
from ..DI import DI
import requests, json, xbmcgui
from resources.lib.plugin import run_hook

class samsung_tv(Plugin):
    name = "Samsung TV Plus"
    priority = 100
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'

    def process_item(self, item):
        if "samsung_tv" in item:
            link = item.get("samsung_tv", "")
            if link == "regions":
                item["link"] = "samsung_tv/regions"
                item["is_dir"] = True
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")))
                return item
            else:
                item["link"] = f"samsung_tv/region/{link}"
                item["is_dir"] = True
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")))
                return item
                

    def routes(self, plugin):
        @plugin.route("/samsung_tv/regions")
        def channels():
            r = requests.get("https://i.mjh.nz/SamsungTVPlus/app.json").json()
            jen_list = []
            for region_code, region in r["regions"].items():
                jen_data = {
                    "title": f"{region['name']} ({len(region['channels'])})",
                    "thumbnail": region["logo"],
                    "fanart": region["logo"],
                    "samsung_tv": region_code,
                    "type": "item"
                }
                jen_list.append(jen_data)
            
            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list]
            run_hook("display_list", jen_list)
        
        @plugin.route("/samsung_tv/region/<region>")
        def region_channels(region):
            r = requests.get("https://i.mjh.nz/SamsungTVPlus/app.json").json()
            jen_list = []
            for channel_code, channel in r["regions"][region]["channels"].items():
                guidedata = []
                for i, program in enumerate(channel["programs"]):
                    program_timestamp = program[0]
                    program_duration = (channel["programs"][i + 1][0] - program_timestamp) if i != len(channel["programs"]) - 1 else (60 * 60 * 2)
                    program_name = program[1].replace('"', "").replace("'", "")
                    guidedata.append({
                        'url': "",
                        'fanart': channel["logo"],
                        'mediatype': 'show',
                        'genre': [channel["group"]],
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
