from ..plugin import Plugin

class cocoscope(Plugin):
    name = "process cocoscope items"
    priority = 1

    def play_video(self, item):
        import json
        item = json.loads(item)
        link = item.get("link")
        if link and 'cocoscope' in link:                           
            from ..DI import DI
            import re
            import xbmc
            html = DI.session.get(link).text
            play_link = re.search("<source src=\"(.*?)\"", html).group(1)
            xbmc.Player().play(play_link)
            return True