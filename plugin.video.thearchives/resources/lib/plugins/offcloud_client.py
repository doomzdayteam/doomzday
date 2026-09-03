"""Updated Offcloud API client used by The Archives' debrid resolver."""

BASE_URL = "https://offcloud.com/api/"


class OffcloudError(Exception):
    pass


def _raise_for_error(payload):
    if not isinstance(payload, dict):
        return
    error = payload.get("error")
    if error:
        if isinstance(error, dict):
            error = error.get("message") or error.get("detail") or str(error)
        raise OffcloudError(str(error))
    unavailable = payload.get("not_available")
    if unavailable:
        raise OffcloudError("Offcloud request unavailable: %s" % unavailable)


def api_request(requests_module, method, endpoint, api_key, data=None, json_data=None, timeout=20):
    """Call Offcloud's current bearer-key API and return its JSON body."""
    api_key = (api_key or "").strip()
    if not api_key:
        raise OffcloudError("Offcloud API key is missing.")
    url = BASE_URL + endpoint.lstrip("/")
    try:
        response = requests_module.request(
            method.upper(), url, data=data, json=json_data,
            headers={"Authorization": "Bearer %s" % api_key}, timeout=timeout
        )
    except Exception as exc:
        raise OffcloudError("Offcloud API request failed: %s" % exc)
    try:
        payload = response.json()
    except Exception as exc:
        raise OffcloudError("Offcloud returned a non-JSON response: %s" % exc)
    if getattr(response, "status_code", 200) >= 400:
        if isinstance(payload, dict):
            _raise_for_error(payload)
        raise OffcloudError("Offcloud API request failed (HTTP %s)." % response.status_code)
    _raise_for_error(payload)
    return payload


def verify_api_key(requests_module, api_key):
    """Verify the end-user Offcloud access key held in Kodi settings."""
    return api_request(requests_module, "get", "account/info", api_key, timeout=20)


def check_cache(requests_module, api_key, hashes, timeout=20):
    hashes = [str(value).strip().lower() for value in hashes or [] if value]
    if not hashes:
        return {}
    return api_request(
        requests_module, "post", "cache", api_key, json_data={"hashes": hashes}, timeout=timeout
    )


def cached_hashes(requests_module, api_key, hashes, timeout=20):
    payload = check_cache(requests_module, api_key, hashes, timeout=timeout)
    values = payload.get("cachedItems") or [] if isinstance(payload, dict) else []
    cached = set()
    for value in values:
        if isinstance(value, dict):
            value = value.get("hash") or value.get("infoHash") or value.get("id")
        if value:
            cached.add(str(value).strip().lower())
    return cached


def add_cloud(requests_module, api_key, url, timeout=30):
    if not url:
        raise OffcloudError("Offcloud magnet URL is missing.")
    return api_request(requests_module, "post", "cloud", api_key, {"url": url}, timeout=timeout)


def cache_download(requests_module, api_key, url, timeout=30):
    if not url:
        raise OffcloudError("Offcloud magnet URL is missing.")
    return api_request(
        requests_module, "post", "cache/download", api_key, json_data={"url": url}, timeout=timeout
    )


def cloud_status(requests_module, api_key, request_id, timeout=20):
    if not request_id:
        raise OffcloudError("Offcloud request ID is missing.")
    return api_request(
        requests_module, "post", "cloud/status", api_key, {"requestId": request_id}, timeout=timeout
    )


def explore_cloud(requests_module, api_key, request_id, timeout=20):
    if not request_id:
        return []
    payload = api_request(requests_module, "get", "cloud/explore/%s" % request_id, api_key, timeout=timeout)
    if isinstance(payload, list):
        return payload
    # The documented response is a list, but accept the current API's common
    # wrapper shapes as well.  This keeps the resolver focused on file links.
    if isinstance(payload, dict):
        for key in ("files", "items", "links", "results", "downloads"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        if payload.get("url") or payload.get("link"):
            return [payload]
    return []


def cloud_history(requests_module, api_key, timeout=20):
    payload = api_request(requests_module, "get", "cloud/history", api_key, timeout=timeout)
    return payload if isinstance(payload, list) else []
