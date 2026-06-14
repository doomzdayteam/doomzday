# -*- coding: utf-8 -*-
import base64
from xml.sax.saxutils import escape


DEFAULT_TIMEOUT = 15


class NzbClientError(Exception):
    pass


def _clean(value, default=""):
    value = str(value if value is not None else default).strip()
    return value or default


def _bool_setting(value):
    return str(value or "").strip().lower() in ("true", "1", "yes", "on")


def _base_url(value):
    url = _clean(value)
    if not url:
        return ""
    if not url.lower().startswith(("http://", "https://")):
        url = "http://" + url
    return url.rstrip("/")


def read_settings(addon):
    return {
        "enabled": _bool_setting(addon.getSetting("provider.nzb_downloader")),
        "client": _clean(addon.getSetting("nzb.client"), "sabnzbd").lower(),
        "url": _base_url(addon.getSetting("nzb.url")),
        "api_key": _clean(addon.getSetting("nzb.api_key")),
        "username": _clean(addon.getSetting("nzb.username")),
        "password": _clean(addon.getSetting("nzb.password")),
        "category": _clean(addon.getSetting("nzb.category")),
    }


def submit_nzb(settings, source, session=None, timeout=DEFAULT_TIMEOUT):
    if not settings.get("enabled", True):
        raise NzbClientError("NZB downloader is disabled")
    client = _clean(settings.get("client"), "sabnzbd").lower()
    if client in ("sab", "sabnzbd"):
        return _submit_sabnzbd(settings, source, session, timeout)
    if client in ("nzbget", "nzb-get"):
        return _submit_nzbget(settings, source, session, timeout)
    raise NzbClientError("Unsupported NZB client: %s" % client)


def _requests_session(session):
    if session is not None:
        return session
    import requests

    return requests


def _submit_sabnzbd(settings, source, session, timeout):
    base = _base_url(settings.get("url"))
    api_key = _clean(settings.get("api_key"))
    nzb_url = _clean(source.get("url") or source.get("link"))
    if not base:
        raise NzbClientError("SABnzbd URL is missing")
    if not api_key:
        raise NzbClientError("SABnzbd API key is missing")
    if not nzb_url:
        raise NzbClientError("NZB URL is missing")

    params = {
        "mode": "addurl",
        "output": "json",
        "apikey": api_key,
        "name": nzb_url,
        "nzbname": _clean(source.get("name") or source.get("title"), "The Archives NZB"),
    }
    category = _clean(settings.get("category"))
    if category:
        params["cat"] = category
    response = _requests_session(session).get(base + "/api", params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") is False:
        raise NzbClientError("SABnzbd rejected the NZB")
    ids = payload.get("nzo_ids") or []
    return {"ok": True, "client": "sabnzbd", "id": ids[0] if ids else ""}


def _submit_nzbget(settings, source, session, timeout):
    base = _base_url(settings.get("url"))
    if not base:
        raise NzbClientError("NZBGet URL is missing")
    nzb_content = source.get("nzb_content")
    if not nzb_content:
        nzb_content = _download_nzb(source, session, timeout)
    if isinstance(nzb_content, str):
        nzb_content = nzb_content.encode("utf-8")

    name = _clean(source.get("name") or source.get("title"), "The Archives NZB")
    category = _clean(settings.get("category"))
    payload = _xmlrpc_append_payload(name, nzb_content, category)
    headers = {"Content-Type": "text/xml"}
    auth = _basic_auth(settings.get("username"), settings.get("password"))
    if auth:
        headers["Authorization"] = auth
    response = _requests_session(session).post(base + "/xmlrpc", data=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    return {"ok": True, "client": "nzbget", "id": ""}


def _download_nzb(source, session, timeout):
    url = _clean(source.get("url") or source.get("link"))
    if not url:
        raise NzbClientError("NZB URL is missing")
    response = _requests_session(session).get(url, timeout=timeout)
    response.raise_for_status()
    return getattr(response, "content", b"")


def _basic_auth(username, password):
    username = _clean(username)
    password = _clean(password)
    if not username and not password:
        return ""
    token = base64.b64encode(("%s:%s" % (username, password)).encode("utf-8")).decode("ascii")
    return "Basic " + token


def _xmlrpc_append_payload(name, nzb_content, category):
    encoded = base64.b64encode(nzb_content or b"").decode("ascii")
    return """<?xml version="1.0"?>
<methodCall>
  <methodName>append</methodName>
  <params>
    <param><value><string>%s</string></value></param>
    <param><value><string>%s</string></value></param>
    <param><value><string>%s</string></value></param>
    <param><value><i4>0</i4></value></param>
    <param><value><boolean>0</boolean></value></param>
  </params>
</methodCall>""" % (escape(name), encoded, escape(category or ""))
