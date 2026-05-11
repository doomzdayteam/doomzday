import json
import requests

from ..DI import DI
from ..plugin import Plugin

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *


ITEMS_PER_PAGE = [20, 40, 60, 80, 100]
PAGES = int(ITEMS_PER_PAGE[int(ownAddon.getSetting("items_per_page"))]/20)

class objectview(object):
    def __init__(self, d):
        self.__dict__ = d


class TMDB_API:
    @property
    def headers(self):
        return {
            "content-type": "application/json;charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
        }

    base_url = "https://api.themoviedb.org"
    image_url = "https://image.tmdb.org/t/p/w500"
    api_key = ownAddon.getSetting("tmdb.api_key") or ""
    access_token = ownAddon.getSetting("tmdb.access_token") or ""
    session = DI.session

    def get(self, path: str, paginated: bool = True, full_meta: bool = False, page_count: int = 1):
        page = 1
        if paginated:
            splitted = path.split("/")
            pagenum = splitted[-1]
            if str.isdigit(pagenum) and len(splitted) == 3:
                page = int(pagenum)
                path = "/".join(splitted[:-1])
            
            if path.startswith("discover"):
                if len(splitted) == 2:
                    pass
                else:
                    page = int(pagenum)
                    media_type = splitted[1]
                    kind = splitted[2]
                    _id = splitted[3]
                    if kind == "genre":
                        path = f"discover/{media_type}?with_genres={_id}"
                    elif kind == "network":
                        path = f"discover/{media_type}?with_networks={_id}"
                    elif kind == "company":
                        path = f"discover/{media_type}?with_companies={_id}"
                    elif kind == "year":
                        path = f"discover/{media_type}?year={_id}"
                           
            elif path.startswith("search") and len(splitted) == 4:
                page = int(pagenum)
                path = f"{'/'.join(splitted[:-2])}?query={splitted[-2]}"
            
        if path.startswith("list"):
            version = 4
        else:
            version = 3
        req = requests.PreparedRequest()
        if full_meta:
            req.prepare_url(
                f"{self.base_url}/{version}/{path}", {"api_key": self.api_key, "language": "en-US", "page": page, "append_to_response": "videos,credits,release_dates,content_ratings"}
            )
        else:
            req.prepare_url(
            f"{self.base_url}/{version}/{path}", {"api_key": self.api_key, "language": "en-US", "page": page}
        )
        response = self.session.get(
            req.url,
            headers=self.headers,
        ).json()
        if  path.startswith("person/"):
            if "cast" in response or "crew" in response:
                results = response.get("cast", [])
                results.extend(response.get("crew", []))
        else:
            results = response.get("results", response.get("parts", response))
        
        total_pages = response.get("total_pages", 1)
        if total_pages > page:
            if page_count < PAGES:
                results.extend(self.get(f"{path.replace('?with_genres=', '/genre/').replace('?with_networks=', '/network/').replace('?with_companies=', '/company/').replace('?year=', '/year/').replace('?query=', '/')}/{page + 1}", paginated=paginated, full_meta=full_meta,page_count=page_count +1))
            elif page_count == PAGES:
                results.append({"type": "dir", "title": "Next Page", "link": f"tmdb/{path.replace('?with_genres=', '/genre/').replace('?with_networks=', '/network/').replace('?with_companies=', '/company/').replace('?year=', '/year/').replace('?query=', '/')}/{page + 1}"})
            
        return results

    def handle_items(self, items,show_id=None):
        if type(items) == list:
            return {"items": [self.handle_items(item) for item in items]}
        if items.get("link", "").startswith("tmdb/"):
            return items

        poster = (
            f'{self.image_url}/{items["poster_path"]}'
            if items.get("poster_path")
            else None
        )
        backdrop = (
            f'{self.image_url}/{items["backdrop_path"]}'
            if items.get("backdrop_path")
            else None
        )
        if "title" in items:
            if ownAddon.getSettingBool("full_meta"):
                movie = self.get(f"movie/{items['id']}", full_meta=True)
            else:
                movie = self.get(f"movie/{items['id']}")
            year = movie["release_date"].split("-")[0] or 0
            imdb = movie["imdb_id"] if movie["imdb_id"] else 0
            item = objectview(items)
            item.poster_path = poster
            item.backdrop_path = backdrop
            jen_item = {
                "content": "movie",
                "type": "item",
                "title": item.title,
                "link": "search",
                "thumbnail": item.poster_path,
                "fanart": item.backdrop_path,
                "summary": item.overview,
                "tmdb_id": item.id,
                "imdb_id": imdb,
                "year": year,
            }
            if ownAddon.getSettingBool("full_meta"):
                jen_item["infolabels"] = self.get_infolabels(movie, media_type="movie")
                jen_item["cast"] = self.get_cast(movie)
            return jen_item
        
        elif "name" in items:
            if "episodes" in items:
                # tv episodes
                show = self.get(f"tv/{show_id}")
                show = objectview(show)
                imdb = self.get(f"tv/{show_id}/external_ids")["imdb_id"]
                year = show.first_air_date.split("-")[0] if show.first_air_date else 0
                result = []
                for episode in items["episodes"]:
                    if ownAddon.getSettingBool("full_meta"):
                        ep = self.get(f"tv/{show_id}/season/{episode['season_number']}/episode/{episode['episode_number']}", full_meta=True)
                    else:
                        ep = self.get(f"tv/{show_id}/season/{episode['season_number']}/episode/{episode['episode_number']}")
                    still = (
                        f'{self.image_url}/{episode["still_path"]}'
                        if episode.get("still_path")
                        else None
                    )
                    episode_number = episode.get("episode_number", "")
                    if episode_number:
                        episode_number = f"{episode_number}. "
                    
                    item = objectview(episode)
                    item.still_path = still
                    jen_item = {
                        "content": "episode",
                        "type": "item",
                        "title": f"{episode_number}{item.name}",
                        "link": "search",
                        "thumbnail": still,
                        "fanart": still,
                        "tmdb_id": item.id,
                        "imdb_id": imdb,
                        "tv_show_title": show.name,
                        "year": year,
                        "season": item.season_number,
                        "episode": item.episode_number,
                        "premiered": item.air_date,
                    }
                    if ownAddon.getSettingBool("full_meta"):
                        jen_item["infolabels"] = self.get_infolabels(ep, media_type="episode")
                        jen_item["cast"] = self.get_cast(ep, media_type="episode")
                        if jen_item["infolabels"].get("premiered"):
                            air_date = jen_item["infolabels"]["premiered"]
                            try:
                                from datetime import datetime
                                air_date = datetime.strptime(air_date, '%Y-%m-%d')
                                if air_date > datetime.today():
                                    jen_item["title"] = f"[COLOR red]{jen_item['title']}[/COLOR]"
                            except:
                                pass
                    result.append(jen_item)
                return {"items": result}
            elif "seasons" in items:
                results = []
                for season in items["seasons"]:
                    poster = (
                        f'{self.image_url}/{items["poster_path"]}'
                        if items.get("poster_path")
                        else None
                    )
                    item = objectview(season)
                    item.poster_path = poster
                    jen_item = {
                        "content": "season",
                        "type": "dir",
                        "link": f"tmdb/tv/{items['id']}/season/{item.season_number}",
                        "thumbnail": item.poster_path,
                        "title": item.name,
                        "summary": item.overview,
                    }
                    results.append(jen_item)
                return {"items": results}
            else:
                # tv shows
                item = objectview(items)
                item.poster_path = poster
                item.backdrop_path = backdrop
                jen_item = {
                    "content": "tvshow",
                    "type": "dir",
                    "link": f"tmdb/tv/{item.id}",
                    "thumbnail": item.poster_path,
                    "fanart": item.backdrop_path,
                    "title": item.name,
                    "summary": item.overview,
                }
                if ownAddon.getSettingBool("full_meta"):
                    req = requests.PreparedRequest()
                    req.prepare_url(
                        f"{self.base_url}/3/tv/{item.id}", {"api_key": self.api_key, "append_to_response": "videos,credits,release_dates,content_ratings"}
                    )
                    response = self.session.get(
                        req.url,
                        headers=self.headers,
                    ).json()
                    jen_item["infolabels"] = self.get_infolabels(response, media_type="tvshow")
                    jen_item["cast"] = self.get_cast(response)
                return jen_item
    
    def tmdb_from_imdb(self, imdb_id: str):
        req = self.session.get(f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={self.api_key}&language=en-US&external_source=imdb_id", headers=self.headers).json()
        if req.get("movie_results"):
            return req["movie_results"][0]["id"]
        elif req.get("tv_results"):
            return req["tv_results"][0]["id"]
        else:
            return None
    
    def get_infolabels(self, items: dict, media_type: str):
        if media_type == 'movie':
            title = items.get('title', 'Unknown Title')
        elif media_type == 'tvshow' or media_type == 'episode':
            title = items.get('name', 'Unknown Title')
        
        plot = items.get('overview', '')
        
        if media_type == 'movie':
            premiered = items.get('release_date', '')
        elif media_type == 'tvshow':
            premiered = items.get('first_air_date', '')
        elif media_type == 'episode':
            premiered = items.get('air_date', '')
        
        genre = [genra.get('name') for genra in items.get('genres')] if items.get('genres') else ''
          
        try:
            mpaa = ''
            for releases in items['release_dates']['results']:
                if releases['iso_3166_1'] == 'US':
                    for release in releases['release_dates']:
                        if release['certification'] != '':
                            mpaa = release['certification']
                            break
        except KeyError:
            mpaa = ''
        
        try:
            if media_type == 'episode':
                crew = items['crew']
            else:
                crew = items['credits']['crew']
            director = []
            writer = []
            for job in crew:
                if job['job'] == 'Director':
                    director.append(job['name'])
                if job['job'] == 'Writer' or job['job'] == 'Screenplay' or job['department'] == 'Writing':
                    writer.append(job['name'])
        except KeyError:
            director = ''
            writer = ''
        
        rating = items.get('vote_average', 0)
        
        votes = items.get('vote_count', '')
        
        try:
            if media_type == 'movie':
                studio = [studio['name'] for studio in items['production_companies']]
            else:
                studio = [studio['name'] for studio in items['networks']]
                for company in items['production_companies']:
                    studio.append(company['name'])
        except KeyError:
            studio = ''
        
        try:
            country = [country['name'] for country in items['production_countries']]
        except KeyError:
            country = ''
        
        if items.get('belongs_to_collection'):
            _set = items['belongs_to_collection'].get('name', '')
        else:
            _set = ''
        
        status = items.get('status', '')
        
        try:
            if media_type == 'movie' or media_type == "episode":
                duration = items.get('runtime', 0)*60
            elif media_type == 'tvshow':
                duration = items['episode_run_time'][0]*60
            else:
                duration = 0
        except (KeyError, IndexError, TypeError):
            duration = 0
        
        try:
            videos = items['videos']['results']
            trailer = ''
            for video in videos:
                if video['type'] == 'Trailer':
                    video_id = video['key']
                    trailer = f'plugin://plugin.video.youtube/play/?video_id={video_id}'
            if trailer == '':
                for video in videos:
                    if video['type'] == 'Teaser':
                        video_id = video['key']
                        trailer = f'plugin://plugin.video.youtube/play/?video_id={video_id}'
        except KeyError:
            trailer = ''
        
        infolabels = {
            'mediatype': media_type,
            'title': title,
            'plot': plot,
            'premiered': premiered,
            'genre': genre,
            'mpaa': mpaa,
            'director': director,
            'writer': writer,
            'rating': rating,
            'votes': votes,
            'studio': studio,
            'country': country,
            'set': _set,
            'status': status,
            'duration': duration,
            'trailer': trailer
        }
        return infolabels
    
    def get_cast(self, items: dict, media_type: str = ""):
        cast = []
        try:
            cast_list = items['credits']['cast']
            for actor in cast_list:
                cast.append({"name": actor['name'], "role": actor['character'], "thumbnail": f"{self.image_url}{actor['profile_path']}"})
        except KeyError:
            pass
        if media_type == "episode":
            try:
                cast_list = items['guest_stars']
                for actor in cast_list:
                    cast.append({"name": actor['name'], "role": actor['character'], "thumbnail": f"{self.image_url}{actor['profile_path']}"})
            except KeyError:
                pass
        return cast


class TMDB(Plugin):
    name = "tmdb Plugin (v2)"

    def get_list(self, url: str):
        api_url = ""
        if url.startswith("tmdb"):
            api = TMDB_API()
            splitted = url.split("/")
            kind = splitted[1]
            if len(splitted) > 3:
                kind = splitted[1]
                list_id = splitted[3]
                if kind == "genre":
                    if "show" in splitted[2] or "tv" in splitted[2]:
                        api_url = f"discover/tv?with_genres={list_id}"
                    else:
                        api_url = f"discover/movie?with_genres={list_id}"
                elif kind == "network":
                    if "show" in splitted[2] or "tv" in splitted[2]:
                        api_url = f"discover/tv?with_networks={list_id}"
                    else:
                        api_url = f"discover/movie?with_networks={list_id}"
                elif kind == "company":
                    if "show" in splitted[2] or "tv" in splitted[2]:
                        api_url = f"discover/tv?with_companies={list_id}"
                    else:
                        api_url = f"discover/movie?with_companies={list_id}"
                elif kind == "year":
                    if "show" in splitted[2] or "tv" in splitted[2]:
                        api_url = f"discover/tv?year={list_id}"
                    else:
                        api_url = f"discover/movie?year={list_id}"
                
                else:
                    api_url = url.replace("tmdb/", "")
            elif kind == "person":
                list_id = splitted[2]
                api_url = f"person/{list_id}/combined_credits"
            elif kind == "search":
                if len(splitted) == 4:
                    pass
                else:
                    query = self.from_keyboard()
                    if query is None:
                        import sys
                        sys.exit()
                    api_url = f"{url.replace('tmdb/', '')}?query={query}"
            else:
                api_url = url.replace("tmdb/", "")
        elif "tmdb_tv_show" in url:
            show_id, _, _ = url.replace("tmdb_tv_show(", "")[:-1].split(",")
            api_url = f"tv/{show_id}"
        elif "tmdb_tv_season" in url:
            show_id, season = url.replace("tmdb_tv_season(", "")[:-1].split(",")
            api_url = f"tv/{show_id}/season/{season}"
        else:
            return False
        tmdb_response = api.get(api_url)
        show_id = None
        if splitted[1] == 'tv':
            if str.isdigit(splitted[2]):
                show_id = splitted[2]     
        jen_list = api.handle_items(tmdb_response, show_id=show_id)
        jen_json = json.dumps(jen_list)
        return jen_json

    def from_keyboard(self, default_text='', header='Search'):
        from xbmc import Keyboard
        kb = Keyboard(default_text, header, False)
        kb.doModal()
        if (kb.isConfirmed()):
            if kb.getText() == '':
                return None
            return kb.getText()
        else:
            return None

tmdb_api = TMDB_API()
