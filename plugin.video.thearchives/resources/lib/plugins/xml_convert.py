from ..plugin import Plugin
from typing import Dict, Union
from urllib.parse import quote
import xml.etree.ElementTree as ET
import re, os, json
import xbmcaddon, xbmc
from collections import defaultdict

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *


DEAD_ART_HOSTS = ("miniaturelife67.co.uk",)


def _clean_art(item):
    for key in ("thumbnail", "fanart", "animated_thumbnail", "animated_fanart"):
        value = str(item.get(key) or "")
        if any(host in value.lower() for host in DEAD_ART_HOSTS):
            item[key] = ""
    return item


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


def _compat_link(item):
    if item.get("link"):
        return item
    tmdb = (item.get("tmdb") or "").strip()
    title = _clean_title(item.get("title") or item.get("name"))
    if tmdb.startswith("list/") and title:
        item["link"] = f"tmdb/legacy_list/{tmdb.split('/', 1)[1]}/{quote(title, safe='')}"
        return item
    for key, prefix in (("tmdb", "tmdb"), ("trakt", "trakt")):
        route = _route_link(prefix, item.get(key))
        if route:
            item["link"] = route
            return item
    for key in ("url", "path", "custom"):
        value = (item.get(key) or "").strip()
        if value:
            item["link"] = value
            return item
    return item


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
                "tmdb",
                "trakt",
                "url",
                "path",
                "custom",
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

                idict = _compat_link(_clean_art(idict))
                jsinfo.append(idict)


        return jsinfo
