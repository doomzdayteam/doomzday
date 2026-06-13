from ..plugin import Plugin
from ..DI import DI
import requests, xbmcgui
from bs4 import BeautifulSoup
from resources.lib.plugin import run_hook

class NginxDir(Plugin):
    name = "nginx_dir"
    priority = 100
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'

    def process_item(self, item):
        if self.name in item:
            link = item.get(self.name, "")
            item["link"] = f"{self.name}/" + link
            item["is_dir"] = True
            item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")))
            return item

    def routes(self, plugin):
        @plugin.route(f"/{self.name}/<path:dir>")
        def directory(dir):
            jen_list = []
            r = requests.get(dir).text
            soup = BeautifulSoup(r, "html.parser")
            if not dir.endswith("/"):
                dir += "/"
            files = soup.find_all("a")[1:]
            for file in files:
                filename = file.text
                href = file.get("href")
                is_dir = filename.endswith("/")
                jen_data = {
                    "title": filename,
                    "type": "dir" if is_dir else "item"
                }
                if is_dir:
                    jen_data["nginx_dir"] = dir + href
                else:
                    jen_data["link"] = dir + href
                jen_list.append(jen_data)
            
            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list]
            run_hook("display_list", jen_list)