from ..plugin import Plugin
from ..DI import DI
import requests, xbmcgui
from bs4 import BeautifulSoup
from resources.lib.plugin import run_hook

class ApacheDir(Plugin):
    name = "apache_dir"
    priority = 100
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'

    def process_item(self, item):
        if self.name in item:
            link = item.get(self.name, "")
            item["link"] = f"{self.name}/directory/" + link
            item["is_dir"] = True
            item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")))
            return item

    def routes(self, plugin):
        @plugin.route(f"/{self.name}/directory/<path:dir>")
        def directory(dir):
            jen_list = []
            r = requests.get(dir).text
            soup = BeautifulSoup(r, "html.parser")
            if not dir.endswith("/"):
                dir += "/"
            files = soup.find_all("tr")[2:-1]
            for file in files:
                icon = file.select_one("img").get("src")
                filename = file.select_one("a").text
                if filename == "Parent Directory":
                    continue
                href = file.select_one("a").text
                last_modified = file.select("td")[2].text
                size = file.select("td")[3].text
                description = file.select("td")[4].text
                jen_data = {
                    "title": filename,
                    "summary": f"Name: {filename}\nLast modified: {last_modified}\nSize: {size}\nDescription: {description}",
                    "type": "dir" if "folder" in icon or filename.endswith(".json") else "item"
                }
                if "folder" in icon:
                    jen_data["apache_dir"] = dir + href
                else:
                    jen_data["link"] = dir + href
                jen_list.append(jen_data)
            
            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list]
            run_hook("display_list", jen_list)