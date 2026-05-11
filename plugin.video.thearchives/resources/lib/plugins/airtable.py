from ..plugin import Plugin
import xbmc
from resources.lib.external.airtable.airtable import Airtable
from resources.lib.plugin import run_hook
import xml.etree.ElementTree as ET

CACHE_TIME = 0

class airtable(Plugin):
    name = "airtable"

    def routes(self, plugin):
        @plugin.route("/airtable/jen/<table_info>")
        def airtable_jen(table_info):
            args_split = table_info.split("***")
            table_split = args_split[0].split("|")
            
            table_type = table_split[0]
            table_base = table_split[-3]
            table_id = table_split[-2]
            
            at = Airtable(table_id, table_base, api_key=args_split[1])
            if table_type == "season" or table_type == "show":
                match = at.search('category', table_base + "_" + table_split[-1], view='Grid view')
            else:
                match = at.get_all(sort=['name'])
            jen_list = []
            for field in match:
                try:
                    res = field['fields']                   
                    keys = res.keys()
                    thumbnail = res.get("thumbnail", "")
                    fanart = res.get("fanart", "")
                    summary = res.get("summary", "")         
                    name = res['name']
                    links = []
                    # for i in range(1, 5):
                        # if "link" + str(i) in res:
                            # link = res["link" + str(i)]
                    for k in keys:
                        if not 'link' in k : continue
                        elif 'link' in k and res[k] == '-' : continue
                        else  : 
                            link = res[k]                           
                            if link == "-": continue
                            if "/live/" in link:
                                link = "ffmpegdirect://" + link
                            links.append(link)
                            if link.endswith(".json"): break
                            
                    jen_data = {
                        "title": name,
                        "link": (links if len(links) > 1 else links[0]) if len(links) > 0 else "",
                        "thumbnail": thumbnail,
                        "fanart": fanart,
                        "summary": summary,
                        "type": "dir" if len(links) > 0 and (links[0].endswith(".json") or ("youtube.com" in links[0] and ("playlist" in links[0] or "channel" in links[0]))) else "item"
                    }
                    if len(links) > 0 and links[0].startswith("<"):
                        root = ET.fromstring(links[0])
                        jen_data[root.tag] = root.text
                    
                    jen_list.append(jen_data)
                except Exception as e:
                    continue
            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list]
            run_hook("display_list", jen_list)