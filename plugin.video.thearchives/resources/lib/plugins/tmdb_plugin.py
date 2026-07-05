import json
import requests
from datetime import date
from urllib.parse import parse_qsl, quote, unquote, urlencode

from ..DI import DI
from ..plugin import Plugin

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *

try:
    from resources.lib.util.history_ui import get_store as get_recent_store
except ImportError:
    get_recent_store = None


ITEMS_PER_PAGE = [20, 40, 60, 80, 100]
PAGES = int(ITEMS_PER_PAGE[int(ownAddon.getSetting("items_per_page"))]/20)


def _is_future_date(value, today=None):
    if not value:
        return False
    try:
        release_date = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    return release_date > (today or date.today())


def _color_future_title(title, release_date, today=None):
    title = str(title or "")
    if not _is_future_date(release_date, today):
        return title
    if title.startswith("[COLOR red]") and title.endswith("[/COLOR]"):
        return title
    return f"[COLOR red]{title}[/COLOR]"


def _remove_repeated_trailing_letters(query: str):
    corrected_words = []
    changed = False
    for word in query.split():
        if (
            len(word) > 2
            and word[-1].isalpha()
            and word[-1].lower() == word[-2].lower()
        ):
            word = word[:-1]
            changed = True
        corrected_words.append(word)
    corrected_query = " ".join(corrected_words)
    if changed and corrected_query != query:
        return corrected_query
    return None


def _get_search_fallback_path(path: str):
    if not path.startswith("search/") or "?query=" not in path:
        return None

    search_path, _, query_string = path.partition("?")
    params = dict(parse_qsl(query_string, keep_blank_values=True))
    query = params.get("query", "")
    fallback_query = _remove_repeated_trailing_letters(query)
    if not fallback_query:
        return None

    params["query"] = fallback_query
    return f"{search_path}?{urlencode(params)}"


def _recent_media_label(media_type):
    return "TV" if media_type == "tv" else "Movie"


def _message_item(title, summary):
    return {
        "type": "plugin",
        "title": title,
        "summary": summary,
    }


def _recent_search_items(media_type):
    if media_type not in ("movie", "tv") or not get_recent_store:
        return []

    searches = get_recent_store().list_recent_searches(media_type)
    label = _recent_media_label(media_type)
    if not searches:
        return [_message_item(
            f"[COLOR khaki][B]No Recent {label} Searches Yet[/B][/COLOR]",
            "Search words will appear here after you use TMDb search.",
        )]

    items = [{
        "type": "dir",
        "title": "[COLOR red]Clear Recent Searches[/COLOR]",
        "link": f"tmdb/clear_recent_searches/{media_type}",
        "summary": f"Clear saved {label.lower()} search words",
    }]
    for query in searches:
        items.append({
            "type": "dir",
            "title": query,
            "link": f"tmdb/search/{media_type}/{quote(query, safe='')}",
            "summary": f"Search {label}: {query}",
        })
    return items


def _clear_recent_searches(media_type):
    if media_type in ("movie", "tv") and get_recent_store:
        get_recent_store().clear_recent_searches(media_type)
    return _recent_search_items(media_type)


def _save_recent_search(media_type, query):
    if media_type in ("movie", "tv") and query and get_recent_store:
        get_recent_store().save_recent_search(media_type, query)


def _genre_summary(media_type, name):
    label = "TV shows" if media_type == "tv" else "movies"
    return f"{name} genre {label}"


def _genre_items(media_type, genres):
    if media_type not in ("movie", "tv"):
        return []
    items = []
    for genre in genres or []:
        genre_id = genre.get("id")
        name = genre.get("name")
        if not genre_id or not name:
            continue
        items.append({
            "type": "dir",
            "title": name,
            "link": f"tmdb/genre/{media_type}/{genre_id}",
            "summary": _genre_summary(media_type, name),
        })
    return items


def _profile_thumbnail(image_url, profile_path):
    if not profile_path:
        return ""
    profile_path = str(profile_path)
    if profile_path.startswith(("http://", "https://")):
        return profile_path
    if not profile_path.startswith("/"):
        profile_path = "/" + profile_path
    return f"{image_url}{profile_path}"


def _cast_member_items(cast, image_url):
    items = []
    for actor in cast or []:
        person_id = actor.get("id")
        name = actor.get("name")
        if not person_id or not name:
            continue
        role = actor.get("character") or actor.get("job") or actor.get("known_for_department") or ""
        items.append({
            "type": "dir",
            "content": "person",
            "title": name,
            "link": f"tmdb/person/{person_id}",
            "thumbnail": _profile_thumbnail(image_url, actor.get("profile_path")),
            "summary": role,
        })
    return items


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

    @property
    def api_key(self):
        return get_tmdb_api_key()

    @property
    def access_token(self):
        return get_tmdb_read_access_token()

    @property
    def account_access_token(self):
        return ownAddon.getSetting("tmdb.token") or self.access_token

    @property
    def account_headers(self):
        return {
            "content-type": "application/json;charset=utf-8",
            "authorization": f"Bearer {self.account_access_token}",
        }

    base_url = "https://api.themoviedb.org"
    image_url = "https://image.tmdb.org/t/p/w500"
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
        request_headers = self.account_headers if version == 4 and self.account_access_token else self.headers
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
            headers=request_headers,
        ).json()
        if  path.startswith("person/"):
            if "cast" in response or "crew" in response:
                results = response.get("cast", [])
                results.extend(response.get("crew", []))
        else:
            results = response.get("results", response.get("parts", response))

        if path.startswith("search/") and not results:
            fallback_path = _get_search_fallback_path(path)
            if fallback_path:
                return self.get(fallback_path, paginated=paginated, full_meta=full_meta, page_count=page_count)
        
        total_pages = response.get("total_pages", 1)
        if total_pages > page:
            if page_count < PAGES:
                results.extend(self.get(f"{path.replace('?with_genres=', '/genre/').replace('?with_networks=', '/network/').replace('?with_companies=', '/company/').replace('?year=', '/year/').replace('?query=', '/')}/{page + 1}", paginated=paginated, full_meta=full_meta,page_count=page_count +1))
            elif page_count == PAGES:
                results.append({"type": "dir", "title": "Next Page", "link": f"tmdb/{path.replace('?with_genres=', '/genre/').replace('?with_networks=', '/network/').replace('?with_companies=', '/company/').replace('?year=', '/year/').replace('?query=', '/')}/{page + 1}"})
            
        return results

    def get_account_lists(self, account_id: str, page: int = 1):
        req = requests.PreparedRequest()
        req.prepare_url(
            f"{self.base_url}/4/account/{account_id}/lists",
            {"page": page}
        )
        response = self.session.get(req.url, headers=self.account_headers).json()
        results = response.get("results", response if isinstance(response, list) else [])
        if response.get("total_pages", 1) > page:
            results.append({"type": "dir", "title": "Next Page", "link": f"tmdb/account/lists/{page + 1}"})
        return results

    def handle_lists_xml(self, lists):
        jen_list = []
        for item in lists or []:
            if item.get("link", "").startswith("tmdb/"):
                jen_list.append(item)
                continue
            list_id = item.get("id")
            if not list_id:
                continue
            item_count = item.get("number_of_items", item.get("item_count", 0)) or 0
            if item_count == 0:
                continue
            name = item.get("name") or item.get("title") or "TMDb List"
            description = item.get("description") or item.get("overview") or ""
            created_by = item.get("created_by", {})
            if isinstance(created_by, dict):
                user = created_by.get("username") or created_by.get("name") or ownAddon.getSetting("tmdb.username") or "TMDb"
            else:
                user = created_by or ownAddon.getSetting("tmdb.username") or "TMDb"
            summary_parts = []
            if description:
                summary_parts.append(description)
            summary_parts.append(f"[B]Author:[/B] {user}")
            jen_list.append({
                "title": f"{name} [I](x{item_count})[/I]",
                "summary": "[CR][CR]".join(summary_parts),
                "type": "dir",
                "link": f"tmdb/list/{list_id}",
            })
        return jen_list

    def get_genres(self, media_type):
        if media_type not in ("movie", "tv"):
            return []
        req = requests.PreparedRequest()
        req.prepare_url(
            f"{self.base_url}/3/genre/{media_type}/list",
            {"api_key": self.api_key, "language": "en-US"}
        )
        response = self.session.get(req.url, headers=self.headers).json()
        return response.get("genres", [])

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
                "title": _color_future_title(item.title, movie.get("release_date")),
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
                        "title": _color_future_title(
                            f"{episode_number}{item.name}", episode.get("air_date")
                        ),
                        "link": "search",
                        "thumbnail": still,
                        "fanart": still,
                        "tmdb_id": item.id,
                        "tv_show_tmdb_id": show_id,
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
                item = objectview(items)
                item.poster_path = poster
                item.backdrop_path = backdrop
                jen_item = {
                    "content": "tvshow",
                    "type": "dir",
                    "link": f"tmdb/tv/{item.id}",
                    "thumbnail": item.poster_path,
                    "fanart": item.backdrop_path,
                    "title": _color_future_title(
                        item.name, items.get("first_air_date")
                    ),
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
        
        genre = [genre.get('name') for genre in items.get('genres', []) if genre.get('name')]
          
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
        
        director = []
        writer = []
        try:
            if media_type == 'episode':
                crew = items['crew']
            else:
                crew = items['credits']['crew']
            for job in crew:
                if job.get('job') == 'Director':
                    director.append(job['name'])
                if job.get('job') == 'Writer' or job.get('job') == 'Screenplay' or job.get('department') == 'Writing':
                    writer.append(job['name'])
        except KeyError:
            pass
        
        rating = items.get('vote_average', 0)
        
        votes = items.get('vote_count', 0) or 0
        
        if media_type == 'movie':
            studio = [studio['name'] for studio in items.get('production_companies', []) if studio.get('name')]
        else:
            studio = [studio['name'] for studio in items.get('networks', []) if studio.get('name')]
            for company in items.get('production_companies', []):
                if company.get('name'):
                    studio.append(company['name'])

        country = [country['name'] for country in items.get('production_countries', []) if country.get('name')]
        
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
                    trailer = f'plugin://plugin.video.thearchives/ytdlp/play/{video_id}'
            if trailer == '':
                for video in videos:
                    if video['type'] == 'Teaser':
                        video_id = video['key']
                        trailer = f'plugin://plugin.video.thearchives/ytdlp/play/{video_id}'
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
            if kind == "account" and len(splitted) > 2 and splitted[2] == "lists":
                if not self.__check_auth():
                    return json.dumps({"items": []})
                page = int(splitted[3]) if len(splitted) > 3 and str.isdigit(splitted[3]) else 1
                account_id = ownAddon.getSetting("tmdb.account_id")
                lists = api.get_account_lists(account_id, page=page)
                return json.dumps({"items": api.handle_lists_xml(lists)})
            if kind == "recent_searches" and len(splitted) > 2:
                return json.dumps({"items": _recent_search_items(splitted[2])})
            if kind == "clear_recent_searches" and len(splitted) > 2:
                return json.dumps({"items": _clear_recent_searches(splitted[2])})
            if kind == "genres" and len(splitted) > 2:
                media_type = splitted[2]
                return json.dumps({"items": _genre_items(media_type, api.get_genres(media_type))})
            if kind == "cast" and len(splitted) > 3:
                media_type = splitted[2]
                media_id = splitted[3]
                if media_type not in ("movie", "tv"):
                    return json.dumps({"items": []})
                details = api.get(f"{media_type}/{media_id}", paginated=False, full_meta=True)
                cast = (details.get("credits") or {}).get("cast", []) if isinstance(details, dict) else []
                return json.dumps({"items": _cast_member_items(cast, api.image_url)})
            if kind == "search":
                media_type = splitted[2] if len(splitted) > 2 else ""
                if len(splitted) >= 4:
                    query = unquote(splitted[3])
                    if len(splitted) >= 5 and str.isdigit(splitted[4]):
                        api_url = f"search/{media_type}/{quote(query, safe='')}/{splitted[4]}"
                    else:
                        api_url = f"search/{media_type}?query={query}"
                else:
                    query = self.from_keyboard()
                    if query is None:
                        import sys
                        sys.exit()
                    api_url = f"{url.replace('tmdb/', '')}?query={query}"
                _save_recent_search(media_type, query)
            elif len(splitted) > 3:
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

    def __check_auth(self):
        if ownAddon.getSetting("tmdb.token") == "" or ownAddon.getSetting("tmdb.account_id") == "":
            xbmcgui.Dialog().ok("TMDb Account", "This action requires a TMDb account. Please authorize TMDb in the addon settings.")
            return False
        return True

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
