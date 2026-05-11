from posixpath import join, split
from ..DI import DI
from ..plugin import Plugin
import json


class TRAKT(Plugin):
    name = "trakt"
    def get_list(self, url):
        if url.startswith("trakt"):
            api = TRAKT_API()
            if "trakt_tv_show" in url:
                show_id, _, show_title= url.replace("trakt_tv_show(", "")[:-1].split(",")
                return api.handle_show(show_id, show_title.strip())
            elif "trakt_tv_season" in url:
                show_id, season, show_title = url.replace("trakt_tv_season(", "")[:-1].split(",")
                return api.handle_season(show_id, season.strip(), show_title.strip())
            else:
                _,kind, list_id = url.split("/")
                if kind == "list":
                    return api.handle_list(list_id)                 

class TRAKT_API:
    @property
    def headers(self):
        return {
            'Content-Type': 'application/json',
            'trakt-api-version':'2',
            'trakt-api-key': self.client_id
        }
    session = DI.session
    base_url = "https://api.trakt.tv"
    client_id = ""
    #client_secret = ""

    def get_list(self, list_id):
        response = self.session.get(f"{self.base_url}/lists/{list_id}/items?extended=full", headers = self.headers)
        trakt_list = response.json()
        return trakt_list

    def get_show(self, show_id:int):
        response = self.session.get(f"{self.base_url}/shows/{show_id}/seasons", headers = self.headers)    
        trakt_show = response.json()     
        return trakt_show

    def get_season(self, show_id:int, season:int):
        response = self.session.get(f"{self.base_url}/shows/{show_id}/seasons/{season}?extended=full", headers = self.headers)
        trakt_season = response.json()        
        return trakt_season

    def process_items(self, items):
        items = [self.handle_item(item) for item in items]
        return items

    def handle_item(self, item):
        media_type = item["type"]
        if media_type == "movie":
            return self.handle_movie_xml(item)
        elif media_type == "show":
            return self.handle_show_xml(item)

    def handle_movie_xml(self, movie):
        movie = movie["movie"]
        return {
            "title": movie["title"],
            "year": movie["year"],
            "content": "movie",
            "summary": movie["overview"].replace('"', '\\\"').replace("'", '\\\''),
            "tmdb_id": movie["ids"]["tmdb"],
            "imdb_id": movie["ids"]["imdb"],
            "type": "item",
            "link": "Search"
        }

    def handle_show_xml(self, show):
        show = show["show"]
        return {
            "title": show["title"],
            "link": f'trakt_tv_show({show["ids"]["trakt"]}, {show["year"]}, {show["title"]})',
            "summary": show["overview"].replace('"', '\\\"').replace("'", '\\\''),
            "type": "dir"
        }

    def handle_season_xml(self, show, show_id, show_title):
        return [{
            "title": f'Season {season["number"]}',
            "link": f'trakt_tv_season({show_id}, {season["number"]}, {show_title})',
            "type": "dir"
            } for season in show]

    def handle_episodes_xml(self, season, show_title):
        return [{
            "title": episode["title"],
            "summary": episode['overview'].replace('"', '\\\"').replace("'", '\\\''),
            "content": "episode",
            "tmdb_id": episode["ids"]["tmdb"],
            "imdb_id": episode["ids"]["imdb"],
            "season": episode['season'],
            "episode": episode['number'],
            "premiered": episode['first_aired'].split("-")[0],
            "tv_show_title": show_title,
            "type": "item",
            "link": "Search"
        } for episode in season]

    def handle_list(self, list_id: str):
        return json.dumps({"items": self.process_items(self.get_list(list_id))})

    def handle_show(self, show_id:str, show_title):
        return json.dumps({"items": self.handle_season_xml(self.get_show(show_id.strip()), show_id, show_title)})

    def handle_season(self, show_id:int, season:int, show_title):
        return json.dumps({"items": self.handle_episodes_xml(self.get_season(show_id.strip(), season.strip()), show_title)})
