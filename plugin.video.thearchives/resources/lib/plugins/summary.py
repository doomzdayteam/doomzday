from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info


class Summary(Plugin):
    name = "summary"
    description = "summary tag support"
    priority = 200

    def get_metadata(self, item):
        if "summary" in item:
            summary = item["summary"]
            set_video_info(item["list_item"],
                {"plot": summary, "plotoutline": summary}
            )
            return item
