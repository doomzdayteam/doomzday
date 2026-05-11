from ..plugin import Plugin


class Summary(Plugin):
    name = "summary"
    description = "summary tag support"
    priority = 200

    def get_metadata(self, item):
        if "summary" in item:
            summary = item["summary"]
            item["list_item"].setInfo(
                "video", {"plot": summary, "plotoutline": summary}
            )
            return item
