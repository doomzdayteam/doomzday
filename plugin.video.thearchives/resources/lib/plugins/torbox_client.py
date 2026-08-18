# -*- coding: utf-8 -*-

BASE_URL = "https://api.torbox.app/v1/api/"


class TorBoxError(Exception):
    pass


def auth_headers(token):
    return {"Authorization": "Bearer %s" % token}


def response_data(payload):
    if not isinstance(payload, dict):
        raise TorBoxError("TorBox returned an invalid response.")
    if payload.get("success") is False:
        raise TorBoxError(payload.get("detail") or payload.get("error") or "TorBox API error.")
    return payload.get("data", payload)


def _response_data(response):
    try:
        payload = response.json()
    except Exception as exc:
        raise TorBoxError("TorBox returned an invalid response.") from exc
    data = response_data(payload)
    try:
        response.raise_for_status()
    except AttributeError:
        status_code = getattr(response, "status_code", None)
        if status_code is not None and status_code >= 400:
            raise TorBoxError("TorBox API request failed (%s)." % status_code)
    return data


def api_get(session, endpoint, token=None, params=None, timeout=20):
    headers = auth_headers(token) if token else None
    return _response_data(
        session.get(
            BASE_URL + endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    )


def api_post(session, endpoint, token=None, data=None, json=None, timeout=20):
    headers = auth_headers(token) if token else None
    return _response_data(
        session.post(
            BASE_URL + endpoint,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout,
        )
    )


def cached_torrents(session, token, hashes):
    """Return TorBox's cached entries for up to 100 torrent hashes."""
    hashes = [str(value).strip() for value in hashes or [] if value]
    if not hashes:
        return []
    return api_get(
        session,
        "torrents/checkcached",
        token,
        params={"hash": ",".join(hashes[:100]), "format": "list", "list_files": "false"},
        timeout=15,
    )


def verify_token(session, token):
    return api_get(session, "user/me", token)
