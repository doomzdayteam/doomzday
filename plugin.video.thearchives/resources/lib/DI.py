import sqlite3
import time
from typing import Optional
import requests
import routing
import xbmc
import xbmcaddon
import json


class _DB:
    def __init__(self):
        if not xbmcaddon.Addon().getSettingBool("use_cache"):
            return
        self.db = xbmcaddon.Addon().getAddonInfo("path") + "/cache.db"
        self.cache_timer =  float(xbmcaddon.Addon().getSetting("time_cache") or 0)
        try:
            self.con = sqlite3.connect(self.db)
            self.cursor = self.con.cursor()
            self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS cache(url text PRIMARY KEY, response text, created int)"
        )
            self.con.commit()
        except sqlite3.Error as e:
            xbmc.log(f"Failed to write data to the sqlite table: {e}", xbmc.LOGINFO)
        finally:
            if self.con:
                self.close()

    def set(self, url: str, response: str) -> None:
        if url.startswith("m3u"):
            url = url.split("|")[1]
        created = time.time()
        cached = self.get(url)
        if cached:
            c_resp, c_created = cached
            try:
                if (c_created + json.loads(c_resp).get("cache_time", self.cache_timer)*60) > created:
                    created = c_created
            except json.decoder.JSONDecodeError as e:
                xbmc.log(f'Json Error: {e}', xbmc.LOGINFO)
                if (c_created + self.cache_timer*60) > created:
                    created = c_created

        try:
            self.con = sqlite3.connect(self.db)
            self.cursor = self.con.cursor()
            self.cursor.execute(
                """INSERT OR REPLACE INTO cache(url, response, created) VALUES(?, ?, ?);
""",
                (url, response, created),
            )
            self.con.commit()
        except sqlite3.Error as e:
            xbmc.log(f"Failed to write data to the sqlite table: {e}", xbmc.LOGINFO)
        finally:
            if self.con:
                self.close()

    def get(self, url: str) -> Optional[str]:
        response = None
        if url.startswith("m3u"):
            url = url.split("|")[1]
        try:
            self.con = sqlite3.connect(self.db)
            self.cursor = self.con.cursor()
            self.cursor.execute(
                """SELECT response, created FROM cache WHERE url = ?""", (url,)
            )
            response = self.cursor.fetchone()
        except sqlite3.Error as e:
            xbmc.log(f"Failed to read data from the sqlite table: {e}", xbmc.LOGINFO)
        finally:
            if self.con:
                self.con.close()
        return response

    def close(self) -> None:
        self.con.close()
    
    def clear_cache(self) -> None:
        from xbmcgui import Dialog
        dialog = Dialog()
        if not xbmcaddon.Addon().getSettingBool("use_cache"):       
            dialog.ok("Clear Cache", "Cache not in use.\nNothing Cleared.")
            return
        clear = dialog.yesno("Clear Cache", "Do You Wish to Clear Addon Cache?")
        if clear:
            try:
                self.con = sqlite3.connect(self.db)
                self.cursor = self.con.cursor()
                self.cursor.execute('DELETE FROM cache;',)
                self.con.commit()
            except sqlite3.Error as e:
                xbmc.log(f"Failed to delete data from the sqlite table: {e}", xbmc.LOGINFO)
                dialog.ok("Clear Cache", "There was a problem clearing cache.\nCheck the log for details.")
                return
            finally:
                if self.con:
                    self.close()
            try:
                self.con = sqlite3.connect(self.db)
                self.cursor = self.con.cursor()
                self.cursor.execute('VACUUM;',)
                self.con.commit()
            except sqlite3.Error as e:
                xbmc.log(f"Failed to vacuum data from the sqlite table: {e}", xbmc.LOGINFO)
            finally:
                if self.con:
                    self.close()
        dialog.notification(xbmcaddon.Addon().getAddonInfo("name"), 'Cache Cleared', xbmcaddon.Addon().getAddonInfo("icon"), 3000, sound=False)
        return


class DI:
    session = requests.Session()
    db = _DB()

    @property
    def plugin(self):
        try:
            return routing.Plugin()
        except AttributeError:
            from routing.routing import Plugin

            return Plugin()


DI = DI()
