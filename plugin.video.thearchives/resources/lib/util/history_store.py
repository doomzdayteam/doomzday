import base64
import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _content_type(item):
    content = _clean(item.get("content")).lower()
    if content == "tv":
        return "tvshow"
    if content:
        return content
    return "video"


def make_item_key(item):
    content = _content_type(item)
    tmdb_id = _clean(item.get("tmdb_id") or item.get("tmdb"))
    imdb_id = _clean(item.get("imdb_id") or item.get("imdb"))

    if content == "episode":
        season = _clean(item.get("season"))
        episode = _clean(item.get("episode"))
        show_id = _clean(item.get("show_tmdb_id") or item.get("tvshow_tmdb_id") or tmdb_id or imdb_id)
        if show_id and season and episode:
            return "episode:%s:%s:%s" % (show_id, season, episode)

    if tmdb_id:
        return "%s:%s" % (content, tmdb_id)
    if imdb_id:
        return "%s:imdb:%s" % (content, imdb_id)

    fallback = "%s|%s|%s" % (content, _clean(item.get("title")), _clean(item.get("link")))
    digest = hashlib.sha1(fallback.encode("utf-8")).hexdigest()
    return "%s:%s" % (content, digest)


def encode_item(item):
    data = json.dumps(item, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("ascii")


def decode_item(payload, raw=False):
    decoded = base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8")
    if raw:
        return decoded
    return json.loads(decoded)


def default_db_path():
    try:
        import xbmcaddon
        import xbmcvfs

        addon = xbmcaddon.Addon()
        profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        if not os.path.exists(profile):
            os.makedirs(profile)
        return os.path.join(profile, "private_history.db")
    except Exception:
        return os.path.join(os.getcwd(), "private_history.db")


class HistoryStore:
    def __init__(self, db_path=None):
        self.db_path = db_path or default_db_path()
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self):
        folder = os.path.dirname(self.db_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)
        with closing(self._connect()) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS history_items (
                    item_key TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    item_json TEXT NOT NULL,
                    favorite INTEGER NOT NULL DEFAULT 0,
                    watched INTEGER NOT NULL DEFAULT 0,
                    resume_point REAL NOT NULL DEFAULT 0,
                    curr_time REAL NOT NULL DEFAULT 0,
                    total_time REAL NOT NULL DEFAULT 0,
                    updated REAL NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS recent_searches (
                    media_type TEXT NOT NULL,
                    query TEXT NOT NULL COLLATE NOCASE,
                    updated REAL NOT NULL,
                    PRIMARY KEY (media_type, query)
                )
                """
            )
            con.commit()

    def _upsert_item(self, item):
        item_key = make_item_key(item)
        now = time.time()
        title = _clean(item.get("title") or item.get("name"))
        content = _content_type(item)
        item_json = json.dumps(item, sort_keys=True)
        with closing(self._connect()) as con:
            con.execute(
                """
                INSERT OR IGNORE INTO history_items
                    (item_key, title, content, item_json, updated)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_key, title, content, item_json, now),
            )
            con.execute(
                """
                UPDATE history_items
                SET title = ?, content = ?, item_json = ?, updated = ?
                WHERE item_key = ?
                """,
                (title, content, item_json, now, item_key),
            )
            con.commit()
        return item_key

    def get_state(self, item_or_key):
        item_key = item_or_key if isinstance(item_or_key, str) else make_item_key(item_or_key)
        with closing(self._connect()) as con:
            row = con.execute(
                """
                SELECT favorite, watched, resume_point, curr_time, total_time
                FROM history_items
                WHERE item_key = ?
                """,
                (item_key,),
            ).fetchone()
        if not row:
            return {
                "favorite": False,
                "watched": False,
                "resume_point": 0.0,
                "curr_time": 0.0,
                "total_time": 0.0,
            }
        favorite, watched, resume_point, curr_time, total_time = row
        return {
            "favorite": bool(favorite),
            "watched": bool(watched),
            "resume_point": float(resume_point or 0),
            "curr_time": float(curr_time or 0),
            "total_time": float(total_time or 0),
        }

    def toggle_favorite(self, item):
        item_key = self._upsert_item(item)
        new_value = 0 if self.get_state(item_key)["favorite"] else 1
        with closing(self._connect()) as con:
            con.execute(
                "UPDATE history_items SET favorite = ?, updated = ? WHERE item_key = ?",
                (new_value, time.time(), item_key),
            )
            con.commit()
        return bool(new_value)

    def set_favorite(self, item, enabled=True):
        item_key = self._upsert_item(item)
        new_value = 1 if enabled else 0
        with closing(self._connect()) as con:
            con.execute(
                "UPDATE history_items SET favorite = ?, updated = ? WHERE item_key = ?",
                (new_value, time.time(), item_key),
            )
            con.commit()
        return bool(new_value)

    def mark_watched(self, item):
        item_key = self._upsert_item(item)
        with closing(self._connect()) as con:
            con.execute(
                """
                UPDATE history_items
                SET watched = 1, resume_point = 0, curr_time = 0, total_time = 0, updated = ?
                WHERE item_key = ?
                """,
                (time.time(), item_key),
            )
            con.commit()

    def mark_unwatched(self, item):
        item_key = self._upsert_item(item)
        with closing(self._connect()) as con:
            con.execute(
                "UPDATE history_items SET watched = 0, updated = ? WHERE item_key = ?",
                (time.time(), item_key),
            )
            con.commit()

    def clear_progress(self, item):
        item_key = self._upsert_item(item)
        with closing(self._connect()) as con:
            con.execute(
                """
                UPDATE history_items
                SET resume_point = 0, curr_time = 0, total_time = 0, updated = ?
                WHERE item_key = ?
                """,
                (time.time(), item_key),
            )
            con.commit()

    def set_progress(self, item, curr_time, total_time):
        try:
            curr_time = float(curr_time)
            total_time = float(total_time)
        except (TypeError, ValueError):
            return
        if total_time <= 0:
            return

        self._upsert_item(item)
        resume_point = round(max(0.0, min(100.0, (curr_time / total_time) * 100.0)), 1)
        if resume_point >= 90.0:
            self.mark_watched(item)
            return
        if resume_point < 5.0:
            return

        item_key = make_item_key(item)
        with closing(self._connect()) as con:
            con.execute(
                """
                UPDATE history_items
                SET watched = 0, resume_point = ?, curr_time = ?, total_time = ?, updated = ?
                WHERE item_key = ?
                """,
                (resume_point, curr_time, total_time, time.time(), item_key),
            )
            con.commit()

    def list_items(self, kind):
        clauses = {
            "favorite": "favorite = 1",
            "progress": "resume_point > 0 AND watched = 0",
            "watched": "watched = 1",
        }
        clause = clauses[kind]
        with closing(self._connect()) as con:
            rows = con.execute(
                "SELECT item_json FROM history_items WHERE %s ORDER BY updated DESC" % clause
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_recent_search(self, media_type, query, limit=20):
        media_type = _clean(media_type).lower()
        query = _clean(query)
        if media_type not in ("movie", "tv") or not query:
            return
        now = max(time.time(), getattr(self, "_recent_search_updated", 0) + 0.000001)
        self._recent_search_updated = now
        with closing(self._connect()) as con:
            con.execute(
                """
                INSERT INTO recent_searches (media_type, query, updated)
                VALUES (?, ?, ?)
                ON CONFLICT(media_type, query) DO UPDATE SET
                    query = excluded.query,
                    updated = excluded.updated
                """,
                (media_type, query, now),
            )
            rows = con.execute(
                """
                SELECT query FROM recent_searches
                WHERE media_type = ?
                ORDER BY updated DESC
                LIMIT -1 OFFSET ?
                """,
                (media_type, int(limit)),
            ).fetchall()
            if rows:
                con.executemany(
                    "DELETE FROM recent_searches WHERE media_type = ? AND query = ?",
                    [(media_type, row[0]) for row in rows],
                )
            con.commit()

    def list_recent_searches(self, media_type):
        media_type = _clean(media_type).lower()
        if media_type not in ("movie", "tv"):
            return []
        with closing(self._connect()) as con:
            rows = con.execute(
                """
                SELECT query FROM recent_searches
                WHERE media_type = ?
                ORDER BY updated DESC
                """,
                (media_type,),
            ).fetchall()
        return [row[0] for row in rows]

    def clear_recent_searches(self, media_type):
        media_type = _clean(media_type).lower()
        if media_type not in ("movie", "tv"):
            return
        with closing(self._connect()) as con:
            con.execute("DELETE FROM recent_searches WHERE media_type = ?", (media_type,))
            con.commit()
