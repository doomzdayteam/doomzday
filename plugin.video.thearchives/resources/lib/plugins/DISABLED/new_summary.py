from ..plugin import Plugin
import json

class Summary(Plugin):
    name = "summary"
    description = "summary tag support"
    priority = 200

    def get_metadata(self, item):
        video_data={}
        video_data['title']=item.get('title',"")
        video_data['genre']=item.get('genre',"")
        
        # if "summary" in item:
            # summary = item["summary"]
        # else:
            # video_data['plot']=item.get('plot',"")
        
        if "summary" in item:
            video_data['plot'] = item.get('summary','')
        elif "plot" in item:
            video_data['plot']=item.get('plot','')
        else :
            video_data['plot']='No Plot data available'
            
            
        video_data['duration']=item.get('duration',"")
        try:
            video_data['duration']=int(video_data['duration'])*60
        except:
            pass
        video_data['year']=item.get('year',"")
        video_data['director']=item.get('director',"")
        video_data['writer']=item.get('writer',"")
        video_data['season']=item.get('season',"")
        video_data['episode']=item.get('episode',"")
        video_data['originaltitle']=item.get('originaltitle',"")
        video_data['mediatype']=item.get('mediatype',"")
        video_data['rating']=item.get('rating',"")
        video_data['studio']=item.get('studios',"")
        video_data['dateadded']=item.get('dateadded',"")
        video_data['trailer']="plugin://plugin.video.youtube/?action=play_video&videoid="+item.get('trailer',"")
        imdb=item.get('imdb',"")
        try:
            actors=json.loads(item.get('cast',""))
            item["list_item"].setCast(actors)
        except:            
            pass

        # if "summary" in item:
            #'summary = item["summary"]
        # if "plot" in item:
            # summary = item["plot"]
            
        item["list_item"].setInfo(type="Video", infoLabels=video_data)
        item["list_item"].setUniqueIDs({ 'imdb': imdb }, "imdb")
        
        
        return item
