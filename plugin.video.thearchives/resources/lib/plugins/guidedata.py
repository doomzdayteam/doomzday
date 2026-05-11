from resources.lib.plugin import Plugin
import datetime, time, xbmc


class guidedata(Plugin):
    name = "guidedata"
    priority = 100

    def get_metadata(self, item):
        if "guidedata" in item:
            ts = time.time()
            utc_offset = (datetime.datetime.fromtimestamp(ts) - datetime.datetime.utcfromtimestamp(ts)).total_seconds()
            current_time = ts
            label = "N/A"
            times = []
            for programme in item["guidedata"]:
                if programme["starttime"] >= (current_time - 9600):
                    start_time = datetime.datetime.utcfromtimestamp(programme["starttime"] + utc_offset)
                    end_time = datetime.datetime.utcfromtimestamp(programme["starttime"] + programme["duration"] + utc_offset)
                    label = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}: [COLORred]{programme['label']}[/COLOR]"
                    times.append(label)
                if current_time >= programme["starttime"] and current_time <= programme["starttime"] + programme["duration"]:
                    start_time = datetime.datetime.utcfromtimestamp(programme["starttime"] + utc_offset)
                    end_time = datetime.datetime.utcfromtimestamp(programme["starttime"] + programme["duration"] + utc_offset)
                    label = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}: {programme['label']}"
                    item["list_item"].setLabel(item["list_item"].getLabel() + f"\n{label}")
            item["summary"] = "\n".join(times)
        if "summary" in item:
            summary = item["summary"]
            item["list_item"].setInfo(
                "video", {"plot": summary, "plotoutline": summary}
            )
        return item