from ..plugin import Plugin
from typing import Dict, Union
import xml.etree.ElementTree as ET
import re, os, json
import xbmcaddon, xbmc
from collections import defaultdict

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *


class xml_convert(Plugin):
    name = "xml converter"
    description = "add support for incomplete xml format"
    priority = 0

    def parse_list(self, url: str, response):
        xml = ""
        jsinfo = []
        if url.endswith(".xml") or "<xml>" in response:
            if "<?xml" in response:
                reg1 = "(<\?)(.+?)(\?>)"
                reg2 = "(<layou[tt|t]ype)(.+?)(<\/layou[tt|t]ype>)"
                # reg2 = '(<[layouttype|layoutype])(.+?)(<\/[layouttype|layoutype]>)'
                reg3 = "(<\!-)(.+?)(->)"
                reg_list = [reg1, reg2, reg3]
                response1 = response

                for reg in reg_list:
                    dBlock = re.compile(reg, re.DOTALL).findall(response1)
                    for d in dBlock:
                        response1 = response1.replace(str("".join(d)), "")
                        response = response1

            this_list = []
            this_xml = []
            fixed_list = []
            this_info = ""

            list_pattern = re.compile(
                "((?:<item>.+?</item>|<dir>.+?</dir>|<plugin>.+?</plugin>|<f4m>.+?</f4m>"
                "|<info>.+?</info>|"
                "<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail>"
                "<mode>[^<]+</mode>|"
                "<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail>"
                "<date>[^<]+</date>))",
                re.MULTILINE | re.DOTALL,
            )

            this_info = ""
            regex = "<%s>(.+?)<\/%s>"

            tag_list = [
                "airtable",
                "name",
                "title",
                "link",
                "thumbnail",
                "tmdb_id",
                "fanart",
                "meta",
                "sublink",
                "content",
                "imdb",
                "title",
                "tvshowtitle",
                "year",
                "summary",
                "season",
                "episode",
                "genre",
                "animated_thumbnail",
                "animated_fanart",
            ]

            # jsdata = {'items' : []}
            # jsinfo = []

            myData = list_pattern.findall(response)

            for md in myData:
                idict = {"link": ""}
                if "item" in md:
                    this_item = "item"
                elif "dir" in md:
                    this_item = "dir"
                elif "plugin" in md:
                    this_item = "plugin"
                else:
                    this_item = "unknown"
                    
                idict.update({"type": this_item})

                for tag in tag_list:
                    t = ""
                    t1 = re.findall(regex % (tag, tag), md, re.MULTILINE | re.DOTALL)
                    t = "".join(
                        re.findall(regex % (tag, tag), md, re.MULTILINE | re.DOTALL)
                    )
                    if t:
                        if tag == "link" and "sublink" in t:
                            subs = re.findall(
                                regex % ("sublink", "sublink"),
                                md,
                                re.MULTILINE | re.DOTALL,
                            )
                            idict.update({"link": subs})

                        elif tag == "link" and not "sublink" in t:
                            idict.update({"link": t})
                        elif tag == "title":
                            if len(t1) > 1:
                                idict.update({"title": str(t1[0])})
                            else:
                                idict.update({"title": t})

                        elif tag == "name":
                            idict.update({"title": t})
                        elif tag == "meta":
                            pass
                        elif tag == "sublink":
                            pass
                        else:
                            idict.update({tag: t})

                    else:
                        pass

                jsinfo.append(idict)

        # jsdata = {'items' : []}
        # for i in jsinfo :
        # jsdata['items'].append(i)

        return jsinfo
