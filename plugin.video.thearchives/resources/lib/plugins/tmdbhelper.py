from ..plugin import Plugin


class tmdbhelper(Plugin):
    name = "disabled tmdbhelper playback"
    priority = -100

    def play_video(self, item):
        return False
