import sys
import json
import re
from html import unescape
from urllib.parse import quote, unquote, urlencode
from typing import List, Optional, Dict
import xbmc
import xbmcgui
from xbmcaddon import Addon
from ..plugin import Plugin
from ..DI import DI

FANART = Addon().getAddonInfo('fanart')


BASE_URL      = 'https://comettv.com'
STREAM_URL    = 'https://fast-channels.sinclairstoryline.com/COMET/index.m3u8'
CDN_BASE      = 'https://d17su2xjlj6zyp.cloudfront.net'
SHOWS_URL     = f'{BASE_URL}/shows/'
SCHEDULE_URL  = f'{BASE_URL}/schedule/'
WATCH_LIVE    = f'{BASE_URL}/watch-live/'
LOGO_URL      = f'{CDN_BASE}/uploads/2021/04/comet-logo.png'
LOGO_SQUARE   = f'{CDN_BASE}/uploads/2021/06/cropped-comet-logo-square-270x270.png'


KNOWN_SHOWS = [
    ('nwa-powerrr',               'NWA Powerrr',               '2019', 'Pro wrestling',
     'Pro wrestling from the National Wrestling Alliance.'),
    ('xena-warrior-princess',     'Xena: Warrior Princess',    '1995', 'Action, Adventure, Drama, Fantasy',
     'Xena is a reformed warrior princess who travels around fighting evil.'),
    ('the-librarians',            'The Librarians',            '2014', 'Adventure, Drama',
     'New members of an ancient group protect mystical artifacts hidden below the Metropolitan Public Library.'),
    ('stargate-sg-1',             'Stargate SG-1',             '1997', 'Adventure, Science fiction',
     'A team of explorers travels through a Stargate, an ancient portal to other planets.'),
    ('grimm',                     'Grimm',                     '2011', 'Drama, Fantasy, Horror, Thriller',
     'Portland detective Nick Burkhardt, descended from Grimms, defends his city from Wesen creatures.'),
    ('the-x-files',               'The X-Files',               '1993', 'Drama, Science fiction',
     'FBI special agents investigate unexplained cases known as "X-Files."'),
    ('wwe-rivals',                'WWE Rivals',                '2022', 'Pro wrestling',
     'A roundtable discussion delving into the storylines behind epic WWE battles.'),
    ('the-outpost',               'The Outpost',               '2018', 'Action, Adventure, Drama, Fantasy',
     'Talon, the last of the Blackblood race, tracks those who destroyed her village.'),
    ('the-outer-limits',          'The Outer Limits',          '1995', 'Anthology, Drama, Fantasy, Horror, Sci-fi',
     'Anthology series exploring eerie and supernatural themes with a science-fiction element.'),
    ('tales-from-the-darkside',   'Tales From the Darkside',   '1983', 'Anthology, Thriller',
     'Horror anthology series produced by George A. Romero that always ends with a twist.'),
    ('friday-the-13th-the-series', 'Friday the 13th: The Series', '1987', 'Drama, Horror',
     'Micki and her cousin recover cursed antiques sold by their uncle who made a deal with the devil.'),
]

KNOWN_SHOW_NAMES = {slug: name for slug, name, _year, _genre, _desc in KNOWN_SHOWS}

KNOWN_MOVIE_NAMES = {
    'the-librarian-return-to-king-solomons-mines': "The Librarian: Return to King Solomon's Mines",
    'galaxy-quest': 'Galaxy Quest',
    'spaceballs': 'Spaceballs',
    'star-trek-ii-the-wrath-of-khan': 'Star Trek II: The Wrath of Khan',
    'star-trek-into-darkness': 'Star Trek Into Darkness',
    'night-of-the-comet': 'Night of the Comet',
    'evolution': 'Evolution',
}


def _strip_html(text):
    
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', str(text))
    return unescape(text).strip()[:500]


def _strip_noise_blocks(html):
    
    if not html:
        return ''
    html = re.sub(
        r'<(script|style|noscript|svg)\b[^>]*>.*?</\1>',
        '',
        str(html),
        flags=re.DOTALL | re.IGNORECASE,
    )
    return re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)


def _is_clean_description(text):
    if not text:
        return False
    lower = text.lower()
    blocked = (
        'function',
        'playerconfig',
        'generatecorrelationid',
        'javascript',
        'window.',
        'document.',
        'cookie',
    )
    return len(text) > 30 and not any(value in lower for value in blocked)


def _title_from_slug(slug, known_names=None):
    if known_names and slug in known_names:
        return known_names[slug]
    return slug.replace('-', ' ').title()


def _with_kodi_headers(url, user_agent, referer):
    return (
        f'{url}|User-Agent={quote(user_agent, safe="")}'
        f'&Referer={quote(referer, safe="")}'
    )


def _extract_image_urls(html_block):
    
    urls = re.findall(r'(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']', html_block)
    urls += re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', html_block)
    for url in urls:
        if 'cloudfront.net' in url or 'comettv.com' in url:
            if not url.startswith('http'):
                url = f'https:{url}' if url.startswith('//') else f'{BASE_URL}{url}'
            return url
    return urls[0] if urls else ''


def _find_thumbnail_for_show(slug):
    
    return f'{BASE_URL}/show/{slug}/'


class CometTV(Plugin):
   
    name = "comet_tv"
    priority = 1050

    def __init__(self):
        self.session = DI.session
        self.base_url = BASE_URL
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        )
        self.session.headers = {
            'User-Agent': self.user_agent,
            'Referer': BASE_URL,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        
        self.live_url     = f'{self.base_url}/live'
        self.shows_url    = f'{self.base_url}/shows'
        self.show_url     = f'{self.base_url}/show'
        self.movies_url   = f'{self.base_url}/movies'
        self.program_url  = f'{self.base_url}/program'
        self.schedule_url = f'{self.base_url}/schedule'


    def get_list(self, url):
        
        if url == self.live_url:
            return json.dumps({'stream': STREAM_URL})

       
        if url == self.shows_url:
            try:
                resp = self.session.get(SHOWS_URL)
                return resp.text
            except Exception:
                return None

       
        if url.startswith(self.show_url + '/'):
            slug = url.replace(self.show_url + '/', '').split('/')[0]
            show_page = f'{BASE_URL}/show/{slug}/'
            try:
                resp = self.session.get(show_page)
                return resp.text
            except Exception:
                return None

      
        if url == self.movies_url:
            try:
                resp = self.session.get(BASE_URL)
                return resp.text
            except Exception:
                return None

        
        if url == self.schedule_url:
            try:
                resp = self.session.get(SCHEDULE_URL)
                return resp.text
            except Exception:
                return None

        
        if url.startswith(self.program_url + '/'):
            slug = url.replace(self.program_url + '/', '').split('/')[0]
            program_page = f'{BASE_URL}/program/{slug}/'
            try:
                resp = self.session.get(program_page)
                return resp.text
            except Exception:
                return None

        return None

   
    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:

        if not url.startswith(self.base_url):
            return None

        itemlist = []

        
        if url == self.base_url:
            stream_url = _with_kodi_headers(
                STREAM_URL, self.user_agent, BASE_URL
            )
            itemlist.append({
                'type': 'item',
                'title': '[COLOR cyan]▶ Watch Comet TV Live[/COLOR]',
                'link': stream_url,
                'thumbnail': LOGO_URL,
                'summary': 'Watch Comet TV live – free sci-fi & fantasy television.',
                'is_playable': 'true',
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── TV Series ──[/COLOR]',
                'link': self.shows_url,
                'thumbnail': LOGO_SQUARE,
                'summary': 'Browse TV series currently airing on Comet.',
            })
            itemlist.append({
                'type': 'dir',
                'title': '[COLOR orange]── Movies ──[/COLOR]',
                'link': self.movies_url,
                'thumbnail': LOGO_SQUARE,
                'summary': 'Browse movies currently featured on Comet.',
            })
            return itemlist

       
        if url == self.live_url:
            stream_url = _with_kodi_headers(
                STREAM_URL, self.user_agent, BASE_URL
            )
            itemlist.append({
                'type': 'item',
                'title': '[COLOR cyan]▶ Comet TV – Live[/COLOR]',
                'link': stream_url,
                'thumbnail': LOGO_URL,
                'summary': 'Comet TV live stream – sci-fi, fantasy, horror & the supernatural.',
                'is_playable': 'true',
            })
            return itemlist

       
        if url == self.shows_url:
            
            if response:
                itemlist = self._parse_shows_html(response)

            
            if not itemlist:
                for slug, name, year, genre, desc in KNOWN_SHOWS:
                    thumb = self._show_thumbnail_from_slug(slug, response or '')
                    display = name
                    if year:
                        display += f' [COLOR grey]({year})[/COLOR]'
                    itemlist.append({
                        'type': 'dir',
                        'title': display,
                        'link': f'{self.show_url}/{slug}',
                        'thumbnail': thumb,
                        'summary': f'{genre}\n{desc}' if genre else desc,
                    })

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No shows available[/COLOR]',
                    'link': self.base_url,
                })
            return itemlist

       
        if url.startswith(self.show_url + '/'):
            slug = url.replace(self.show_url + '/', '').split('/')[0]
            if response:
                itemlist = self._parse_show_detail(slug, response)

            if not itemlist:
                
                stream_url = _with_kodi_headers(
                    STREAM_URL, self.user_agent, BASE_URL
                )
                itemlist.append({
                    'type': 'item',
                    'title': '[COLOR cyan]▶ Watch Comet TV Live (show may be airing)[/COLOR]',
                    'link': stream_url,
                    'thumbnail': LOGO_URL,
                    'summary': 'Tune in to Comet TV live to catch this show.',
                    'is_playable': 'true',
                })
            return itemlist

        
        if url == self.movies_url:
            if response:
                itemlist = self._parse_movies_html(response)

            if not itemlist:
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR grey]No movies found – check the schedule[/COLOR]',
                    'link': self.schedule_url,
                })
            return itemlist

        
        if url == self.schedule_url:
            if response:
                itemlist = self._parse_schedule_html(response)

            if not itemlist:
                stream_url = _with_kodi_headers(
                    STREAM_URL, self.user_agent, BASE_URL
                )
                itemlist.append({
                    'type': 'item',
                    'title': '[COLOR cyan]▶ Watch Comet TV Live[/COLOR]',
                    'link': stream_url,
                    'thumbnail': LOGO_URL,
                    'summary': 'Schedule data loads dynamically. Watch live instead!',
                    'is_playable': 'true',
                })
                itemlist.append({
                    'type': 'dir',
                    'title': '[COLOR deepskyblue]Open Schedule in Browser[/COLOR]',
                    'link': self.schedule_url,
                    'summary': 'Visit comettv.com/schedule/ for the full interactive schedule.',
                })
            return itemlist

        
        if url.startswith(self.program_url + '/'):
            if response:
                itemlist = self._parse_program_detail(response)

            if not itemlist:
                stream_url = _with_kodi_headers(
                    STREAM_URL, self.user_agent, BASE_URL
                )
                itemlist.append({
                    'type': 'item',
                    'title': '[COLOR cyan]▶ Watch Comet TV Live[/COLOR]',
                    'link': stream_url,
                    'thumbnail': LOGO_URL,
                    'summary': 'Tune in live to catch this program.',
                    'is_playable': 'true',
                })
            return itemlist

        stream_url = _with_kodi_headers(
            STREAM_URL, self.user_agent, BASE_URL
        )
        return [{
            'type': 'item',
            'title': '[COLOR cyan]▶ Watch Comet TV Live[/COLOR]',
            'link': stream_url,
            'thumbnail': LOGO_URL,
            'summary': 'This Comet TV page is not available as on-demand video. Watch the live channel instead.',
            'is_playable': 'true',
        }]

   

    def _parse_shows_html(self, html):
        
        itemlist = []

       
        show_blocks = re.findall(
            r'<a[^>]*href=["\']https?://comettv\.com/show/([^/"\']+)/?["\'][^>]*>.*?</a>',
            html, re.DOTALL | re.IGNORECASE
        )

        
        sections = re.split(r'<(?:article|div)[^>]*class=["\'][^"\']*show-card[^"\']*["\']', html)
        if len(sections) <= 1:
           
            sections = re.split(
                r'(?=<a[^>]*href=["\']https?://comettv\.com/show/[^"\']+["\'])',
                html
            )

        seen_slugs = set()
        for section in sections:
            
            slug_match = re.search(
                r'href=["\']https?://comettv\.com/show/([^/"\']+)/?["\']',
                section
            )
            if not slug_match:
                continue
            slug = slug_match.group(1)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            
            title_match = re.search(r'<h2[^>]*>(.*?)</h2>', section, re.DOTALL)
            if title_match:
                title = _strip_html(title_match.group(1))
            else:
                title = _title_from_slug(slug, KNOWN_SHOW_NAMES)

            
            title = re.sub(r'More Info$', '', title).strip()

            
            img_match = re.search(
                r'<img[^>]*src=["\']([^"\']*cloudfront[^"\']*)["\']',
                section
            )
            thumb = img_match.group(1) if img_match else ''
            if not thumb:
                img_match = re.search(
                    r'<img[^>]*src=["\']([^"\']+\.(?:jpg|png|webp))["\']',
                    section
                )
                thumb = img_match.group(1) if img_match else LOGO_SQUARE

            
            meta_match = re.search(
                r'(\d{4})\s*[•·]\s*([^<\n]+)',
                section
            )
            year = meta_match.group(1) if meta_match else ''
            genre = _strip_html(meta_match.group(2)).strip() if meta_match else ''

            
            desc_match = re.search(
                r'<p[^>]*>(.*?)</p>',
                section, re.DOTALL
            )
            desc = _strip_html(desc_match.group(1)) if desc_match else ''

            
            air_match = re.search(
                r'Watch Next\s+(.*?)(?:<|$)',
                section, re.DOTALL
            )
            air_time = _strip_html(air_match.group(1)).strip() if air_match else ''

            
            display = title
            if year:
                display += f' [COLOR grey]({year})[/COLOR]'

            
            summary_parts = []
            if genre:
                summary_parts.append(genre)
            if air_time:
                summary_parts.append(f'Next: {air_time}')
            if desc:
                summary_parts.append(desc[:300])
            summary = '\n'.join(summary_parts)

            itemlist.append({
                'type': 'dir',
                'title': display,
                'link': f'{self.show_url}/{slug}',
                'thumbnail': thumb,
                'summary': summary,
            })

        return itemlist

    def _parse_show_detail(self, slug, html):
        """Parse a show detail page into episodes / info items."""
        itemlist = []
        html = _strip_noise_blocks(html)

        
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        show_title = _strip_html(title_match.group(1)) if title_match else slug.replace('-', ' ').title()

        
        main_img = ''
        img_match = re.search(
            r'<img[^>]*src=["\']([^"\']*cloudfront[^"\']*_h10[^"\']*)["\']',
            html
        )
        if img_match:
            main_img = img_match.group(1)
        if not main_img:
            img_match = re.search(
                r'<img[^>]*src=["\']([^"\']*cloudfront[^"\']+\.(?:jpg|png))["\']',
                html
            )
            main_img = img_match.group(1) if img_match else LOGO_SQUARE

        
        desc = ''
        desc_match = re.search(
            r'(\d{4}\s*[•·]\s*[^<]+)</?\w',
            html
        )
        meta_line = _strip_html(desc_match.group(1)) if desc_match else ''

        
        p_matches = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        for p_text in p_matches:
            clean = _strip_html(p_text)
            if _is_clean_description(clean):
                desc = clean
                break

        
        info = f'{meta_line}\n{desc}' if meta_line else desc
        stream_url = _with_kodi_headers(STREAM_URL, self.user_agent, BASE_URL)

        itemlist.append({
            'type': 'item',
            'title': f'[COLOR cyan]▶ Watch Comet TV Live[/COLOR] [COLOR grey](catch {show_title})[/COLOR]',
            'link': stream_url,
            'thumbnail': main_img,
            'summary': info if info else f'Watch {show_title} on Comet TV.',
            'is_playable': 'true',
        })

        
        episode_blocks = re.findall(
            r'<a[^>]*href=["\']https?://comettv\.com/program/([^"\']+)["\'][^>]*>'
            r'(.*?)</a>',
            html, re.DOTALL
        )

        seen_episodes = set()
        for ep_slug, ep_block in episode_blocks:
            ep_slug_clean = ep_slug.rstrip('/')
            if ep_slug_clean in seen_episodes:
                continue
            seen_episodes.add(ep_slug_clean)

           
            ep_title_match = re.search(r'<h\d[^>]*>(.*?)</h\d>', ep_block, re.DOTALL)
            ep_title = _strip_html(ep_title_match.group(1)) if ep_title_match else ep_slug_clean.replace('-', ' ').title()

            
            ep_img = ''
            ep_img_match = re.search(
                r'<img[^>]*src=["\']([^"\']+)["\']',
                ep_block
            )
            if ep_img_match:
                ep_img = ep_img_match.group(1)
            if not ep_img:
                ep_img = main_img

           
            ep_desc = ''
            ep_p = re.search(r'<p[^>]*>(.*?)</p>', ep_block, re.DOTALL)
            if ep_p:
                ep_desc = _strip_html(ep_p.group(1))

            
            air_pattern = re.search(
                re.escape(ep_slug_clean) + r'.*?'
                r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\s+\w+\s+\d+\s*@\s*[\d:]+\s*[APap][Mm]\s*ET/PT)',
                html, re.DOTALL
            )
            ep_air = air_pattern.group(1).strip() if air_pattern else ''

            display = f'[COLOR limegreen]▶[/COLOR] {ep_title}'
            if ep_air:
                display += f' [COLOR grey]({ep_air})[/COLOR]'

            itemlist.append({
                'type': 'dir',
                'title': display,
                'link': f'{self.program_url}/{ep_slug_clean}',
                'thumbnail': ep_img,
                'summary': ep_desc if ep_desc else f'Upcoming episode of {show_title}.',
            })

       
        if len(itemlist) <= 1:
            ep_sections = re.findall(
                r'(?:program|episode)[^"\']*["\'][^>]*>.*?'
                r'<h\d[^>]*>(.*?)</h\d>'
                r'(.*?)'
                r'(?=(?:program|episode)|$)',
                html, re.DOTALL | re.IGNORECASE
            )

        return itemlist

    def _parse_movies_html(self, html):
        
        itemlist = []
        html = _strip_noise_blocks(html)

       
        movies_section = ''
        movies_heading = r'Movies\s+on\s*(?:<[^>]+>\s*)*COMET(?:\s*</[^>]+>)*'
        movies_match = re.search(
            movies_heading + r'(.*?)(?:Find\s+Comet|</main>|<footer|$)',
            html, re.DOTALL | re.IGNORECASE
        )
        if not movies_match:
            
            movies_match = re.search(
                r'Movies(.*?)(?:Find\s+Comet|footer|$)',
                html, re.DOTALL | re.IGNORECASE
            )
        if movies_match:
            movies_section = movies_match.group(1)
        else:
            movies_section = html

        
        program_links = re.findall(
            r'<a[^>]*href=["\'](?:https?://comettv\.com)?/program/([^/"\']+)/?["\']',
            movies_section, re.IGNORECASE
        )

        seen = set()
        stream_url = _with_kodi_headers(STREAM_URL, self.user_agent, BASE_URL)
        for slug in program_links:
            if slug in seen:
                continue
            seen.add(slug)

            title = _title_from_slug(slug, KNOWN_MOVIE_NAMES)

            
            thumb = ''
            img_pattern = re.search(
                re.escape(slug) + r'.*?<img[^>]*src=["\']([^"\']+)["\']',
                movies_section, re.DOTALL
            )
            if not img_pattern:
                img_pattern = re.search(
                    r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>.*?' + re.escape(slug),
                    movies_section, re.DOTALL
                )
            thumb = img_pattern.group(1) if img_pattern else LOGO_SQUARE

            display = title

            itemlist.append({
                'type': 'item',
                'title': display,
                'link': stream_url,
                'thumbnail': thumb,
                'summary': f'{title} is scheduled on Comet TV. This plays the live Comet TV stream.',
                'is_playable': 'true',
            })

        return itemlist

    def _parse_schedule_html(self, html):
       
        itemlist = []
        html = _strip_noise_blocks(html)
        stream_url = _with_kodi_headers(STREAM_URL, self.user_agent, BASE_URL)

       
        itemlist.append({
            'type': 'item',
            'title': '[COLOR cyan]▶ Watch Comet TV Live Now[/COLOR]',
            'link': stream_url,
            'thumbnail': LOGO_URL,
            'summary': 'Watch whatever is currently airing on Comet TV.',
            'is_playable': 'true',
        })

       
        day_matches = re.findall(
            r'<(?:h\d|div)[^>]*>\s*(\w+day)\s*<br\s*/?>\s*(\w+\s+\d+)',
            html, re.IGNORECASE
        )

        if day_matches:
            for day_name, date_str in day_matches[:7]:
                itemlist.append({
                    'type': 'dir',
                    'title': f'[COLOR orange]── {day_name} {date_str} ──[/COLOR]',
                    'link': self.schedule_url,
                    'thumbnail': LOGO_SQUARE,
                })

       
        itemlist.append({
            'type': 'dir',
            'title': '[COLOR deepskyblue]📅 View Full Schedule on comettv.com[/COLOR]',
            'link': SCHEDULE_URL,
            'thumbnail': LOGO_SQUARE,
            'summary': 'The full schedule loads dynamically. Visit comettv.com/schedule/ for details.',
        })

        
        itemlist.append({
            'type': 'dir',
            'title': '[COLOR orange]── Browse Shows ──[/COLOR]',
            'link': self.shows_url,
            'thumbnail': LOGO_SQUARE,
        })
        itemlist.append({
            'type': 'dir',
            'title': '[COLOR orange]── Browse Movies ──[/COLOR]',
            'link': self.movies_url,
            'thumbnail': LOGO_SQUARE,
        })

        return itemlist

    def _parse_program_detail(self, html):
        
        itemlist = []
        html = _strip_noise_blocks(html)

        
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        title = _strip_html(title_match.group(1)) if title_match else 'Program'

        
        img = ''
        img_match = re.search(
            r'<img[^>]*src=["\']([^"\']*cloudfront[^"\']+\.(?:jpg|png))["\']',
            html
        )
        img = img_match.group(1) if img_match else LOGO_SQUARE

       
        desc = ''
        p_matches = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        for p_text in p_matches:
            clean = _strip_html(p_text)
            if _is_clean_description(clean):
                desc = clean
                break

        
        meta = ''
        meta_match = re.search(r'(\d{4})\s*[•·]\s*([^<]+)', html)
        if meta_match:
            meta = _strip_html(meta_match.group(0))

       
        air_time = ''
        air_match = re.search(
            r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\s+\w+\s+\d+\s*@\s*[\d:]+\s*[APap][Mm]\s*ET/PT)',
            html
        )
        if air_match:
            air_time = air_match.group(1).strip()

        stream_url = _with_kodi_headers(STREAM_URL, self.user_agent, BASE_URL)

        summary_parts = []
        if meta:
            summary_parts.append(meta)
        if air_time:
            summary_parts.append(f'Airs: {air_time}')
        if desc:
            summary_parts.append(desc[:400])
        summary = '\n'.join(summary_parts)

        display = f'[COLOR cyan]▶ Watch Comet TV Live[/COLOR]'
        if air_time:
            display += f' [COLOR grey]({title} airs {air_time})[/COLOR]'
        else:
            display += f' [COLOR grey](catch {title})[/COLOR]'

        itemlist.append({
            'type': 'item',
            'title': display,
            'link': stream_url,
            'thumbnail': img,
            'summary': summary if summary else f'{title} on Comet TV.',
            'is_playable': 'true',
        })

       
        if desc or meta:
            itemlist.append({
                'type': 'dir',
                'title': f'[COLOR white]{title}[/COLOR]',
                'link': self.base_url,
                'thumbnail': img,
                'summary': summary,
            })

        return itemlist

    def _show_thumbnail_from_slug(self, slug, html=''):
        
        if html:
            pattern = re.search(
                re.escape(slug) + r'.*?<img[^>]*src=["\']([^"\']+)["\']',
                html, re.DOTALL
            )
            if pattern:
                return pattern.group(1)
        return LOGO_SQUARE

  

    def play_video(self, item: str) -> Optional[bool]:
        
        data = {}
        link = item
        try:
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            data = json.loads(item)
            link = data.get('link', '')
        except (json.JSONDecodeError, TypeError, AttributeError):
            data = {}
            link = item.decode('utf-8') if isinstance(item, bytes) else item

        if not isinstance(link, str):
            return None

        
        if 'sinclairstoryline.com/COMET' not in link and 'comettv.com' not in link:
            return None

        
        if 'comettv.com' in link and '.m3u8' not in link:
            return None

        title = data.get('title', '')
        title = re.sub(r'\[/?COLOR[^\]]*\]', '', str(title or 'Comet TV')).strip()
        if not title:
            title = 'Comet TV'
        thumbnail = data.get('thumbnail', LOGO_URL)

       
        stream_path = link.split('|', 1)[0]

        liz = xbmcgui.ListItem(title, path=link)
        liz.setProperty('IsPlayable', 'true')
        liz.setArt({
            'thumb': thumbnail,
            'icon': thumbnail,
            'poster': LOGO_SQUARE,
            'fanart': FANART,
        })
        from resources.lib.infotagger.helpers import set_video_info
        set_video_info(liz, {
            "title": title,
            "plot": data.get("summary", "Comet TV – Sci-Fi & Fantasy Television"),
        })
        liz.setMimeType('application/vnd.apple.mpegurl')
        try:
            liz.setContentLookup(False)
        except AttributeError:
            pass

        xbmc.Player().play(link, liz)
        return True

    

    def from_keyboard(self, default_text='', header='Search Comet TV'):
       
        kb = xbmc.Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            return kb.getText()
        return None
