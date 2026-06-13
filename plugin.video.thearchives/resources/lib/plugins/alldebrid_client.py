# -*- coding: utf-8 -*-

BASE_URL_V4 = "https://api.alldebrid.com/v4/"
BASE_URL_V41 = "https://api.alldebrid.com/v4.1/"


class AllDebridError(Exception):
    pass


def auth_headers(api_key):
    return {"Authorization": "Bearer %s" % api_key}


def response_data(payload):
    if not isinstance(payload, dict):
        raise AllDebridError("AllDebrid returned an invalid response.")
    if payload.get("status") == "error":
        error = payload.get("error") or {}
        message = error.get("message") or error.get("code") or "AllDebrid API error."
        raise AllDebridError(message)
    return payload.get("data", payload)


def get_pin(session):
    return response_data(session.get(BASE_URL_V41 + "pin/get", timeout=20).json())


def check_pin(session, pin, check):
    return response_data(
        session.post(
            BASE_URL_V4 + "pin/check",
            data={"pin": pin, "check": check},
            timeout=20,
        ).json()
    )


def api_get(session, endpoint, api_key, timeout=20):
    return response_data(session.get(BASE_URL_V4 + endpoint, headers=auth_headers(api_key), timeout=timeout).json())


def api_post(session, endpoint, api_key, data=None, timeout=20, base_url=BASE_URL_V4):
    return response_data(
        session.post(
            base_url + endpoint,
            data=data or {},
            headers=auth_headers(api_key),
            timeout=timeout,
        ).json()
    )


def verify_api_key(session, api_key):
    return api_get(session, "user", api_key)


def extract_magnet_files(data, transfer_id):
    magnets = data.get("magnets", []) if isinstance(data, dict) else []
    if isinstance(magnets, dict):
        return magnets.get("files", [])
    for magnet in magnets:
        if isinstance(magnet, dict) and str(magnet.get("id")) == str(transfer_id):
            return magnet.get("files", [])
    return []
