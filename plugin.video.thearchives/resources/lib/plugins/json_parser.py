import json
import xbmc
from ..plugin import Plugin


class json_parser(Plugin):
    name = "json_parser"
    description = "add json format support"
    priority = 0

    def parse_list(self, url: str, response):
        if isinstance(response, bytes):
            response = response.decode("utf-8-sig")
        else:
            response = response.lstrip("\ufeff")
        stripped = response.lstrip()
        if url.endswith(".json") or (stripped.startswith("{") and '"items"' in stripped):
            try:
                return [i for i in json.loads(response)["items"] if not i.get("enabled","true").lower()=="false"]
            except json.decoder.JSONDecodeError:
                xbmc.log(f"invalid json: {response}", xbmc.LOGINFO)
