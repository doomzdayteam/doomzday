import json
import random
import re
import sys
from typing import Dict, List, Optional
from urllib.parse import parse_qs, quote, unquote, urlparse

import xbmc
import xbmcgui
from xbmcaddon import Addon

from ..DI import DI
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_music_info


addon = Addon()
FANART = addon.getAddonInfo("fanart")
addon_id = addon.getAddonInfo("id")
default_icon = Addon(addon_id).getAddonInfo("icon")


class RadioBrowser(Plugin):
    name = "radio_browser"
    priority = 1100

    def __init__(self):
        self.session = DI.session
        self.public_base = "https://www.radio-browser.info"
        self.route_base = f"{self.public_base}/thearchives"
        self.default_api_base = "https://de1.api.radio-browser.info"
        self.user_agent = self._user_agent()
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        self._api_base_cache = None

    def get_list(self, url):
        if not self._owns_url(url):
            return

        if self._is_root_url(url):
            return json.dumps({"kind": "root"})

        route = self._route(url)

        if route == "/search":
            query = self.from_keyboard()
            if not query:
                sys.exit()
            stations = self._search_stations({"name": query, "order": "votes", "reverse": "true"})
            return json.dumps({"kind": "stations", "title": f"Search: {query}", "stations": stations})

        if route == "/top-clicked":
            return self._station_response("Top Clicked", "/json/stations/topclick/100")

        if route == "/top-voted":
            return self._station_response("Top Voted", "/json/stations/topvote/100")

        if route == "/recent-clicked":
            return self._station_response("Recently Clicked", "/json/stations/lastclick/100")

        if route == "/recent-changed":
            return self._station_response("Recently Changed", "/json/stations/lastchange/100")

        if route == "/countries":
            countries = self._api_get_json(
                "/json/countries",
                {"hidebroken": "true", "order": "stationcount", "reverse": "true", "limit": 300},
            )
            return json.dumps({"kind": "countries", "countries": countries or []})

        if route.startswith("/country/"):
            code = unquote(route.rsplit("/", 1)[-1]).upper()
            name = self._query_value(url, "name") or code
            stations = self._search_stations({"countrycode": code, "order": "clickcount", "reverse": "true"})
            return json.dumps({"kind": "stations", "title": name, "stations": stations})

        if route == "/tags":
            tags = self._api_get_json(
                "/json/tags",
                {"hidebroken": "true", "order": "stationcount", "reverse": "true", "limit": 300},
            )
            return json.dumps({"kind": "tags", "tags": tags or []})

        if route.startswith("/tag/"):
            tag = unquote(route.rsplit("/", 1)[-1])
            stations = self._search_stations({"tag": tag, "order": "clickcount", "reverse": "true"})
            return json.dumps({"kind": "stations", "title": tag, "stations": stations})

        if route == "/languages":
            languages = self._api_get_json(
                "/json/languages",
                {"hidebroken": "true", "order": "stationcount", "reverse": "true", "limit": 300},
            )
            return json.dumps({"kind": "languages", "languages": languages or []})

        if route.startswith("/language/"):
            language = unquote(route.rsplit("/", 1)[-1])
            stations = self._search_stations({"language": language, "order": "clickcount", "reverse": "true"})
            return json.dumps({"kind": "stations", "title": language, "stations": stations})

        if route.startswith("/station/"):
            stationuuid = unquote(route.rsplit("/", 1)[-1])
            stations = self._api_get_json("/json/stations/byuuid", {"uuids": stationuuid})
            return json.dumps({"kind": "stations", "title": "Station", "stations": stations or []})

        return json.dumps({"kind": "root"})

    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not self._owns_url(url):
            return

        try:
            data = json.loads(response or "{}")
        except (TypeError, json.JSONDecodeError):
            return [self._message_item("[COLOR grey]Radio Browser did not return valid data[/COLOR]")]

        kind = data.get("kind")

        if kind == "root":
            return [
                self._dir("[COLOR deepskyblue]Search Stations[/COLOR]", self._link("search")),
                self._dir("Top Clicked", self._link("top-clicked")),
                self._dir("Top Voted", self._link("top-voted")),
                self._dir("Recently Clicked", self._link("recent-clicked")),
                self._dir("Recently Changed", self._link("recent-changed")),
                self._dir("Browse Countries", self._link("countries")),
                self._dir("Browse Tags", self._link("tags")),
                self._dir("Browse Languages", self._link("languages")),
            ]

        if kind == "countries":
            items = []
            for country in data.get("countries") or []:
                code = (country.get("iso_3166_1") or "").upper()
                name = country.get("name") or code
                if not code or not name:
                    continue
                title = self._count_title(name, country.get("stationcount"))
                items.append(self._dir(title, self._link(f"country/{quote(code, safe='')}?name={quote(name)}")))
            return items or [self._message_item("[COLOR grey]No countries found[/COLOR]")]

        if kind == "tags":
            return self._named_count_dirs(data.get("tags") or [], "tag", "No tags found")

        if kind == "languages":
            return self._named_count_dirs(data.get("languages") or [], "language", "No languages found")

        if kind == "stations":
            stations = data.get("stations") or []
            return self._stations_to_items(stations) or [
                self._message_item("[COLOR grey]No playable stations found[/COLOR]")
            ]

        return [self._message_item("[COLOR grey]Radio Browser route not recognized[/COLOR]")]

    def play_video(self, item) -> Optional[bool]:
        try:
            if isinstance(item, bytes):
                item = item.decode("utf-8")
            data = json.loads(item)
        except (TypeError, AttributeError, json.JSONDecodeError):
            if isinstance(item, str) and self._is_station_url(item):
                data = {"link": item, "stationuuid": self._station_uuid_from_url(item)}
            else:
                return

        stationuuid = data.get("stationuuid") or self._station_uuid_from_url(data.get("link", ""))
        link = data.get("link", "")
        if not stationuuid and not self._is_station_url(link):
            return

        stream_url = self._click_station(stationuuid) if stationuuid else ""
        if not stream_url:
            stream_url = data.get("stream_url") or data.get("url_resolved") or data.get("url") or ""

        if not stream_url:
            xbmc.log(f"[RadioBrowser] No stream URL for {stationuuid or link}", xbmc.LOGWARNING)
            return

        title = self._clean_title(data.get("title") or data.get("name") or "Radio")
        thumbnail = data.get("thumbnail") or default_icon
        summary = data.get("summary") or ""

        liz = xbmcgui.ListItem(title, path=stream_url)
        set_music_info(liz, {"title": title, "plot": summary})
        liz.setArt({"thumb": thumbnail, "icon": thumbnail, "fanart": FANART})
        liz.setProperty("IsPlayable", "true")
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass
        xbmc.Player().play(stream_url, liz)
        return True

    def _station_response(self, title: str, path: str) -> str:
        stations = self._api_get_json(path, {"hidebroken": "true"})
        return json.dumps({"kind": "stations", "title": title, "stations": stations or []})

    def _search_stations(self, params: Dict[str, str]) -> list:
        clean_params = {
            "hidebroken": "true",
            "limit": 100,
            "offset": 0,
        }
        clean_params.update(params)
        stations = self._api_get_json("/json/stations/search", clean_params)
        return stations or []

    def _api_get_json(self, path: str, params: Optional[Dict[str, str]] = None):
        errors = []
        for base_url in self._api_bases():
            try:
                response = self.session.get(
                    f"{base_url}{path}",
                    params=params or {},
                    headers=self.headers,
                    timeout=15,
                )
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                errors.append(f"{base_url}: {exc}")
        xbmc.log(f"[RadioBrowser] API request failed for {path}: {'; '.join(errors)}", xbmc.LOGERROR)
        return None

    def _api_bases(self) -> list:
        if self._api_base_cache:
            return self._api_base_cache

        bases = [self.default_api_base]
        try:
            response = self.session.get(
                f"{self.default_api_base}/json/servers",
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            names = []
            for server in response.json() or []:
                name = server.get("name") if isinstance(server, dict) else ""
                if name:
                    names.append(f"https://{name}")
            random.shuffle(names)
            bases = self._unique(names + bases)
        except Exception as exc:
            xbmc.log(f"[RadioBrowser] Server mirror lookup failed: {exc}", xbmc.LOGWARNING)

        self._api_base_cache = bases
        return bases

    def _click_station(self, stationuuid: str) -> str:
        if not stationuuid:
            return ""
        result = self._api_get_json(f"/json/url/{quote(stationuuid, safe='')}")
        if isinstance(result, dict) and str(result.get("ok", "")).lower() == "true":
            return result.get("url") or ""
        return ""

    def _stations_to_items(self, stations: list) -> list:
        items = []
        seen = set()
        for station in stations:
            if not isinstance(station, dict):
                continue
            stationuuid = station.get("stationuuid") or ""
            title = station.get("name") or ""
            stream_url = station.get("url_resolved") or station.get("url") or ""
            if not stationuuid or not title or not stream_url:
                continue
            if stationuuid in seen:
                continue
            seen.add(stationuuid)

            details = []
            codec = station.get("codec") or ""
            bitrate = station.get("bitrate") or 0
            country = station.get("countrycode") or ""
            tags = self._first_values(station.get("tags"), 2)
            if codec:
                details.append(str(codec).upper())
            if bitrate:
                details.append(f"{bitrate} kbps")
            if country:
                details.append(str(country).upper())
            details.extend(tags)

            display_title = title
            if details:
                display_title = f"{title}  [COLOR gray]({' | '.join(details)})[/COLOR]"

            summary_parts = []
            if station.get("homepage"):
                summary_parts.append(station.get("homepage"))
            if station.get("language"):
                summary_parts.append(f"Language: {station.get('language')}")
            if station.get("tags"):
                summary_parts.append(f"Tags: {station.get('tags')}")

            items.append(
                {
                    "type": "item",
                    "title": display_title,
                    "link": self._link(f"station/{quote(stationuuid, safe='')}"),
                    "thumbnail": station.get("favicon") or "",
                    "summary": "\n".join(summary_parts),
                    "stationuuid": stationuuid,
                    "stream_url": stream_url,
                    "is_playable": "true",
                }
            )
        return items

    def _named_count_dirs(self, rows: list, route_name: str, empty_text: str) -> list:
        items = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = row.get("name") or ""
            if not name:
                continue
            items.append(
                self._dir(
                    self._count_title(name, row.get("stationcount")),
                    self._link(f"{route_name}/{quote(name, safe='')}"),
                )
            )
        return items or [self._message_item(f"[COLOR grey]{empty_text}[/COLOR]")]

    def _dir(self, title: str, link: str) -> Dict[str, str]:
        return {
            "type": "dir",
            "title": title,
            "link": link,
        }

    def _message_item(self, title: str) -> Dict[str, str]:
        return {
            "type": "dir",
            "title": title,
            "link": self.route_base,
        }

    def _link(self, route: str) -> str:
        return f"{self.route_base}/{route.lstrip('/')}"

    def _owns_url(self, url: str) -> bool:
        return "radio-browser.info" in str(url or "").lower()

    def _is_root_url(self, url: str) -> bool:
        parsed = urlparse(str(url or ""))
        path = parsed.path.rstrip("/")
        return path in ("", "/thearchives")

    def _is_station_url(self, url: str) -> bool:
        return self._owns_url(url) and self._route(url).startswith("/station/")

    def _station_uuid_from_url(self, url: str) -> str:
        if not self._is_station_url(url):
            return ""
        return unquote(self._route(url).rsplit("/", 1)[-1])

    def _route(self, url: str) -> str:
        parsed = urlparse(str(url or ""))
        path = parsed.path.rstrip("/")
        if path.startswith("/thearchives"):
            path = path[len("/thearchives"):]
        return path or "/"

    def _query_value(self, url: str, name: str) -> str:
        values = parse_qs(urlparse(str(url or "")).query).get(name)
        return unquote(values[0]) if values else ""

    def _count_title(self, name: str, count) -> str:
        try:
            count_int = int(count)
        except (TypeError, ValueError):
            count_int = 0
        if count_int:
            return f"{name} [COLOR gray]({count_int})[/COLOR]"
        return name

    def _first_values(self, value: str, limit: int) -> list:
        values = []
        for part in str(value or "").split(","):
            part = part.strip()
            if part:
                values.append(part)
            if len(values) >= limit:
                break
        return values

    def _clean_title(self, value: str) -> str:
        return re.sub(r"\[/?COLOR[^\]]*\]", "", str(value or "")).strip()

    def _unique(self, values: list) -> list:
        result = []
        for value in values:
            if value and value not in result:
                result.append(value)
        return result

    def _user_agent(self) -> str:
        try:
            version = addon.getAddonInfo("version") or "0"
        except Exception:
            version = "0"
        return f"The Archives/{version} ({addon_id}; Kodi)"

    def from_keyboard(self, default_text="", header="Search Stations"):
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
