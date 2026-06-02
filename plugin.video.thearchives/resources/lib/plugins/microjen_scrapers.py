
from ..plugin import Plugin
from resources.lib.infotagger.helpers import set_video_info
import base64, html, json, re, sys, os, xbmc
import xbmcaddon
import xbmcgui
from urllib.parse import urlencode
try:
    from resources.lib.util.common import *
    from resources.lib.util.source_picker import select_source
except ImportError:
    from .resources.lib.util.common import *
    from .resources.lib.util.source_picker import select_source

try:
    from resources.lib.plugins import alldebrid_client
except ImportError:
    from . import alldebrid_client

debrid_only = ownAddon.getSetting('debrid.only') or 'false'
addon_name = xbmcaddon.Addon().getAddonInfo('name')

DEFAULT_TIMEOUT = 12


class RealDebridApiError(Exception):
    def __init__(self, message, status_code=None, error_code=None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

    @property
    def cache_endpoint_disabled(self):
        return self.error_code == 37


def get_scraper_module_id():
    """Return the addon id of the user-chosen scraper module, or empty string."""
    return ownAddon.getSetting('scraper.module') or ''


def get_scrapers_addon():
    """Return the xbmcaddon.Addon object for the chosen scraper module."""
    module_id = get_scraper_module_id()
    if not module_id:
        return None
    try:
        return xbmcaddon.Addon(module_id)
    except Exception:
        return None


def import_scraper_sources():
    """Import and return the sources() function from the chosen scraper module."""
    module_id = get_scraper_module_id()
    if not module_id:
        xbmcgui.Dialog().ok(addon_name, 'No scraper module selected.\nPlease choose one in Settings > Choose Scraper Module.')
        return None
    module_name = module_id.split('.')[-1]
    try:
        scraper_addon = xbmcaddon.Addon(module_id)
        scraper_path = os.path.join(scraper_addon.getAddonInfo('path'), 'lib')
        if scraper_path not in sys.path:
            sys.path.insert(0, scraper_path)
    except Exception:
        pass
    try:
        mod = __import__(module_name)
        try:
            return mod.sources(specified_folders=['torrents'])
        except TypeError:
            return mod.sources()
    except Exception as e:
        do_log(f'TheArchivesScrapers - Failed to import scraper module {module_id}: {e}')
        xbmcgui.Dialog().ok(addon_name, f'Failed to load scraper module:\n[B]{module_id}[/B]\n\nPlease check it is installed and enabled.')
        return None


class TheArchivesScrapers(Plugin):
    name = "thearchivesscrapers"
    description = "Scrape with chosen Scraper Module"
    priority = 121

    def _play_with_history(self, url, liz, item):
        """Play video with HistoryPlayer for progress/watched tracking."""
        try:
            from resources.lib.plugins.history import HistoryPlayer
            return HistoryPlayer(item).play(url, liz)
        except Exception as e:
            xbmc.log(f"[TheArchives] HistoryPlayer error in scrapers: {e}", xbmc.LOGERROR)
            xbmc.Player().play(url, liz)
            return True

    hostprDict = [
        "1fichier.com",
        "dailyuploads.net",
        "ddl.to",
        "ddownload.com",
        "dropapk.to",
        "earn4files.com",
        "filefactory.com",
        "hexupload.net",
        "mega.io",
        "mega.nz",
        "multiup.org",
        "nitroflare.com",
        "oboom.com",
        "rapidgator.net",
        "rg.to",
        "rockfile.co",
        "rockfile.eu",
        "turbobit.net",
        "ul.to",
        "uploaded.net",
        "uploaded.to",
        "uploadgig.com",
        "uploadrocket.net",
        "usersdrive.com",
    ]
    hostDict = []

    def _get_scrapers_setting_bool(self, setting_id):
        """Safely read a bool setting from the chosen scraper addon."""
        scrapers_addon = get_scrapers_addon()
        if scrapers_addon:
            try:
                value = scrapers_addon.getSetting(setting_id)
                if value == "":
                    return True
                return str(value).lower() not in ("false", "0", "no", "off")
            except Exception:
                pass
        return True

    def play_video(self, item):
        item = json.loads(item)
        link = item.get("link")
        if link and link.startswith("search"):
            sources = import_scraper_sources()
            if sources is None:
                return True
            import concurrent.futures
            import operator
            import time

            self.hostDict = self._host_filters()
            self._cache_check_results = {}
            progress = xbmcgui.DialogProgress()
            all_sources = []
            search_title = re.sub(r"(\[.+?\])", "", item.get("title"))
            do_log(f'{self.name} - search_title = \n' + str(search_title) )  
            
            if item.get("content").lower() == "movie":
                microjen_sources = [(i[0], i[1], getattr(i[1], "movie", None)) for i in sources]
                microjen_sources = list(filter(lambda source: source[2], microjen_sources))
                external_sources = [(i[0], i[1]) for i in sources if self._is_data_source(i[1])]
                all_sources = []
                num_sources = len(microjen_sources) + len(external_sources)
                counter = 0
                progress.create(
                    f"{addon_name}",
                    f"Scraping for {item.get('title')}\n[I][COLOR orange](Sources : {num_sources - counter} / {num_sources} left)[/I][COLOR white] > [COLOR lawngreen]{len(all_sources)} links found[/COLOR]",
                )
                threads = [
                    self.get_movie_source(
                        search_title,
                        item.get("year"),
                        item.get("imdb_id"),
                        i[0],
                        i[1],
                    )
                    for i in microjen_sources
                ]
                threads += [
                    self.get_data_movie_source(
                        search_title,
                        item.get("year"),
                        item.get("imdb_id"),
                        i[0],
                        i[1],
                    )
                    for i in external_sources
                ]
                for t in threads:
                    t[0].start()
                end_time = self._scrape_timeout() + time.monotonic()
                while True:
                    if not threads:
                        break
                    for t in threads:
                        if progress.iscanceled():
                            break
                        wait_timeout = end_time - time.monotonic()
                        if wait_timeout < 0:
                            break
                        if t[0].is_alive():
                            continue
                        else:
                            result = t[1]
                            threads.remove(t)
                            if result:
                                all_sources.extend(result)
                            counter += 1
                            percent = int((counter / num_sources) * 100) if num_sources else 100
                            progress.update(
                                percent,
                                f"Scraping for {item.get('title')}\n[I][COLOR orange](Sources : {num_sources - counter} / {num_sources} left)[/I][COLOR white] > [COLOR lawngreen]{len(all_sources)} links found[/COLOR]",
                            )
                    else:
                        continue
                    break
                progress.close()
                all_sources = list(filter(lambda source: source, all_sources))
            elif item.get("content").lower() == "episode":
                microjen_sources = [(i[0], i[1], getattr(i[1], "tvshow", None)) for i in sources]
                microjen_sources = list(filter(lambda source: source[2], microjen_sources))
                external_sources = [(i[0], i[1]) for i in sources if self._is_data_source(i[1])]
                all_sources = []
                num_sources = len(microjen_sources) + len(external_sources)
                counter = 0
                name = f'{item.get("tv_show_title")} - S{item.get("season")}E{item.get("episode")}'
                progress.create(
                    f"{addon_name}",
                    f"Scraping for {item.get('title')}\n[I][COLOR orange](Sources : {num_sources - counter} / {num_sources} left)[/I][COLOR white] > [COLOR lawngreen]{len(all_sources)} links found[/COLOR]",
                )
                threads = [
                    self.get_episode_source(
                        item.get("title"),
                        item.get("tv_show_title"),
                        item.get("year"),
                        item.get("imdb_id"),
                        item.get("tmdb_id"),
                        item.get("premiered"),
                        item.get("season"),
                        item.get("episode"),
                        i[0],
                        i[1],
                    )
                    for i in microjen_sources
                ]
                threads += [
                    self.get_data_episode_source(
                        item.get("title"),
                        item.get("tv_show_title"),
                        item.get("year"),
                        item.get("imdb_id"),
                        item.get("tmdb_id"),
                        item.get("tvdb_id"),
                        item.get("season"),
                        item.get("episode"),
                        i[0],
                        i[1],
                    )
                    for i in external_sources
                ]
                for t in threads:
                    t[0].start()
                end_time = self._scrape_timeout() + time.monotonic()
                while True:
                    if not threads:
                        break
                    for t in threads:
                        if progress.iscanceled():
                            break
                        wait_timeout = end_time - time.monotonic()
                        if wait_timeout < 0:
                            break
                        if t[0].is_alive():
                            continue
                        else:
                            result = t[1]
                            threads.remove(t)
                            if result:
                                all_sources.extend(result)
                            counter += 1
                            percent = int((counter / num_sources) * 100) if num_sources else 100
                            progress.update(
                                percent,
                                f"Scraping for {item.get('title')}\n[I][COLOR orange](Sources : {num_sources - counter} / {num_sources} left)[/I][COLOR white] > [COLOR lawngreen]{len(all_sources)} links found[/COLOR]",
                            )
                    else:
                        continue
                    break
                progress.close()
                all_sources = list(filter(lambda source: source, all_sources))

            easynews_sources = self._get_easynews_sources(item)
            if easynews_sources:
                all_sources.extend(easynews_sources)

            if not all_sources:
                xbmcgui.Dialog().notification(addon_name, 'No scraper sources found', xbmcaddon.Addon().getAddonInfo('icon'), 3000, sound=False)
                return True

            all_sources = sorted(all_sources, key=lambda source: str(source.get("quality", "")))
            try:
                if self._get_scrapers_setting_bool("quality.4k") is False:
                    all_sources = [source for source in all_sources if not str(source.get("quality", "")).lower().replace(".", "") == "4k"]
                if self._get_scrapers_setting_bool("quality.1080p") is False:
                    all_sources = [source for source in all_sources if not str(source.get("quality", "")).lower() == "1080p"]
                if self._get_scrapers_setting_bool("quality.720p") is False:
                    all_sources = [source for source in all_sources if not str(source.get("quality", "")).lower() == "720p"]
                if self._get_scrapers_setting_bool("quality.sd") is False:
                    all_sources = [source for source in all_sources if not str(source.get("quality", "")).lower() == "sd"]
                if self._get_scrapers_setting_bool("quality.cam") is False:
                    all_sources = [source for source in all_sources if not str(source.get("quality", "")).lower() == "cam"]
            except:
                pass

            all_sources = self._prepare_source_results(all_sources)
            cache_summary = f'{self.name} - playable sources after filtering: {len(all_sources)}'
            do_log(cache_summary)
            xbmc.log(f'TheArchivesScrapers - {cache_summary}', getattr(xbmc, 'LOGINFO', 1))
            if not all_sources:
                xbmcgui.Dialog().notification(addon_name, 'No playable sources found', xbmcaddon.Addon().getAddonInfo('icon'), 3000, sound=False)
                return True

            play_sources = self._source_display_labels(all_sources)
            selected = select_source(all_sources, play_sources, item)
            if not selected == -1:
                default_icon = xbmcaddon.Addon().getAddonInfo('icon')
                title = item["title"]
                thumbnail = item.get("thumbnail", default_icon)
                plot = item.get("summary", "")
                liz = xbmcgui.ListItem(title)
                set_video_info(liz, {'title': title, 'plot': plot})
                liz.setArt({'thumb': thumbnail, 'icon': thumbnail})

                selected_source = all_sources[selected]
                source_url = selected_source.get("url", "")
                if self._is_magnet_url(source_url):
                    url = self._resolve_magnet_source(selected_source, item)
                    if url:
                        self._play_with_history(url, liz, item)
                        return True
                    xbmcgui.Dialog().notification(addon_name, 'Unable to resolve selected magnet with enabled debrid services', xbmcaddon.Addon().getAddonInfo('icon'), 3000, sound=False)
                    return True

                if selected_source.get("direct") or self._is_direct_playable_url(source_url):
                    self._play_with_history(source_url, liz, item)
                    return True
                else:
                    xbmcgui.Dialog().notification(addon_name, 'Selected source is not directly playable without a resolver', xbmcaddon.Addon().getAddonInfo('icon'), 3000, sound=False)
                    return True
            else:
                return True
    
    def routes(self, plugin):
        @plugin.route(f"/{self.name}/play/<path:query>")
        def play(query):
            q = query.split("|")
            item = {"title": q[1], "content": q[0], "imdb_id": q[2], "year": q[3], "link": "search"}
            self.play_video(json.dumps(item))

    def _log_provider_failure(self, source_name, error):
        xbmc.log(
            f'TheArchivesScrapers - provider {source_name} failed: {error}',
            getattr(xbmc, 'LOGERROR', 4),
        )

    def get_movie_source(self, title, year, imdb, source_name, source_object):
        from threading import Thread

        result = []
        thread = Thread(
            target=self._get_movie_source_threaded,
            args=(
                title,
                year,
                imdb,
                source_name,
                source_object,
                result,
            ),
        )
        return (thread, result)

    def _get_movie_source_threaded(
        self, title, year, imdb, source_name, source_object, outlist
    ):
        try:
            url = source_object.movie(imdb, title, title, "", year)
            sources = source_object.sources(url, self.hostDict, self.hostprDict)
            if sources:
                for item in sources:
                    item["origin"] = source_name
                outlist.extend(sources)
            return sources
        except Exception as e:
            self._log_provider_failure(source_name, e)
            return []

    def get_episode_source(
        self,
        title,
        tv_show_title,
        year,
        imdb,
        tmdb,
        premiered,
        season,
        episode,
        source_name,
        source_object,
    ):
        from threading import Thread

        result = []
        thread = Thread(
            target=self._get_episode_source_threaded,
            args=(
                title,
                tv_show_title,
                year,
                imdb,
                tmdb,
                premiered,
                season,
                episode,
                source_name,
                source_object,
                result,
            ),
        )
        return (thread, result)

    def _get_episode_source_threaded(
        self,
        title,
        tv_show_title,
        year,
        imdb,
        tmdb,
        premiered,
        season,
        episode,
        source_name,
        source_object,
        outlist,
    ):
        try:
            tv_show_url = source_object.tvshow(
                imdb, tmdb, tv_show_title, tv_show_title, "", year
            )
            episode_url = source_object.episode(
                tv_show_url, imdb, tmdb, title, premiered, season, episode
            )
            sources = source_object.sources(episode_url, self.hostDict, self.hostprDict)
            if sources:
                for item in sources:
                    item["origin"] = source_name
                outlist.extend(sources)
            return sources
        except Exception as e:
            self._log_provider_failure(source_name, e)
            return []

    def _is_data_source(self, source_object):
        return callable(getattr(source_object, "sources", None)) and not callable(getattr(source_object, "movie", None)) and not callable(getattr(source_object, "tvshow", None))

    def get_data_movie_source(self, title, year, imdb, source_name, source_object):
        from threading import Thread

        result = []
        thread = Thread(
            target=self._get_data_movie_source_threaded,
            args=(title, year, imdb, source_name, source_object, result),
        )
        return (thread, result)

    def _get_data_movie_source_threaded(
        self, title, year, imdb, source_name, source_object, outlist
    ):
        data = {
            "imdb": imdb or "",
            "title": title or "",
            "aliases": [],
            "year": str(year or ""),
        }
        try:
            sources = source_object().sources(data, self.hostDict)
            sources = self._normalize_data_sources(source_name, sources)
            if sources:
                outlist.extend(sources)
            return sources
        except Exception as e:
            self._log_provider_failure(source_name, e)
            return []

    def get_data_episode_source(
        self,
        title,
        tv_show_title,
        year,
        imdb,
        tmdb,
        tvdb,
        season,
        episode,
        source_name,
        source_object,
    ):
        from threading import Thread

        result = []
        thread = Thread(
            target=self._get_data_episode_source_threaded,
            args=(title, tv_show_title, year, imdb, tmdb, tvdb, season, episode, source_name, source_object, result),
        )
        return (thread, result)

    def _get_data_episode_source_threaded(
        self,
        title,
        tv_show_title,
        year,
        imdb,
        tmdb,
        tvdb,
        season,
        episode,
        source_name,
        source_object,
        outlist,
    ):
        data = {
            "imdb": imdb or "",
            "tmdb": tmdb or "",
            "tvdb": tvdb or "",
            "tvshowtitle": tv_show_title or "",
            "aliases": [],
            "year": str(year or ""),
            "title": title or "",
            "season": str(season or ""),
            "episode": str(episode or ""),
        }
        try:
            sources = source_object().sources(data, self.hostDict)
            sources = self._normalize_data_sources(source_name, sources)
            if sources:
                outlist.extend(sources)
            return sources
        except Exception as e:
            self._log_provider_failure(source_name, e)
            return []

    def _normalize_data_sources(self, source_name, sources):
        normalized = []
        for item in sources or []:
            item = dict(item)
            item["origin"] = item.get("provider") or source_name
            item["source"] = item.get("source") or item.get("provider") or source_name
            item["quality"] = item.get("quality") or "SD"
            item["info"] = item.get("info") or item.get("name") or item.get("size_label") or "Size Unknown"
            item["direct"] = item.get("direct", False)
            normalized.append(item)
        return normalized

    def _is_magnet_url(self, url):
        return str(url or "").lower().startswith("magnet:")

    def _is_direct_playable_url(self, url):
        clean_url = str(url or "").lower().split("|", 1)[0].split("?", 1)[0]
        return clean_url.startswith(("http://", "https://")) and clean_url.endswith((".m3u8", ".mpd", ".mp4", ".mkv", ".avi", ".mov", ".m4v", ".ts", ".wmv", ".flv", ".webm"))

    def _scrape_timeout(self):
        try:
            timeout = int(ownAddon.getSetting("results.timeout") or DEFAULT_TIMEOUT)
        except Exception:
            timeout = DEFAULT_TIMEOUT
        return max(5, min(timeout, 120))

    def _host_filters(self):
        return []

    def _get_easynews_sources(self, item):
        if str(ownAddon.getSetting("provider.easynews") or "").lower() != "true":
            return []
        username = ownAddon.getSetting("easynews.username") or ""
        password = ownAddon.getSetting("easynews.password") or ""
        if not username or not password:
            do_log(f'{self.name} - Easynews enabled but username/password is missing')
            return []
        query = self._easynews_query(item)
        if not query:
            return []
        try:
            return self._easynews_search(query, username, password)
        except Exception as e:
            do_log(f'{self.name} - Easynews search failed: {e}')
            xbmc.log(f'TheArchivesScrapers - Easynews search failed: {e}', getattr(xbmc, 'LOGERROR', 4))
            return []

    def _easynews_query(self, item):
        content = str(item.get("content") or "").lower()
        if content == "episode":
            show = item.get("tv_show_title") or item.get("title") or ""
            try:
                season = int(item.get("season") or 0)
                episode = int(item.get("episode") or 0)
                if show and season and episode:
                    return f"{show} S{season:02d}E{episode:02d}"
            except Exception:
                pass
            return " ".join([str(value) for value in (show, item.get("season"), item.get("episode")) if value])
        title = re.sub(r"(\[.+?\])", "", item.get("title") or "").strip()
        year = str(item.get("year") or "").strip()
        return f"{title} {year}".strip()

    def _easynews_search(self, query, username, password):
        import requests
        from urllib.parse import quote_plus

        extensions = "m4v,3gp,mov,divx,xvid,wmv,avi,mpg,mpeg,mp4,mkv,avc,flv,webm"
        url = (
            "https://members.easynews.com/2.0/search/solr-search/advanced"
            "?st=adv&sb=1&fex=%s&fty[]=VIDEO&spamf=1&u=1&gx=1&pno=1"
            "&sS=3&s1=dsize&s1d=-&s2=relevance&s2d=-&s3=dtime&s3d=-"
            "&pby=50&safeO=0&gps=%s"
        ) % (extensions, quote_plus(query))
        response = requests.get(
            url,
            auth=(username, password),
            headers={"User-Agent": "Kodi TheArchives"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        results = []
        for row in payload.get("data") or []:
            item = self._easynews_source_item(payload, row, username, password)
            if item:
                results.append(item)
        do_log(f'{self.name} - Easynews query "{query}" returned {len(results)} playable sources')
        xbmc.log(f'TheArchivesScrapers - Easynews returned {len(results)} playable sources', getattr(xbmc, 'LOGINFO', 1))
        return results

    def _easynews_source_item(self, payload, row, username, password):
        from urllib.parse import quote

        if row.get("passwd") or row.get("password") or row.get("virus"):
            return None
        source_url = self._easynews_stream_url(payload, row, quote)
        if not source_url:
            return None
        if not self._is_direct_playable_url(source_url):
            return None
        auth = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        stream_url = f"{source_url}|Authorization={quote('Basic ' + auth, safe='')}&User-Agent=Kodi%20TheArchives"
        title = html.unescape(row.get("fn") or row.get("10") or row.get("subject") or "Easynews")
        size = row.get("rawSize") or row.get("size") or row.get("4") or 0
        quality = self._easynews_quality(row, title)
        return {
            "provider": "Easynews",
            "origin": "Easynews",
            "source": "usenet",
            "quality": quality,
            "info": self._format_size(size),
            "size": size,
            "name": title,
            "url": stream_url,
            "direct": True,
            "debrid_cached": False,
        }

    def _easynews_stream_url(self, payload, row, quote):
        down_url = str(payload.get("downURL") or "https://members.easynews.com/dl").rstrip("/")
        dl_farm = str(payload.get("dlFarm") or "auto").strip("/")
        dl_port = str(payload.get("dlPort") or "443").strip("/")
        post_hash = str(row.get("0") or row.get("hash") or "").strip()
        post_title = str(row.get("10") or row.get("fn") or "").strip()
        extension = str(row.get("11") or row.get("extension") or row.get("2") or "").strip()
        if not post_hash or not post_title or not extension:
            return ""
        if not extension.startswith("."):
            extension = "." + extension
        file_id = quote(f"{post_hash}{extension}", safe="")
        file_name = quote(f"{post_title}{extension}", safe="")
        return f"{down_url}/{dl_farm}/{dl_port}/{file_id}/{file_name}"

    def _easynews_quality(self, row, title):
        height = str(row.get("yres") or row.get("height") or "")
        if height:
            try:
                value = int(float(height))
                if value >= 2160:
                    return "4K"
                if value >= 1080:
                    return "1080p"
                if value >= 720:
                    return "720p"
            except Exception:
                pass
        name = str(title or "").lower()
        if "2160" in name or "4k" in name:
            return "4K"
        if "1080" in name:
            return "1080p"
        if "720" in name:
            return "720p"
        return "SD"

    def _format_size(self, value):
        try:
            size = float(value)
        except Exception:
            match = re.search(r"(\d+(?:\.\d+)?)\s*([kmgt]?b)", str(value), re.I)
            return match.group(0).upper() if match else "Size Unknown"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
            size /= 1024
        return "Size Unknown"

    def _prepare_source_results(self, sources):
        prepared = []
        seen = set()
        rejected_uncached = 0
        rejected_unplayable = 0
        duplicates = 0
        normalized_sources = [self._normalize_source_item(source) for source in sources or []]
        self._prime_cache_checks(normalized_sources)
        for item in normalized_sources:
            source_url = item.get("url", "")
            if self._is_magnet_url(source_url):
                cached_service = self._cached_debrid_service_for_source(item)
                uncached_service = None
                if cached_service:
                    item["debrid_cached"] = True
                    item["debrid_service"] = cached_service["name"]
                    item["cached_service_id"] = cached_service["id"]
                else:
                    uncached_service = self._uncached_debrid_service_for_source()
                if not cached_service and not uncached_service:
                    rejected_uncached += 1
                    continue
                if uncached_service:
                    item["debrid_cached"] = False
                    item["debrid_uncached"] = True
                    item["debrid_service"] = uncached_service["name"]
                    item["cached_service_id"] = uncached_service["id"]
            elif not item.get("debrid_cached") and not item.get("direct") and not self._is_direct_playable_url(source_url):
                rejected_unplayable += 1
                continue

            key = self._source_dedupe_key(item)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            prepared.append(item)
        provider_counts = {}
        for item in prepared:
            provider = item.get("origin") or "Unknown"
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        summary = f'{self.name} - source filter kept={len(prepared)} providers={provider_counts} uncached={rejected_uncached} unplayable={rejected_unplayable} duplicates={duplicates}'
        do_log(summary)
        xbmc.log(f'TheArchivesScrapers - {summary}', getattr(xbmc, 'LOGINFO', 1))
        return sorted(prepared, key=self._source_sort_key)

    def _prime_cache_checks(self, items):
        if not hasattr(self, "_cache_check_results"):
            self._cache_check_results = {}
        pending = []
        for item in items or []:
            if self._source_marked_cached(item):
                continue
            source_url = item.get("url", "")
            if not self._is_magnet_url(source_url):
                continue
            source_hash = self._source_hash(item)
            if not source_hash and not source_url:
                continue
            key_value = source_hash.lower() if source_hash else source_url.lower()
            pending.append((source_url, source_hash, key_value))
        if not pending:
            return
        total_checks = 0
        already_cached = set()
        for service in self._enabled_debrid_services():
            if service.get("cached_only") is False:
                continue
            entries = []
            seen = set()
            for source_url, source_hash, key_value in pending:
                if key_value in already_cached:
                    continue
                cache_key = (service["id"], key_value)
                if cache_key in self._cache_check_results or cache_key in seen:
                    continue
                seen.add(cache_key)
                entries.append((cache_key, source_url, source_hash))
            if not entries:
                continue
            results = self._batch_check_cached_with_service(service, entries)
            for cache_key, cached in results.items():
                self._cache_check_results[cache_key] = cached
                if cached:
                    already_cached.add(cache_key[1])
            for cache_key, _source_url, _source_hash in entries:
                self._cache_check_results.setdefault(cache_key, False)
            total_checks += len(entries)
        if total_checks:
            xbmc.log(f'TheArchivesScrapers - batched debrid cache checks for {total_checks} hashes/links', getattr(xbmc, 'LOGINFO', 1))

    def _batch_check_cached_with_service(self, service, entries):
        try:
            if service["id"] == "rd":
                return self._real_debrid_cached_batch(service["token"], entries)
            if service["id"] == "pm":
                return self._premiumize_cached_batch(service["token"], entries)
            if service["id"] == "ad":
                return self._all_debrid_cached_batch(service["token"], entries)
            if service["id"] == "tb":
                return self._torbox_cached_batch(service["token"], entries)
        except RealDebridApiError as e:
            if service["id"] == "rd" and e.cache_endpoint_disabled:
                self._mark_debrid_cache_check_unavailable(service["id"])
                msg = 'Real-Debrid cache check endpoint is disabled; falling back to uncached magnet resolution'
                do_log(f'{self.name} - {msg}')
                xbmc.log(f'TheArchivesScrapers - {msg}', getattr(xbmc, 'LOGERROR', 4))
            else:
                do_log(f'{self.name} - {service["name"]} batch cache check failed: {e}')
                xbmc.log(f'TheArchivesScrapers - {service["name"]} batch cache check failed: {e}', getattr(xbmc, 'LOGERROR', 4))
        except Exception as e:
            do_log(f'{self.name} - {service["name"]} batch cache check failed: {e}')
            xbmc.log(f'TheArchivesScrapers - {service["name"]} batch cache check failed: {e}', getattr(xbmc, 'LOGERROR', 4))
        return {cache_key: False for cache_key, _source_url, _source_hash in entries}

    def _normalize_source_item(self, source):
        item = dict(source or {})
        item["origin"] = item.get("origin") or item.get("provider") or item.get("name") or "Unknown"
        item["source"] = item.get("source") or item.get("provider") or item.get("origin") or "Unknown"
        item["quality"] = self._normalize_quality(item.get("quality"))
        item["info"] = item.get("info") or item.get("size_label") or item.get("size") or item.get("name") or "Size Unknown"
        item["url"] = item.get("url") or item.get("link") or item.get("url_dl") or ""
        item["seeders"] = item.get("seeders") or item.get("seeds") or item.get("seed") or ""
        cached_service = self._source_marked_cached(item)
        if cached_service:
            item["debrid_cached"] = True
            item["debrid_service"] = cached_service["name"]
            item["cached_service_id"] = cached_service["id"]
        return item

    def _normalize_quality(self, quality):
        quality = str(quality or "SD").replace(".", "").strip()
        if quality.lower() == "sd":
            return "SD"
        if quality.lower() == "cam":
            return "CAM"
        if quality.lower() in ("4k", "2160p"):
            return "4K"
        return quality

    def _source_display_labels(self, sources):
        return [self._source_display_label(item) for item in sources]

    def _source_display_label(self, item):
        service = item.get("debrid_service") or "Debrid"
        if item.get("debrid_cached"):
            cache_label = f"{service} Cached"
        elif item.get("debrid_uncached"):
            cache_label = f"{service} Uncached"
        elif item.get("direct") or self._is_direct_playable_url(item.get("url", "")):
            cache_label = "Direct"
        else:
            cache_label = service
        parts = [
            str(item.get("origin") or "Unknown"),
            str(item.get("quality") or "SD").replace(".", ""),
            cache_label,
            str(item.get("info") or "Size Unknown"),
        ]
        seeders = item.get("seeders")
        if seeders not in ("", None):
            parts.append(f"S:{seeders}")
        parts.append(str(item.get("source") or "Unknown"))
        return " | ".join(parts)

    def _source_sort_key(self, item):
        return (
            self._quality_rank(item.get("quality")),
            0 if item.get("debrid_cached") else 1,
            -self._size_from_source(item),
            str(item.get("origin") or "").lower(),
        )

    def _quality_rank(self, quality):
        value = str(quality or "").lower().replace(".", "")
        if value in ("4k", "2160p"):
            return 0
        if value == "1080p":
            return 1
        if value == "720p":
            return 2
        if value == "sd":
            return 3
        if value == "cam":
            return 4
        return 5

    def _size_from_source(self, item):
        value = item.get("size") or item.get("size_bytes") or item.get("filesize") or item.get("info") or 0
        if isinstance(value, (int, float)):
            return float(value)
        match = re.search(r"(\d+(?:\.\d+)?)\s*([kmgt]?b)", str(value), re.I)
        if not match:
            return 0
        number = float(match.group(1))
        unit = match.group(2).lower()
        multiplier = {"kb": 1024, "mb": 1024 ** 2, "gb": 1024 ** 3, "tb": 1024 ** 4}.get(unit, 1)
        return number * multiplier

    def _source_dedupe_key(self, item):
        source_hash = self._source_hash(item)
        if source_hash:
            provider = item.get("origin") or item.get("provider") or item.get("source") or ""
            return f"hash:{str(provider).lower()}:{source_hash.lower()}"
        return str(item.get("url") or item.get("origin") or "").lower()

    def _source_hash(self, item):
        source_hash = item.get("hash") or item.get("btih") or item.get("info_hash")
        if source_hash:
            return str(source_hash).strip()
        match = re.search(r"btih:([a-z0-9]{32,40})", str(item.get("url") or ""), re.I)
        return match.group(1) if match else ""

    def _source_marked_cached(self, item):
        cached_value = None
        for key in ("debrid_cached", "cached", "is_cached", "cache"):
            if key in item:
                cached_value = item.get(key)
                break
        if isinstance(cached_value, str):
            cached_value = cached_value.lower() in ("true", "1", "yes", "cached")
        if cached_value is False:
            return None
        service = item.get("debrid_service") or item.get("cache_provider") or item.get("debrid")
        if cached_value or service:
            return self._service_from_name(service) or {"id": "", "name": str(service or "Debrid")}
        for key, service_id in (("rd", "rd"), ("real_debrid", "rd"), ("pm", "pm"), ("premiumize", "pm"), ("ad", "ad"), ("alldebrid", "ad"), ("tb", "tb"), ("torbox", "tb")):
            if str(item.get(key, "")).lower() in ("true", "1", "yes", "cached"):
                return self._service_from_id(service_id)
        return None

    def _cached_debrid_service_for_source(self, item):
        marked = self._source_marked_cached(item)
        if marked:
            return marked
        source_hash = self._source_hash(item)
        source_url = item.get("url", "")
        if not source_hash and not source_url:
            return None
        if not hasattr(self, "_cache_check_results"):
            self._cache_check_results = {}
        for service in self._enabled_debrid_services():
            if service.get("cached_only") is False:
                continue
            cache_key = (service["id"], source_hash.lower() if source_hash else source_url.lower())
            if cache_key not in self._cache_check_results:
                self._cache_check_results[cache_key] = self._check_cached_with_service(service, source_url, source_hash)
            if self._cache_check_results[cache_key]:
                return service
        return None

    def _uncached_debrid_service_for_source(self):
        for service in self._enabled_debrid_services():
            if service.get("cached_only") is False or self._debrid_cache_check_unavailable(service["id"]):
                return service
        return None

    def _check_cached_with_service(self, service, source_url, source_hash):
        try:
            if service["id"] == "rd":
                return self._real_debrid_cached(service["token"], source_hash)
            if service["id"] == "pm":
                return self._premiumize_cached(service["token"], source_url, source_hash)
            if service["id"] == "ad":
                return self._all_debrid_cached(service["token"], source_url, source_hash)
            if service["id"] == "tb":
                return self._torbox_cached(service["token"], source_hash)
        except RealDebridApiError as e:
            if service["id"] == "rd" and e.cache_endpoint_disabled:
                self._mark_debrid_cache_check_unavailable(service["id"])
                do_log(f'{self.name} - Real-Debrid cache check endpoint is disabled; using uncached fallback')
            else:
                do_log(f'{self.name} - {service["name"]} cache check failed: {e}')
        except Exception as e:
            do_log(f'{self.name} - {service["name"]} cache check failed: {e}')
        return False

    def _real_debrid_cached(self, token, source_hash):
        if not source_hash:
            return False
        data = self._real_debrid_api_request("get", f"torrents/instantAvailability/{source_hash}", token, timeout=15)
        result = data.get(source_hash.lower()) or data.get(source_hash.upper()) or data.get(source_hash)
        return bool(result)

    def _real_debrid_cached_batch(self, token, entries):
        results = {cache_key: False for cache_key, _source_url, _source_hash in entries}
        hash_entries = [(cache_key, source_hash) for cache_key, _source_url, source_hash in entries if source_hash]
        for index in range(0, len(hash_entries), 50):
            chunk = hash_entries[index:index + 50]
            hashes = [source_hash for _cache_key, source_hash in chunk]
            endpoint = "torrents/instantAvailability/" + "/".join(hashes)
            data = self._real_debrid_api_request("get", endpoint, token, timeout=15)
            for cache_key, source_hash in chunk:
                result = data.get(source_hash.lower()) or data.get(source_hash.upper()) or data.get(source_hash)
                results[cache_key] = bool(result)
        return results

    def _premiumize_cached(self, token, source_url, source_hash=""):
        item = source_hash or source_url
        if not item:
            return False
        import requests
        response = requests.post(
            "https://www.premiumize.me/api/cache/check",
            data={"items[]": [item]},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        ).json()
        values = response.get("response") or []
        return bool(values and values[0])

    def _premiumize_cached_batch(self, token, entries):
        import requests
        results = {cache_key: False for cache_key, _source_url, _source_hash in entries}
        for index in range(0, len(entries), 100):
            chunk = entries[index:index + 100]
            items = [(source_hash or source_url) for _cache_key, source_url, source_hash in chunk]
            response = requests.post(
                "https://www.premiumize.me/api/cache/check",
                data={"items[]": items},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            ).json()
            values = response.get("response") or []
            for entry, cached in zip(chunk, values):
                results[entry[0]] = bool(cached)
        return results

    def _all_debrid_cached(self, token, source_url, source_hash):
        magnet = source_url or source_hash
        if not magnet:
            return False
        import requests
        data = alldebrid_client.api_post(
            requests,
            "magnet/instant",
            token,
            {"magnets[]": magnet},
            timeout=15,
        )
        magnets = data.get("magnets", [])
        if isinstance(magnets, dict):
            magnets = list(magnets.values())
        return any(bool(item.get("instant") or item.get("cached")) for item in magnets if isinstance(item, dict))

    def _all_debrid_cached_batch(self, token, entries):
        import requests
        results = {cache_key: False for cache_key, _source_url, _source_hash in entries}
        for index in range(0, len(entries), 100):
            chunk = entries[index:index + 100]
            magnets = [(source_url or source_hash) for _cache_key, source_url, source_hash in chunk]
            data = alldebrid_client.api_post(
                requests,
                "magnet/instant",
                token,
                {"magnets[]": magnets},
                timeout=15,
            )
            response_items = data.get("magnets", [])
            if isinstance(response_items, dict):
                response_items = list(response_items.values())
            for entry, response_item in zip(chunk, response_items):
                if isinstance(response_item, dict):
                    results[entry[0]] = bool(response_item.get("instant") or response_item.get("cached"))
        return results

    def _torbox_cached(self, token, source_hash):
        if not source_hash:
            return False
        import requests
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            "https://api.torbox.app/v1/api/torrents/checkcached",
            params={"hash": source_hash, "format": "list"},
            headers=headers,
            timeout=15,
        ).json()
        data = response.get("data", response)
        return bool(data)

    def _torbox_cached_batch(self, token, entries):
        return {
            cache_key: self._torbox_cached(token, source_hash)
            for cache_key, _source_url, source_hash in entries
            if source_hash
        }

    def _service_from_name(self, name):
        name = str(name or "").lower()
        if not name:
            return None
        for service_id, service_name in (("rd", "Real-Debrid"), ("pm", "Premiumize"), ("ad", "AllDebrid"), ("tb", "TorBox")):
            if service_id == name or service_name.lower() in name or name in service_name.lower():
                return {"id": service_id, "name": service_name}
        return None

    def _service_from_id(self, service_id):
        names = {"rd": "Real-Debrid", "pm": "Premiumize", "ad": "AllDebrid", "tb": "TorBox"}
        return {"id": service_id, "name": names.get(service_id, service_id)}

    def _resolve_magnet_source(self, source_item, media_item):
        resolvers = {
            "pm": self._resolve_premiumize_magnet,
            "rd": self._resolve_real_debrid_magnet,
            "ad": self._resolve_all_debrid_magnet,
            "tb": self._resolve_torbox_magnet,
        }
        services = self._enabled_debrid_services()
        if not services:
            xbmcgui.Dialog().notification(addon_name, 'Enable and authorize a debrid service to play torrent sources', xbmcaddon.Addon().getAddonInfo('icon'), 3000, sound=False)
            return None
        preferred_service = source_item.get("cached_service_id")
        if preferred_service:
            services = sorted(services, key=lambda item: item["id"] != preferred_service)
        for service in services:
            try:
                url = resolvers[service["id"]](source_item, media_item, service["token"])
                if url:
                    return url
            except RealDebridApiError as e:
                message = f'{service["name"]} magnet resolve failed: {e}'
                do_log(f'{self.name} - {message}')
                xbmc.log(f'TheArchivesScrapers - {message}', getattr(xbmc, 'LOGERROR', 4))
            except Exception as e:
                do_log(f'{self.name} - {service["name"]} magnet resolve failed: {e}')
        return None

    def _enabled_debrid_services(self):
        services = []
        for service_id, name in (("rd", "Real-Debrid"), ("pm", "Premiumize"), ("ad", "AllDebrid"), ("tb", "TorBox")):
            enabled = str(ownAddon.getSetting(f"{service_id}.enabled") or "").lower() == "true"
            token = ownAddon.getSetting(f"{service_id}.token") or ""
            if not enabled or not token:
                continue
            try:
                priority = int(ownAddon.getSetting(f"{service_id}.priority") or 10)
            except Exception:
                priority = 10
            services.append({"id": service_id, "name": name, "token": token, "priority": priority, "cached_only": self._service_cached_only(service_id)})
        return sorted(services, key=lambda item: item["priority"])

    def _service_cached_only(self, service_id):
        value = ownAddon.getSetting(f"{service_id}.cached_only")
        if value == "":
            return True
        return str(value).lower() not in ("false", "0", "no", "off")

    def _mark_debrid_cache_check_unavailable(self, service_id):
        if not hasattr(self, "_debrid_cache_check_unavailable_services"):
            self._debrid_cache_check_unavailable_services = set()
        self._debrid_cache_check_unavailable_services.add(service_id)

    def _debrid_cache_check_unavailable(self, service_id):
        unavailable = getattr(self, "_debrid_cache_check_unavailable_services", set())
        return service_id in unavailable

    def _refresh_real_debrid_token(self):
        client_id = ownAddon.getSetting("rd.client_id") or ""
        client_secret = ownAddon.getSetting("rd.secret") or ""
        refresh_token = ownAddon.getSetting("rd.refresh") or ""
        if not client_id or not client_secret or not refresh_token:
            do_log(f'{self.name} - Real-Debrid token refresh skipped; missing OAuth credentials')
            return ""
        import requests
        response = requests.post(
            "https://api.real-debrid.com/oauth/v2/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": refresh_token,
                "grant_type": "http://oauth.net/grant_type/device/1.0",
            },
            timeout=15,
        )
        try:
            data = response.json()
        except Exception:
            data = {}
        if getattr(response, "status_code", 200) >= 400 or not data.get("access_token"):
            error = data.get("error") or data.get("error_description") or getattr(response, "text", "")
            xbmc.log(f'TheArchivesScrapers - Real-Debrid token refresh failed: {error}', getattr(xbmc, 'LOGERROR', 4))
            return ""
        ownAddon.setSetting("rd.token", data.get("access_token", ""))
        if data.get("refresh_token"):
            ownAddon.setSetting("rd.refresh", data.get("refresh_token", ""))
        return data.get("access_token", "")

    def _real_debrid_api_request(self, method, endpoint, token, data=None, timeout=30, retry=True):
        import requests

        base_url = "https://api.real-debrid.com/rest/1.0/"
        current_token = ownAddon.getSetting("rd.token") or token
        headers = {"Authorization": f"Bearer {current_token}"}
        request = getattr(requests, method.lower())
        kwargs = {"headers": headers, "timeout": timeout}
        if data is not None:
            kwargs["data"] = data
        response = request(base_url + endpoint, **kwargs)
        try:
            payload = response.json()
        except Exception:
            payload = {}
        status_code = getattr(response, "status_code", 200)
        error_code = payload.get("error_code") if isinstance(payload, dict) else None
        if retry and (status_code == 401 or error_code == 8):
            refreshed_token = self._refresh_real_debrid_token()
            if refreshed_token:
                return self._real_debrid_api_request(method, endpoint, refreshed_token, data=data, timeout=timeout, retry=False)
        if status_code >= 400 or (isinstance(payload, dict) and payload.get("error")):
            message = payload.get("error") if isinstance(payload, dict) else getattr(response, "text", "")
            raise RealDebridApiError(message or f"HTTP {status_code}", status_code, error_code)
        return payload

    def _resolve_premiumize_magnet(self, source_item, media_item, token):
        import requests

        response = requests.post(
            "https://www.premiumize.me/api/transfer/directdl",
            data={"src": source_item.get("url", "")},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        ).json()
        if response.get("status") != "success":
            return None
        file_item = self._pick_debrid_file(response.get("content", []), media_item, "path", "size")
        link = file_item.get("link") if file_item else None
        if link:
            return link + "|" + urlencode({"User-Agent": "The Archives", "Authorization": f"Bearer {token}"})
        return None

    def _resolve_real_debrid_magnet(self, source_item, media_item, token):
        torrent_id = None
        try:
            added = self._real_debrid_api_request(
                "post",
                "torrents/addMagnet",
                token,
                data={"magnet": source_item.get("url", "")},
                timeout=30,
            )
            torrent_id = added.get("id")
            if not torrent_id:
                return None
            self._real_debrid_api_request(
                "post",
                f"torrents/selectFiles/{torrent_id}",
                token,
                data={"files": "all"},
                timeout=30,
            )
            torrent_info = {}
            for _ in range(6):
                xbmc.sleep(1000)
                torrent_info = self._real_debrid_api_request(
                    "get",
                    f"torrents/info/{torrent_id}",
                    token,
                    timeout=30,
                )
                if torrent_info.get("links"):
                    break
            files = [dict(file_item, link=torrent_info.get("links", [])[idx]) for idx, file_item in enumerate(torrent_info.get("files", [])) if idx < len(torrent_info.get("links", []))]
            file_item = self._pick_debrid_file(files, media_item, "path", "bytes")
            if not file_item:
                return None
            unrestricted = self._real_debrid_api_request(
                "post",
                "unrestrict/link",
                token,
                data={"link": file_item.get("link")},
                timeout=30,
            )
            return unrestricted.get("download")
        finally:
            if torrent_id:
                try:
                    self._real_debrid_api_request("delete", f"torrents/delete/{torrent_id}", token, timeout=15)
                except Exception:
                    pass

    def _resolve_all_debrid_magnet(self, source_item, media_item, token):
        import requests

        transfer_id = None
        try:
            data = alldebrid_client.api_post(
                requests,
                "magnet/upload",
                token,
                {"magnets[]": source_item.get("url", "")},
                timeout=30,
            )
            magnets = data.get("magnets", [])
            transfer_id = magnets[0].get("id") if magnets else None
            if not transfer_id:
                return None
            files = []
            for _ in range(6):
                xbmc.sleep(1000)
                status_data = alldebrid_client.api_post(
                    requests,
                    "magnet/status",
                    token,
                    {"id": transfer_id},
                    timeout=30,
                    base_url=alldebrid_client.BASE_URL_V41,
                )
                files = alldebrid_client.extract_magnet_files(status_data, transfer_id)
                if files:
                    break
            if not files:
                files_data = alldebrid_client.api_post(
                    requests,
                    "magnet/files",
                    token,
                    {"id[]": transfer_id},
                    timeout=30,
                )
                files = alldebrid_client.extract_magnet_files(files_data, transfer_id)
            links = self._flatten_all_debrid_files(files)
            file_item = self._pick_debrid_file(links, media_item, "n", "s")
            if not file_item:
                return None
            data = alldebrid_client.api_post(
                requests,
                "link/unlock",
                token,
                {"link": file_item.get("l", "")},
                timeout=30,
            )
            return data.get("link")
        finally:
            if transfer_id:
                try:
                    alldebrid_client.api_post(requests, "magnet/delete", token, {"id": transfer_id}, timeout=15)
                except Exception:
                    pass

    def _resolve_torbox_magnet(self, source_item, media_item, token):
        import requests

        headers = {"Authorization": f"Bearer {token}"}
        base_url = "https://api.torbox.app/v1/api/"
        torrent_id = None
        try:
            added = requests.post(base_url + "torrents/createtorrent", data={"magnet": source_item.get("url", ""), "seed": 3, "allow_zip": False}, headers=headers, timeout=30).json()
            if not added.get("success"):
                return None
            torrent_id = added.get("data", {}).get("torrent_id")
            info = requests.get(base_url + f"torrents/mylist?id={torrent_id}", headers=headers, timeout=30).json()
            files = []
            for item in info.get("data", {}).get("files", []):
                files.append({"path": item.get("short_name", ""), "size": item.get("size", 0), "file_id": item.get("id")})
            file_item = self._pick_debrid_file(files, media_item, "path", "size")
            if not file_item:
                return None
            params = {"token": token, "torrent_id": torrent_id, "file_id": file_item.get("file_id")}
            link = requests.get(base_url + "torrents/requestdl", params=params, headers=headers, timeout=30).json()
            return link.get("data")
        finally:
            if torrent_id:
                try:
                    requests.post(base_url + "torrents/controltorrent", json={"torrent_id": torrent_id, "operation": "delete"}, headers=headers, timeout=15)
                except Exception:
                    pass

    def _flatten_all_debrid_files(self, files_list):
        results = []
        stack = list(files_list or [])
        while stack:
            item = stack.pop()
            if not isinstance(item, dict):
                continue
            if "e" in item:
                stack.extend(item["e"])
            elif item.get("l"):
                results.append(item)
        return results

    def _pick_debrid_file(self, files, media_item, name_key, size_key):
        valid_files = [item for item in files or [] if self._is_video_file(item.get(name_key, "")) and item.get("link", item.get("l", item.get("file_id", True)))]
        if not valid_files:
            return None
        season = media_item.get("season")
        episode = media_item.get("episode")
        if season and episode:
            episode_pattern = re.compile(r"(?:s%02de%02d|s%de%d|%dx%02d|%dx%d)" % (int(season), int(episode), int(season), int(episode), int(season), int(episode), int(season), int(episode)), re.I)
            episode_files = [item for item in valid_files if episode_pattern.search(item.get(name_key, ""))]
            if episode_files:
                valid_files = episode_files
        return sorted(valid_files, key=lambda item: self._size_as_int(item.get(size_key)), reverse=True)[0]

    def _is_video_file(self, filename):
        return str(filename or "").lower().split("?", 1)[0].endswith((".mkv", ".mp4", ".avi", ".mov", ".m4v", ".ts", ".wmv", ".flv", ".webm"))

    def _size_as_int(self, value):
        try:
            return int(float(value))
        except Exception:
            return 0
