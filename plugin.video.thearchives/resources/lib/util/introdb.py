import time


API_URL = "https://api.theintrodb.org/v3/media"
REQUEST_TIMEOUT = 8
MIN_REQUEST_GAP = 0.4
_last_request_at = 0.0


def _positive_int(value):
    try:
        value = int(str(value).strip())
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None


def _imdb_id(value):
    value = str(value or "").strip()
    return value if value.startswith("tt") and value[2:].isdigit() else None


def build_query(item, duration_ms=None):
    item = item or {}
    content = str(item.get("content") or "").lower()
    params = {}
    if content == "episode":
        tmdb_id = _positive_int(item.get("tv_show_tmdb_id"))
        season = _positive_int(item.get("season"))
        episode = _positive_int(item.get("episode"))
        if not season or not episode:
            return None
        params.update({"season": season, "episode": episode})
    elif content == "movie":
        tmdb_id = _positive_int(item.get("tmdb_id") or item.get("tmdb"))
    else:
        return None

    if tmdb_id:
        params["tmdb_id"] = tmdb_id
    else:
        imdb_id = _imdb_id(item.get("imdb_id") or item.get("imdb"))
        if not imdb_id:
            return None
        params["imdb_id"] = imdb_id

    duration = _positive_int(duration_ms)
    if duration:
        params["duration_ms"] = duration
    return params


def _segments(segment_type, values):
    normalized = []
    for value in values or []:
        if not isinstance(value, dict):
            continue
        start_ms = value.get("start_ms")
        end_ms = value.get("end_ms")
        if segment_type == "intro":
            start_ms = 0 if start_ms is None else start_ms
            if end_ms is None:
                continue
        elif segment_type == "credits":
            if start_ms is None:
                continue
        else:
            continue
        try:
            start = max(0.0, float(start_ms) / 1000.0)
            end = None if end_ms is None else max(0.0, float(end_ms) / 1000.0)
        except (TypeError, ValueError):
            continue
        if end is not None and end <= start:
            continue
        normalized.append({"start": start, "end": end, "type": segment_type})
    return sorted(normalized, key=lambda segment: segment["start"])


def lookup_segments(item, duration_ms=None, http_get=None, now=None, sleep=None):
    global _last_request_at

    params = build_query(item, duration_ms)
    if not params:
        return {}
    if http_get is None:
        try:
            import requests

            http_get = requests.get
        except Exception:
            return {}
    now = now or time.monotonic
    sleep = sleep or time.sleep
    gap = now() - _last_request_at
    if gap < MIN_REQUEST_GAP:
        sleep(MIN_REQUEST_GAP - gap)
    try:
        response = http_get(
            API_URL,
            params=params,
            headers={"Accept": "application/json", "User-Agent": "TheArchives Kodi Addon"},
            timeout=REQUEST_TIMEOUT,
        )
        _last_request_at = now()
        if getattr(response, "status_code", None) != 200:
            return {}
        data = response.json()
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        "intro": _segments("intro", data.get("intro")),
        "credits": _segments("credits", data.get("credits")),
    }
