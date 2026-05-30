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


def verify_token(session, token):
    return response_data(
        session.get(
            BASE_URL + "user/me",
            headers=auth_headers(token),
            timeout=20,
        ).json()
    )
