##########################################
# GIVE CREDIT WHERE CREDIT IS DUE                                
# Thanks and respect to Crucial Minds for permission    
# to use the Base Code for the scraper module  
# (script.module.microjenscrapers) and to The Jen Crew for their      
# valuable contributions in bringing this project together 
# and for ongoing  maintenance / development                        
#########################################

from ..plugin import Plugin
import json, re, xbmc
import xbmcaddon
try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *

debrid_only = ownAddon.getSetting('debrid.only') or 'false'
addon_name = xbmcaddon.Addon().getAddonInfo('name')
scrapers_addon = xbmcaddon.Addon('script.module.microjenscrapers')
scrapers_setting_bool = scrapers_addon.getSettingBool

TIMEOUT = 10

class MicroJenScrapers(Plugin):
    name = "microjenscrapers"
    description = "Scrape with MicroJen Scrapers"
    priority = 121

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
    # hostprDict = [] 
    hostDict = []

    def play_video(self, item):
        item = json.loads(item)
        link = item.get("link")
        if link and link.startswith("search"):
            import microjenscrapers
            import xbmcgui
            import concurrent.futures
            import resolveurl
            import operator
            import time

            self.hostDict = resolveurl.relevant_resolvers(order_matters=True)
            progress = xbmcgui.DialogProgress()
            sources = microjenscrapers.sources()
            all_sources = []
            search_title = re.sub("(\[.+?\])", "", item.get("title")) 
            do_log(f'{self.name} - search_title = \n' + str(search_title) )  
            
            if item.get("content").lower() == "movie":
                sources = [(i[0], i[1], getattr(i[1], "movie", None)) for i in sources]
                sources = list(filter(lambda source: source[2], sources))
                all_sources = []
                num_sources = len(sources)
                counter = 0
                progress.create(
                    f"{addon_name}",
                    f"Scraping for {item.get('title')}\n[I][COLOR orange](Sources : {num_sources - counter} / {num_sources} left)[/I][COLOR white] > [COLOR lawngreen]{len(all_sources)} links found[/COLOR]",
                )
                # progress.create(
                    # "MicroJen",
                    # f"Scraping for {item.get('title')}\n{num_sources}/{num_sources} left\n 0 links found",
                # )
                threads = [
                    self.get_movie_source(
                        # item.get("title"),
                        search_title,
                        item.get("year"),
                        item.get("imdb_id"),
                        i[0],
                        i[1],
                    )
                    for i in sources
                ]
                for t in threads:
                    t[0].start()
                end_time = TIMEOUT + time.monotonic()
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
                            percent = int((counter / num_sources) * 100)
                            progress.update(
                                percent,
                                f"Scraping for {item.get('title')}\n[I][COLOR orange](Sources : {num_sources - counter} / {num_sources} left)[/I][COLOR white] > [COLOR lawngreen]{len(all_sources)} links found[/COLOR]",
                            )
                            # progress.update(
                                # percent,
                                # f"Scraping for {item.get('title')}\n{num_sources - counter}/{num_sources} left\n {len(all_sources)} links found",
                            # )
                    else:
                        continue
                    break
                progress.close()
                all_sources = list(filter(lambda source: source, all_sources))
            elif item.get("content").lower() == "episode":
                sources = [(i[0], i[1], getattr(i[1], "tvshow", None)) for i in sources]
                sources = list(filter(lambda source: source[2], sources))
                all_sources = []
                num_sources = len(sources)
                counter = 0
                name = f'{item.get("tv_show_title")} - S{item.get("season")}E{item.get("episode")}'
                progress.create(
                    f"{addon_name}",
                    f"Scraping for {item.get('title')}\n[I][COLOR orange](Sources : {num_sources - counter} / {num_sources} left)[/I][COLOR white] > [COLOR lawngreen]{len(all_sources)} links found[/COLOR]",
                )
                # progress.create(
                    # "MicroJen",
                    # f"Scraping for {item.get('title')}\n{num_sources}/{num_sources} left\n 0 links found",
                # )
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
                    for i in sources
                ]
                for t in threads:
                    t[0].start()
                end_time = TIMEOUT + time.monotonic()
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
                            percent = int((counter / num_sources) * 100)
                            progress.update(
                                percent,
                                f"Scraping for {item.get('title')}\n[I][COLOR orange](Sources : {num_sources - counter} / {num_sources} left)[/I][COLOR white] > [COLOR lawngreen]{len(all_sources)} links found[/COLOR]",
                            )
                            # progress.update(
                                # percent,
                                # f"Scraping for {item.get('title')}\n{num_sources - counter}/{num_sources} left\n {len(all_sources)} links found",
                            # )
                    else:
                        continue
                    break
                progress.close()
                all_sources = list(filter(lambda source: source, all_sources))

            if not all_sources:
                return False

            all_sources = sorted(all_sources, key=operator.itemgetter("quality"))
            try:
                if scrapers_setting_bool("quality.4k") is False:
                    all_sources = [source for source in all_sources if not source["quality"] == ".4K"]
                if scrapers_setting_bool("quality.1080p") is False:
                    all_sources = [source for source in all_sources if not source["quality"] == "1080p"]
                if scrapers_setting_bool("quality.720p") is False:
                    all_sources = [source for source in all_sources if not source["quality"] == "720p"]
                if scrapers_setting_bool("quality.sd") is False:
                    all_sources = [source for source in all_sources if not source["quality"] == "sd"]
                if scrapers_setting_bool("quality.cam") is False:
                    all_sources = [source for source in all_sources if not source["quality"] == "cam"]
            except:
                pass
            play_sources = [
                f"{item['origin']} - {item['source']} - {str(item['quality']).replace('.','')} - {item.get('info', 'Size Unknown')}"
                for item in all_sources
            ]
            selected = xbmcgui.Dialog().select("Select a Link", play_sources)
            if not selected == -1:
                import xbmc
                import xbmcaddon
                default_icon = xbmcaddon.Addon().getAddonInfo('icon')
                title = item["title"]
                thumbnail = item.get("thumbnail", default_icon)
                plot = item.get("summary", "")
                #if item.get("infolabels", ""):
                    #plot = item["infolabels"]["plot"]
                liz = xbmcgui.ListItem(title)
                liz.setInfo('video', {'title': title, "plot": plot})
                liz.setArt({'thumb': thumbnail, 'icon': thumbnail})

                if resolveurl.HostedMediaFile(all_sources[selected]["url"]).valid_url():                    
                    url = resolveurl.HostedMediaFile(
                        all_sources[selected]["url"]
                    ).resolve()
                    xbmc.Player().play(url, liz)
                    return True
                elif all_sources[selected]["direct"]:
                    xbmc.Player().play(all_sources[selected]["url"], liz)
                    return True
                else:
                    return False
            else:
                return True
    
    def routes(self, plugin):
        @plugin.route(f"/{self.name}/play/<path:query>")
        def play(query):
            q = query.split("|")
            item = {"title": q[1], "content": q[0], "imdb_id": q[2], "year": q[3], "link": "search"}
            self.play_video(json.dumps(item))

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
        url = source_object.movie(imdb, title, title, "", year)
        sources = source_object.sources(url, self.hostDict, self.hostprDict)
        if sources:
            for item in sources:
                item["origin"] = source_name
            outlist.extend(sources)
        return sources

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
