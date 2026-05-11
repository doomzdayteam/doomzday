from ..plugin import Plugin
import xml.etree.ElementTree as ET
import xbmcgui, requests, datetime, time, uuid
from resources.lib.plugin import run_hook
from unidecode import unidecode


class plutotv(Plugin):
    name = "plutotv"
    priority = 100
    BASE_GUIDE = 'https://service-channels.clusters.pluto.tv/v1/guide?start=%s&stop=%s&%s' 
    
    def __timezone(self):
        if time.localtime(time.time()).tm_isdst and time.daylight: return time.altzone / -(60*60) * 100
        else: return time.timezone / -(60*60) * 100

    def process_item(self, item):
        if self.name in item:
            link = item.get("plutotv", "")
            if link == "channels":
                item["link"] = "plutotv/channels"
                item["is_dir"] = True
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")), offscreen=True)
                return item
    
    def routes(self, plugin):
        @plugin.route("/plutotv/channels")
        def get_channels():
            now = datetime.datetime.utcnow()
            stime = datetime.datetime(1970,1,1)
            tz    = str(self.__timezone()).replace(".0", "")
            start = datetime.datetime.now().strftime('%Y-%m-%dT%H:00:00').replace('T','%20').replace(':00:00','%3A00%3A00.000'+tz)
            stop  = (datetime.datetime.now() + datetime.timedelta(hours=48)).strftime('%Y-%m-%dT%H:00:00').replace('T','%20').replace(':00:00','%3A00%3A00.000'+tz)
            url = self.BASE_GUIDE %(start,stop,'deviceId=%s&deviceMake=Chrome&deviceType=web&deviceVersion=80.0.3987.149&DNT=0&sid=%s&appName=web&appVersion=5.2.2-d60060c7283e0978cc63ba036956b5c1657f8eba'%(str(uuid.uuid4()),str(uuid.uuid1())))
            json_data = requests.get(url).json()
            channels = json_data['channels']
            images = channels[0]['images']
            Images ={}
            jen_list = []
            for c in channels:
                chData = {}
                shData = []
                images = c['images']
                for i in images:
                    imageurl = i['url']
                    imagetype = i['type']
                    Images.update( {imagetype : imageurl} )
                chlogo = Images['logo']
                chthumb = Images['colorLogoPNG']
                chfanart = Images['featuredImage']
                chhero = Images['hero']
                chname = c['name']
                chsummary = c['summary']
                try:
                    chlink = c['stitched']['urls'][0]['url']
                except:
                    chlink = ""
                try:
                    chlink = c['timelines'][0]['episode']['sourcesWithClipDetails'][0]['url']
                    chlink = chlink + "?serverSideAds=true|User-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36"
                except:
                    pass
                chnum = c['number']
                chData.update({'channelname': chname,
                            'channelnumber': chnum,
                            'channellogo': chlogo,})
                try:
                    timelines = c['timelines']
                    for t in timelines:
                        sstart = t['start'][0:19]
                        starttime = datetime.datetime(*(time.strptime(sstart, "%Y-%m-%dT%H:%M:%S")[0:6]))
                        gamestartepoch = int((starttime - stime).total_seconds())
                        sstop = t['stop'][0:19]
                        stoptime = datetime.datetime(*(time.strptime(sstop, "%Y-%m-%dT%H:%M:%S")[0:6]))
                        gamestopepoch = int((stoptime - stime).total_seconds())
                        duration = int(gamestopepoch - gamestartepoch)
                        sname = t['title'][0:71]
                        plot = t['episode']['description']
                        genre = t['episode']['genre']
                        shthumb = t['episode']['series']['featuredImage']['path']
                        shData.append({
                            'url': chlink,
                            'fanart': chfanart,
                            'mediatype': 'show',
                            'genre': genre,
                            'starttime': gamestartepoch, 
                            'duration': duration, 
                            'label': unidecode(sname.replace('"', "").replace("'", "")), 
                            'label2': 'HD',
                            'channelname': chname, 
                            'art': {
                                'thumb': chfanart,
                                'fanart': shthumb, 
                                'poster': '', 
                                'logo': '', 
                                'clearart': '',
                                'icon': chlogo
                            } 
                        })
                    
                    chData['guidedata']=shData
                except: pass

                jen_data = {
                    "title": str(chnum) + " | " + chname,
                    "thumbnail": chthumb,
                    "fanart": chfanart,
                    "link": [chlink],
                    "number": chnum,
                    "guidedata": shData,
                    "type": "item"
                }
                jen_list.append(jen_data)
            jen_list.sort(key=lambda x: x["number"])
            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item) for item in jen_list]
            run_hook("display_list", jen_list)