# -*- coding: utf-8 -*-
import os
import re

import xbmc
import xbmcaddon
import xbmcgui


SELECTION_ACTIONS = (7, 100)
CLOSING_ACTIONS = (9, 10, 13, 92)


QUALITY_COLORS = {
    "4K": "FFFF3300",
    "2160P": "FFFF3300",
    "1080P": "FFFF7A00",
    "720P": "FFFF9900",
    "SD": "FFFF3300",
    "CAM": "FFFF3300",
}


def _clean(value, default=""):
    value = str(value if value is not None else default).strip()
    return value or default


def _upper(value, default=""):
    return _clean(value, default).upper()


def _art_path(path, addon_path):
    path = _clean(path)
    if not path:
        return path
    lower_path = path.lower()
    if lower_path.startswith(("http://", "https://", "special://")) or os.path.isabs(path):
        return path
    return os.path.join(addon_path, path.replace("/", os.sep))


def _quality(value):
    value = _upper(str(value or "SD").replace(".", ""), "SD")
    if value in ("2160P", "4K"):
        return "4K"
    return value


def _format_gb(value):
    return "%.2f GB" % float(value)


def _format_bytes(value):
    return "%.2f GB" % (float(value) / (1024 ** 3))


def _size_label(source):
    size_label = source.get("size_label")
    if size_label not in (None, ""):
        return _clean(size_label)

    size = source.get("size")
    if size not in (None, ""):
        if isinstance(size, (int, float)):
            return _format_gb(size) if abs(float(size)) < 10000 else _format_bytes(size)
        return _clean(size)

    for key in ("filesize", "size_bytes"):
        value = source.get(key)
        if value not in (None, ""):
            if isinstance(value, (int, float)):
                return _format_bytes(value)
            return _clean(value)

    info = _clean(source.get("info"), "Size Unknown")
    match = re.search(r"\d+(?:\.\d+)?\s*[KMGT]?B", info, re.I)
    return match.group(0) if match else info


def _provider(source):
    return _upper(source.get("debrid_service") or source.get("cache_provider") or source.get("debrid") or "Debrid", "DEBRID")


def _hoster(source, provider):
    if source.get("debrid_cached"):
        return "%s CACHED" % provider
    if source.get("debrid_uncached"):
        return "%s UNCACHED" % provider
    if source.get("direct"):
        return "DIRECT"
    return provider


def _site(source):
    return _upper(source.get("origin") or source.get("provider") or source.get("source") or "Unknown", "UNKNOWN")


def _title(source, fallback):
    return _upper(source.get("display_name") or source.get("name") or source.get("title") or fallback, "UNKNOWN")


def _info(source):
    parts = []
    seeders = source.get("seeders") or source.get("seeds") or source.get("seed")
    if seeders not in (None, ""):
        parts.append("S:%s" % seeders)
    source_type = source.get("source") or source.get("provider") or source.get("origin")
    if source_type:
        parts.append(_upper(source_type))
    extra = _clean(source.get("extraInfo") or source.get("extra_info"), "")
    if extra:
        parts.append(extra.upper())
    return " | ".join(parts) if parts else _upper(source.get("info"), "N/A")


def build_source_row(source, count, fallback_label=""):
    quality = _quality(source.get("quality"))
    provider = _provider(source)
    return {
        "count": "%02d." % count,
        "quality": quality,
        "provider": provider,
        "highlight": QUALITY_COLORS.get(quality, "FFFF3300"),
        "line1": "SIZE: %s     HOSTER: %s     SITE: %s" % (_size_label(source), _hoster(source, provider), _site(source)),
        "line2": "INFO: %s" % _info(source),
        "line3": "TITLE: %02d. %s" % (count, _title(source, fallback_label)),
    }


def build_source_rows(sources, labels=None):
    labels = labels or []
    return [build_source_row(source, index + 1, labels[index] if index < len(labels) else "") for index, source in enumerate(sources or [])]


class ArchivesSourceResults(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args)
        self.sources = kwargs.get("sources") or []
        self.labels = kwargs.get("labels") or []
        self.meta = kwargs.get("meta") or {}
        self.rows = build_source_rows(self.sources, self.labels)
        self.selected = -1

    def onInit(self):
        addon = xbmcaddon.Addon()
        addon_path = addon.getAddonInfo("path")
        addon_icon = addon.getAddonInfo("icon")
        self.setProperty("icon", _art_path(addon_icon, addon_path))
        self.setProperty("fanart", _art_path(self.meta.get("fanart") or addon.getAddonInfo("fanart"), addon_path))
        self.setProperty("poster", _art_path(self.meta.get("thumbnail") or self.meta.get("poster") or addon_icon, addon_path))
        self.setProperty("title", self.meta.get("title") or "Select a Cached Debrid Link")
        self.setProperty("total_results", str(len(self.rows)))
        self._add_rows()
        try:
            self.setFocusId(2000)
        except Exception:
            pass

    def _add_rows(self):
        items = []
        for row in self.rows:
            item = xbmcgui.ListItem(row["line3"])
            for key, value in row.items():
                item.setProperty(key, str(value))
            items.append(item)
        self.getControl(2000).addItems(items)

    def _action_id(self, action):
        try:
            return action.getId()
        except Exception:
            return int(action)

    def onAction(self, action):
        action_id = self._action_id(action)
        if action_id in CLOSING_ACTIONS:
            self.selected = -1
            self.close()
        elif action_id in SELECTION_ACTIONS:
            self._select_focused()

    def onClick(self, control_id):
        if control_id == 2000:
            self._select_focused()

    def _select_focused(self):
        try:
            self.selected = self.getControl(2000).getSelectedPosition()
        except Exception:
            self.selected = -1
        self.close()

    def run(self):
        self.doModal()
        return self.selected


def select_source(sources, labels, meta=None):
    if not sources:
        return -1
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    try:
        dialog = ArchivesSourceResults("archives_sources.xml", addon_path, "Default", "1080i", sources=sources, labels=labels, meta=meta or {})
        selected = dialog.run()
        del dialog
        return selected
    except Exception as exc:
        xbmc.log("TheArchivesSourcePicker - custom source window failed: %s" % exc, getattr(xbmc, "LOGERROR", 4))
        return xbmcgui.Dialog().select("Select a Cached Debrid Link", labels)

