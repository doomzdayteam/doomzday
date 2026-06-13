try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


def build_qr_image_url(approval_url, size=420):
    size = int(size or 420)
    query = urlencode({
        "size": "%sx%s" % (size, size),
        "ecc": "L",
        "qzone": "4",
        "format": "png",
        "data": approval_url or "",
    })
    return "https://api.qrserver.com/v1/create-qr-code/?%s" % query
