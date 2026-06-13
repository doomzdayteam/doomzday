# -*- coding: utf-8 -*-
"""
Convenience helpers wrapping the bundled infotagger module.
Drop-in replacements for the deprecated ListItem.setInfo() and ListItem.setCast().
"""
from resources.lib.infotagger.listitem import ListItemInfoTag


def set_video_info(listitem, infolabels):
    """Replace listitem.setInfo('video', infolabels)"""
    info_tag = ListItemInfoTag(listitem, 'video')
    info_tag.set_info(infolabels)
    return info_tag


def set_video_cast(listitem, cast):
    """Replace listitem.setCast(cast)"""
    if not cast:
        return
    info_tag = ListItemInfoTag(listitem, 'video')
    info_tag.set_cast(cast)
    return info_tag


def set_music_info(listitem, infolabels):
    """Replace listitem.setInfo('music', infolabels)"""
    info_tag = ListItemInfoTag(listitem, 'music')
    info_tag.set_info(infolabels)
    return info_tag


def set_audio_info(listitem, infolabels):
    """Replace listitem.setInfo('audio', infolabels) - uses music tag"""
    info_tag = ListItemInfoTag(listitem, 'music')
    info_tag.set_info(infolabels)
    return info_tag
