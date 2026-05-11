from ..plugin import Plugin
from typing import Dict
import xml.etree.ElementTree as ET


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
                # reg2 = '(<[layouttype|layoutype])(.+?)(<\/[layouttype|layoutype]>)'
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
                # return
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
        return result