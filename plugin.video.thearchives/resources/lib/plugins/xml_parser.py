from ..plugin import Plugin
from typing import Dict
from urllib.parse import quote
import xml.etree.ElementTree as ET
import re


DEAD_ART_HOSTS = ("miniaturelife67.co.uk",)


def _clean_art(result):
    for key in ("thumbnail", "fanart", "animated_thumbnail", "animated_fanart"):
        value = str(result.get(key) or "")
        if any(host in value.lower() for host in DEAD_ART_HOSTS):
            result[key] = ""
    return result


def _route_link(prefix, value):
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith(f"{prefix}/"):
        return value
    return f"{prefix}/{value.lstrip('/')}"


def _clean_title(value):
    value = re.sub(r"\[[^\]]+\]", "", str(value or ""))
    return " ".join(value.split())


def _compat_link(result):
    if result.get("link"):
        return result
    tmdb = (result.get("tmdb") or "").strip()
    title = _clean_title(result.get("title") or result.get("name"))
    if tmdb.startswith("list/") and title:
        result["link"] = f"tmdb/legacy_list/{tmdb.split('/', 1)[1]}/{quote(title, safe='')}"
        return result
    for key, prefix in (("tmdb", "tmdb"), ("trakt", "trakt")):
        route = _route_link(prefix, result.get(key))
        if route:
            result["link"] = route
            return result
    for key in ("url", "path", "custom"):
        value = (result.get(key) or "").strip()
        if value:
            result["link"] = value
            return result
    return result


class xml(Plugin):
    name = "xml"
    description = "add support for xml jen format"
    priority = 0

    def parse_list(self, url: str, response):
        if url.endswith('.xml') or '<xml>' in response or '<dir>' in response or '<item>' in response:
            response = response.replace('&','&amp;').replace("'",'&apos;').replace('"','&quot;')
            if '</layouttype>' in response:
                response = response.split('</layouttype>')[1].strip()
            elif "<?xml" in response:           
                import re
                reg1 = '(<\?)(.+?)(\?>)' 
                reg2 = '(<layou[tt|t]ype)(.+?)(<\/layou[tt|t]ype>)'  
                reg3 = '(<\!-)(.+?)(->)'    
                reg_list = [reg1, reg2, reg3] 
                response1 = response
            
                for reg in reg_list :
                    dBlock = re.compile(reg,re.DOTALL).findall(response1)
                    for d in dBlock : 
                        response1 = response1.replace(str(''.join(d)),'')
                response = response1
            
            _xml = ''
            try:  
                try:
                    _xml = ET.fromstring(response)
                except ET.ParseError:
                    _xml = ET.fromstringlist(["<root>", response, "</root>"])            
            except :   
                pass
            itemlist = []
            if _xml:           
                for item in _xml:
                    itemlist.append(self._handle_item(item))
                return itemlist

    def _handle_item(self, item: ET.Element) -> Dict[str, str]:
        result = {child.tag: child.text for child in item}
        if item.findall('.//sublink'):
        	result["link"] = [child.text for child in item.findall('.//sublink')]
        result["type"] = item.tag
        return _compat_link(_clean_art(result))
