import html
import json
import re
from urllib.parse import unquote, urljoin


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def parse_channel_text(text):
    channels = []
    pending = None

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("##"):
            continue

        if "||" in line and not line.lower().startswith(("http://", "https://")):
            parts = [part.strip() for part in line.split("||")]
            if len(parts) < 3:
                pending = None
                continue
            pending = {
                "title": parts[0],
                "channel_id": parts[1],
                "category": parts[2].strip().title() or "Uncategorized",
            }
            continue

        if pending and line.lower().startswith(("http://", "https://")):
            item = dict(pending)
            item["url"] = line
            channels.append(item)
            pending = None

    return channels


def clean_stream_url(value):
    value = html.unescape(value or "")
    value = value.replace("\\u0026", "&")
    value = value.replace("\\/", "/")
    value = value.replace("\\x3d", "=")
    value = value.strip().strip('"').strip("'")
    return value


def _decode_json_string(value):
    try:
        return json.loads('"%s"' % value)
    except Exception:
        return value


def extract_hls_manifest_url(response):
    response = response or ""

    match = re.search(r'"hlsManifestUrl"\s*:\s*"((?:\\.|[^"\\])*)"', response)
    if match:
        return clean_stream_url(_decode_json_string(match.group(1)))

    match = re.search(r'(https?://[^"\'<>\s]+?\.m3u8[^"\'<>\s]*)', response)
    if match:
        return clean_stream_url(match.group(1))

    return ""


def is_playable_hls_manifest(manifest_text):
    manifest_text = manifest_text or ""
    return (
        "#EXT-X-STREAM-INF" in manifest_text
        or "#EXTINF" in manifest_text
        or "#EXT-X-MAP" in manifest_text
    )


def _variant_score(metadata):
    bandwidth_match = re.search(r"BANDWIDTH=(\d+)", metadata or "")
    resolution_match = re.search(r"RESOLUTION=(\d+)x(\d+)", metadata or "")
    bandwidth = int(bandwidth_match.group(1)) if bandwidth_match else 0
    height = int(resolution_match.group(2)) if resolution_match else 0
    return height, bandwidth


def extract_hls_variants(manifest_text, base_url):
    variants = []
    lines = (manifest_text or "").splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF"):
            continue
        if index + 1 >= len(lines):
            continue
        playlist = lines[index + 1].strip()
        if not playlist or playlist.startswith("#"):
            continue
        variants.append({
            "metadata": line,
            "url": urljoin(base_url, playlist),
            "score": _variant_score(line),
        })
    variants.sort(key=lambda variant: variant["score"], reverse=True)
    return variants


def extract_hls_segments(manifest_text, base_url):
    segments = []
    for line in (manifest_text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        segments.append(urljoin(base_url, line))
    return segments


def verify_first_hls_segment(manifest_text, base_url, session, timeout=15):
    segments = extract_hls_segments(manifest_text, base_url)
    if not segments:
        return False
    try:
        response = session.get(
            segments[0],
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=timeout,
        )
    except Exception:
        return False
    return getattr(response, "status_code", 0) == 200


def verify_hls_manifest(url, session, timeout=15):
    if not url:
        return ""
    try:
        response = session.get(
            url,
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=timeout,
        )
    except Exception:
        return ""
    if getattr(response, "status_code", 0) != 200:
        return ""
    manifest_text = getattr(response, "text", "")
    if not is_playable_hls_manifest(manifest_text):
        return ""

    for variant in extract_hls_variants(manifest_text, url):
        try:
            variant_response = session.get(
                variant["url"],
                headers={"User-Agent": DEFAULT_USER_AGENT},
                timeout=timeout,
            )
        except Exception:
            continue
        if getattr(variant_response, "status_code", 0) != 200:
            continue
        variant_text = getattr(variant_response, "text", "")
        if (
            is_playable_hls_manifest(variant_text)
            and verify_first_hls_segment(variant_text, variant["url"], session, timeout=timeout)
        ):
            return variant["url"]

    if verify_first_hls_segment(manifest_text, url, session, timeout=timeout):
        return url
    return ""


def extract_video_id(url):
    match = re.search(r"(?:youtube\.com/(?:watch\?v=|embed/|live/)|youtu\.be/)([^\"&?/\s]{11})", url or "")
    if match:
        return match.group(1)
    if re.fullmatch(r"[^\"&?/\s]{11}", url or ""):
        return url
    return ""


def extract_innertube_config(response):
    response = response or ""
    key_match = re.search(r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"', response)
    version_match = re.search(r'"INNERTUBE_CLIENT_VERSION"\s*:\s*"([^"]+)"', response)
    if not key_match or not version_match:
        return {}
    return {
        "api_key": key_match.group(1),
        "client_version": version_match.group(1),
    }


def _post_player(session, api_key, client, video_id, referer, timeout):
    payload = {
        "context": {
            "client": client,
            "thirdParty": {"embedUrl": "https://www.youtube.com/embed/%s" % video_id},
        },
        "videoId": video_id,
        "contentCheckOk": True,
        "racyCheckOk": True,
    }
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Content-Type": "application/json",
        "Origin": "https://www.youtube.com",
        "Referer": referer,
    }
    response = session.post(
        "https://www.youtube.com/youtubei/v1/player?key=%s" % api_key,
        headers=headers,
        data=json.dumps(payload),
        timeout=timeout,
    )
    if getattr(response, "status_code", 0) != 200:
        return ""
    data = response.json()
    streaming = data.get("streamingData") or {}
    return clean_stream_url(streaming.get("hlsManifestUrl") or "")


def resolve_innertube_hls(watch_url, page_html, session, timeout=15):
    video_id = extract_video_id(watch_url)
    config = extract_innertube_config(page_html)
    if not video_id or not config:
        return ""

    base = {
        "hl": "en",
        "gl": "US",
    }
    clients = [
        dict(base, clientName="ANDROID", clientVersion="20.21.35", androidSdkVersion=35),
        dict(base, clientName="WEB", clientVersion=config["client_version"]),
        dict(base, clientName="WEB_EMBEDDED_PLAYER", clientVersion=config["client_version"]),
        dict(base, clientName="TVHTML5", clientVersion="7.20250129.19.00"),
    ]
    for client in clients:
        try:
            manifest = _post_player(session, config["api_key"], client, video_id, watch_url, timeout)
            if manifest:
                return manifest
        except Exception:
            continue
    return ""


def _clean_text(value):
    value = clean_stream_url(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _thumbnail_from_block(block):
    match = re.search(r'"thumbnail"\s*:\s*\{.*?"url"\s*:\s*"((?:\\.|[^"\\])*)"', block)
    if match:
        return clean_stream_url(_decode_json_string(match.group(1)))
    return ""


def _title_from_block(block, fallback):
    match = re.search(r'"title"\s*:\s*\{\s*"runs"\s*:\s*\[\s*\{\s*"text"\s*:\s*"((?:\\.|[^"\\])*)"', block)
    if match:
        return _clean_text(_decode_json_string(match.group(1)))
    match = re.search(r'"title"\s*:\s*\{\s*"simpleText"\s*:\s*"((?:\\.|[^"\\])*)"', block)
    if match:
        return _clean_text(_decode_json_string(match.group(1)))
    return fallback


def extract_search_results(response, limit=30):
    response = response or ""
    results = []
    seen = set()

    for match in re.finditer(r'"videoRenderer"\s*:\s*\{\s*"videoId"\s*:\s*"([^"]{11})"', response):
        video_id = match.group(1)
        if video_id in seen:
            continue
        seen.add(video_id)
        block = response[match.start():match.start() + 5000]
        title = _title_from_block(block, "YouTube Live")
        results.append({
            "id": video_id,
            "title": title,
            "url": "https://www.youtube.com/watch?v=%s" % video_id,
            "thumbnail": _thumbnail_from_block(block),
        })
        if len(results) >= limit:
            return results

    for video_id in re.findall(r'(?:/watch\?v=|watch\?v%3D)([^"&?/\\\s]{11})', response):
        video_id = unquote(video_id)
        if video_id in seen:
            continue
        seen.add(video_id)
        results.append({
            "id": video_id,
            "title": "YouTube Live",
            "url": "https://www.youtube.com/watch?v=%s" % video_id,
            "thumbnail": "",
        })
        if len(results) >= limit:
            break

    return results


def resolve_live_hls(url, session, timeout=15):
    if "&" in url:
        url = url.split("&", 1)[0]

    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    response = session.get(url, headers=headers, timeout=timeout)
    if getattr(response, "status_code", 0) != 200:
        return ""
    page_html = getattr(response, "text", "")
    candidates = [
        resolve_innertube_hls(url, page_html, session, timeout=timeout),
        extract_hls_manifest_url(page_html),
    ]
    for manifest in candidates:
        verified = verify_hls_manifest(manifest, session, timeout=timeout)
        if verified:
            return verified
    return ""
