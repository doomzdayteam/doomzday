import hashlib
import json
import os
import sqlite3
import time


CATALOG_TTL = 12 * 60 * 60
SEARCH_TTL = 2 * 60 * 60


def _log(message):
    try:
        import xbmc
        xbmc.log(f"The Archives VOD cache: {message}", xbmc.LOGINFO)
    except Exception:
        pass


def _translate_path(path):
    try:
        import xbmcvfs
        if hasattr(xbmcvfs, "translatePath"):
            return xbmcvfs.translatePath(path)
        return xbmcvfs.translatePath(path)
    except Exception:
        return path


def _addon_profile_dir():
    try:
        from xbmcaddon import Addon
        profile = Addon().getAddonInfo("profile")
        if profile:
            return _translate_path(profile)
    except Exception:
        pass
    return os.path.join(os.getcwd(), "profile")


def _cache_enabled():
    try:
        from xbmcaddon import Addon
        return Addon().getSettingBool("use_cache")
    except Exception:
        return True


def _key_hash(key):
    return hashlib.sha256(str(key or "").encode("utf-8")).hexdigest()


def vod_cache_key(*parts):
    return _key_hash("|".join(str(part or "") for part in parts))


class VODCache:
    def __init__(self, root_dir=None, now_func=None, enabled=None):
        self.root_dir = root_dir or os.path.join(_addon_profile_dir(), "cache")
        self.db_path = os.path.join(self.root_dir, "vod_cache.db")
        self.now_func = now_func or time.time
        self.enabled = _cache_enabled() if enabled is None else bool(enabled)

    def ttl_for(self, kind):
        return SEARCH_TTL if kind == "search" else CATALOG_TTL

    def get_response(self, provider, key, kind="catalog"):
        return self._get(provider, "raw", key, kind)

    def set_response(self, provider, key, response, kind="catalog"):
        self._set(provider, "raw", key, kind, response)

    def get_menu(self, provider, key, kind="catalog"):
        payload = self._get(provider, "menu", key, kind)
        if payload is None:
            return None
        try:
            data = json.loads(payload)
            return data if isinstance(data, list) else None
        except (TypeError, ValueError):
            return None

    def set_menu(self, provider, key, itemlist, kind="catalog"):
        self._set(provider, "menu", key, kind, json.dumps(itemlist or [], separators=(",", ":")))

    def get_or_set_response(self, provider, key, kind, fetcher):
        cached = self.get_response(provider, key, kind)
        if cached is not None:
            return cached
        response = fetcher()
        if response is not None:
            self.set_response(provider, key, response, kind)
        return response

    def get_or_set_menu(self, provider, key, kind, builder):
        cached = self.get_menu(provider, key, kind)
        if cached is not None:
            return cached
        itemlist = builder()
        if itemlist is not None:
            self.set_menu(provider, key, itemlist, kind)
        return itemlist

    def clear(self):
        try:
            if os.path.exists(self.db_path):
                con = sqlite3.connect(self.db_path)
                try:
                    con.execute("DELETE FROM vod_cache")
                    con.commit()
                finally:
                    con.close()
        except sqlite3.Error as exc:
            _log(f"clear failed: {exc}")

    def _get(self, provider, layer, key, kind):
        if not self.enabled:
            return None
        try:
            self._ensure_db()
            con = sqlite3.connect(self.db_path)
            try:
                row = con.execute(
                    """
                    SELECT payload, created
                    FROM vod_cache
                    WHERE provider = ? AND layer = ? AND key_hash = ?
                    """,
                    (provider, layer, _key_hash(key)),
                ).fetchone()
            finally:
                con.close()
            if not row:
                return None
            payload, created = row
            if (float(created) + self.ttl_for(kind)) <= float(self.now_func()):
                return None
            return payload
        except sqlite3.Error as exc:
            _log(f"read failed: {exc}")
            return None

    def _set(self, provider, layer, key, kind, payload):
        if not self.enabled or payload is None:
            return
        try:
            self._ensure_db()
            con = sqlite3.connect(self.db_path)
            try:
                con.execute(
                    """
                    INSERT OR REPLACE INTO vod_cache
                    (provider, layer, key_hash, key, kind, payload, created)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (provider, layer, _key_hash(key), str(key or ""), kind, payload, float(self.now_func())),
                )
                con.commit()
            finally:
                con.close()
        except sqlite3.Error as exc:
            _log(f"write failed: {exc}")

    def _ensure_db(self):
        os.makedirs(self.root_dir, exist_ok=True)
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS vod_cache (
                    provider TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    key TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created REAL NOT NULL,
                    PRIMARY KEY (provider, layer, key_hash)
                )
                """
            )
            con.commit()
        finally:
            con.close()


VOD_CACHE = VODCache()
