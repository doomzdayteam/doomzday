import json
import xbmc
from ..plugin import Plugin


class json_parser(Plugin):
    name = "json_parser"
    description = "add json format support"
    priority = 0

    def parse_list(self, url: str, response):
        if url.endswith(".json") or '"items": [' in response :
            try:
                return [i for i in json.loads(response)["items"] if not i.get("enabled","true").lower()=="false"]
            except json.decoder.JSONDecodeError:
                xbmc.log(f"invalid json: {response}", xbmc.LOGINFO)
