import xbmcaddon
try:
    from resources.lib.DI import DI
    from resources.lib.plugin import run_hook, register_routes
except ImportError:
    from .resources.lib.DI import DI
    from .resources.lib.plugin import run_hook, register_routes

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *
    
DEFAULT_ROOT_XML = "file://main.json"


def get_root_xml_url():
    configured_url = (ownAddon.getSetting('root_xml') or "").strip()
    if not configured_url:
        return DEFAULT_ROOT_XML

    if configured_url.lower() == "file://main.xml":
        main_xml = os.path.join(PATH, "xml", "main.xml")
        main_json = os.path.join(PATH, "xml", "main.json")
        if not xbmcvfs.exists(main_xml) and xbmcvfs.exists(main_json):
            return DEFAULT_ROOT_XML

    return configured_url


root_xml_url = get_root_xml_url()


plugin = DI.plugin
short_checker = ([
    'Adf.ly', 
    'Bit.ly', 
    'Chilp.it', 
    'Clck.ru', 
    'Cutt.ly', 
    'Da.gd', 
    'Git.io', 
    'goo.gl', 
    'Is.gd', 
    'NullPointer', 
    'Os.db', 
    'Ow.ly', 
    'Po.st', 
    'Qps.ru', 
    'Short.cm', 
    'Tiny.cc', 
    'TinyURL.com', 
    'Git.io', 
    'Tiny.cc', 
     ])

@plugin.route("/")
def root() -> None:
    get_list(root_xml_url)

@plugin.route("/get_list/<path:url>")
def get_list(url: str) -> None:
    url = url.replace('.xmll', '.xml')
    _get_list(url)

def _get_list(url):
    if any(check.lower() in url.lower() for check in short_checker):
        url = DI.session.get(url).url
    response = run_hook("get_list", url)
    if response:           
        if ownAddon.getSettingBool("use_cache") and not "tmdb/search" in url:
            DI.db.set(url, response)
        jen_list = run_hook("parse_list", url, response)
        if not jen_list:
            run_hook("display_list", [])
            return
        jen_list = [run_hook("process_item", item) for item in jen_list]
        jen_list = [
        run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list
        ]
        run_hook("display_list", jen_list)
    else:
        run_hook("display_list", [])

@plugin.route("/play_video/<path:video>")
def play_video(video: str):
    _play_video(video)

def _play_video(video):
    import base64
    video_link = '' 
    video = base64.urlsafe_b64decode(video)      
    if '"link":' in str(video) :
        video_link = run_hook("pre_play", video)
        if video_link : 
            run_hook("play_video", video_link)        
    else :
        run_hook("play_video", video)

@plugin.route("/settings")
def settings():
    xbmcaddon.Addon().openSettings()

@plugin.route("/clear_cache")
def clear_cache():
    DI.db.clear_cache()
    import xbmc
    xbmc.executebuiltin("Container.Refresh")

@plugin.route("/choose_scraper")
def choose_scraper():
    import xbmc, xbmcgui, json
    addon = xbmcaddon.Addon()
    addon_name = addon.getAddonInfo('name')
    jsonrpc_request = json.dumps({
        'jsonrpc': '2.0',
        'method': 'Addons.GetAddons',
        'params': {
            'type': 'xbmc.python.module',
            'properties': ['name', 'thumbnail', 'enabled']
        },
        'id': 1
    })
    response = json.loads(xbmc.executeJSONRPC(jsonrpc_request))
    addons = response.get('result', {}).get('addons', [])
    addons = [a for a in addons if a.get('enabled', True)]
    if not addons:
        xbmcgui.Dialog().ok(addon_name, 'No script modules found.')
        return
    names = [a['name'] for a in addons]
    choice = xbmcgui.Dialog().select('Choose Scraper Module', names)
    if choice == -1:
        return
    selected = addons[choice]
    module_id = selected['addonid']
    module_name = selected['name']
    import sys, os
    scraper_module_name = module_id.split('.')[-1]
    try:
        scraper_addon = xbmcaddon.Addon(module_id)
        scraper_path = os.path.join(scraper_addon.getAddonInfo('path'), 'lib')
        if scraper_path not in sys.path:
            sys.path.insert(0, scraper_path)
        mod = __import__(scraper_module_name)
        test_sources = mod.sources()
        success = True
    except Exception as e:
        success = False
        do_log(f'choose_scraper - Failed to import {module_id}: {e}')
    if success:
        addon.setSetting('scraper.module', module_id)
        addon.setSetting('scraper.name', module_name)
        xbmcgui.Dialog().ok(addon_name, f'Success!\n[B]{module_name}[/B] set as Scraper Module.')
    else:
        xbmcgui.Dialog().ok(addon_name, f'[B]{module_name}[/B] is not a compatible scraper module.\nPlease choose a different one.')

@plugin.route("/inputstream_helper")
def inputstream_helper():
    import xbmc, xbmcgui
    addon = xbmcaddon.Addon()
    addon_name = addon.getAddonInfo('name')
    helper_id = 'script.module.inputstreamhelper'
    if not xbmc.getCondVisibility(f'System.HasAddon({helper_id})'):
        install = xbmcgui.Dialog().yesno(
            addon_name,
            'InputStream Helper is needed for Roku Widevine playback.\nInstall it now?'
        )
        if install:
            xbmc.executebuiltin(f'InstallAddon({helper_id})')
        return
    try:
        import inputstreamhelper
        helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        if helper.check_inputstream():
            xbmcgui.Dialog().notification(
                addon_name,
                'InputStream Adaptive / Widevine is ready',
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
    except Exception as e:
        do_log(f'inputstream_helper - Error opening helper: {e}')
        xbmc.executebuiltin(f'Addon.OpenSettings({helper_id})')

@plugin.route("/open_scraper_settings")
def open_scraper_settings():
    import xbmc, xbmcgui
    addon = xbmcaddon.Addon()
    module_id = addon.getSetting('scraper.module') or ''
    if not module_id:
        xbmcgui.Dialog().ok(addon.getAddonInfo('name'), 'No scraper module selected yet.\nPlease choose one first via Settings > Choose Scraper Module.')
        return
    xbmc.executebuiltin(f'Addon.OpenSettings({module_id})')

@plugin.route("/auth_service/<service>")
def auth_service(service):
    import xbmc, xbmcgui, json, time
    addon = xbmcaddon.Addon()
    addon_name = addon.getAddonInfo('name')
    service_names = {
        'rd': 'Real-Debrid',
        'pm': 'Premiumize',
        'ad': 'AllDebrid',
        'tb': 'TorBox'
    }
    name = service_names.get(service, service)
    try:
        if service == 'rd':
            _auth_real_debrid(addon, addon_name)
        elif service == 'pm':
            _auth_premiumize(addon, addon_name)
        elif service == 'ad':
            _auth_alldebrid(addon, addon_name)
        elif service == 'tb':
            _auth_torbox(addon, addon_name)
        else:
            xbmcgui.Dialog().ok(addon_name, f'Unknown service: {service}')
    except Exception as e:
        do_log(f'auth_service - Error authorizing {name}: {e}')
        xbmcgui.Dialog().ok(addon_name, f'Authorization failed for {name}.\n{str(e)}')

def build_debrid_qr_image_url(verification_url, size=800):
    try:
        from resources.lib.util.tmdb_qr import build_qr_image_url
    except ImportError:
        from .resources.lib.util.tmdb_qr import build_qr_image_url
    return build_qr_image_url(verification_url or '', size=size)

def format_debrid_user_code(user_code):
    return (user_code or '').replace('-', '').upper()

def _show_debrid_qr_auth_window(addon_name, service_name, verification_url, user_code, poller):
    import threading, xbmcgui

    class DebridQRAuthDialog(xbmcgui.WindowXMLDialog):
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92

        def __init__(self, *args, **kwargs):
            super(DebridQRAuthDialog, self).__init__(*args, **kwargs)
            self.cancelled = False
            self.response = None
            self.error = None

        def onAction(self, action):
            if action.getId() in (self.ACTION_PREVIOUS_MENU, self.ACTION_NAV_BACK):
                self.cancelled = True
                self.close()

    dialog = DebridQRAuthDialog('debrid_auth_qr.xml', PATH, 'Default', '1080i')
    dialog.setProperty('debrid.title', f'{addon_name} - {service_name}')
    dialog.setProperty('debrid.service', service_name)
    dialog.setProperty('debrid.qr_url', build_debrid_qr_image_url(verification_url, size=800))
    dialog.setProperty('debrid.auth_url', verification_url or '')
    dialog.setProperty('debrid.user_code', format_debrid_user_code(user_code))
    worker = threading.Thread(target=poller, args=(dialog,))
    worker.daemon = True
    worker.start()
    dialog.doModal()
    dialog.cancelled = True
    worker.join(0.1)
    if dialog.error:
        raise dialog.error
    return dialog.response

def _auth_real_debrid(addon, addon_name):
    import xbmc, xbmcgui, json, time, requests
    base_url = 'https://api.real-debrid.com/oauth/v2/'
    client_id = addon.getSetting('rd.client_id') or get_real_debrid_client_id()
    if not client_id:
        xbmcgui.Dialog().ok(addon_name, 'The addon is missing its Real-Debrid Client ID.\nPlease add the addon API credentials before authorizing Real-Debrid.')
        return
    resp = requests.get(f'{base_url}device/code?client_id={client_id}&new_credentials=yes').json()
    user_code = resp['user_code']
    device_code = resp['device_code']
    verify_url = resp.get('verification_url', 'https://real-debrid.com/device')
    interval = resp.get('interval', 5)
    expires_in = resp.get('expires_in', 600)

    def poll_credentials(dialog):
        start = time.time()
        while not dialog.cancelled and (time.time() - start) < expires_in:
            xbmc.sleep(interval * 1000)
            try:
                poll = requests.get(f'{base_url}device/credentials?client_id={client_id}&code={device_code}').json()
                if 'client_id' in poll:
                    dialog.response = poll
                    dialog.close()
                    return
            except:
                continue
        dialog.cancelled = True
        try:
            dialog.close()
        except:
            pass

    credentials = _show_debrid_qr_auth_window(addon_name, 'Real-Debrid', verify_url, user_code, poll_credentials)
    if not credentials:
        xbmcgui.Dialog().ok(addon_name, 'Real-Debrid authorization timed out or was cancelled.')
        return
    new_client_id = credentials['client_id']
    client_secret = credentials['client_secret']
    data = {
        'client_id': new_client_id,
        'client_secret': client_secret,
        'code': device_code,
        'grant_type': 'http://oauth.net/grant_type/device/1.0'
    }
    token_resp = requests.post(f'{base_url}token', data=data).json()
    addon.setSetting('rd.token', token_resp.get('access_token', ''))
    addon.setSetting('rd.refresh', token_resp.get('refresh_token', ''))
    addon.setSetting('rd.client_id', new_client_id)
    addon.setSetting('rd.secret', client_secret)
    xbmcgui.Dialog().ok(addon_name, '[B]Real-Debrid[/B] authorized successfully!')

def _premiumize_activation_message(verify_url, user_code):
    display_code = user_code.replace('-', '').upper()
    return f'Go to: [B]{verify_url}[/B]\nEnter code: [B][COLOR lawngreen]{display_code}[/COLOR][/B]'

def _auth_premiumize(addon, addon_name):
    import xbmc, xbmcgui, json, time, requests
    default_client_id = get_premiumize_client_id()
    if not default_client_id:
        xbmcgui.Dialog().ok(addon_name, 'The addon is missing its Premiumize Client ID.\nPlease add the addon API credentials before authorizing Premiumize.')
        return
    client_id = addon.getSetting('pm.client_id') or default_client_id

    def start_device_flow(value):
        return requests.post('https://www.premiumize.me/token', data={
            'response_type': 'device_code',
            'client_id': value
        }).json()

    resp = start_device_flow(client_id)
    if ('user_code' not in resp or 'device_code' not in resp) and client_id != default_client_id:
        client_id = default_client_id
        resp = start_device_flow(client_id)
        if 'user_code' in resp and 'device_code' in resp:
            addon.setSetting('pm.client_id', client_id)

    if 'user_code' not in resp or 'device_code' not in resp:
        error = resp.get('error_description') or resp.get('message') or resp.get('error') or 'Premiumize did not return an authorization code.'
        xbmcgui.Dialog().ok(addon_name, f'Premiumize authorization failed.\n{error}')
        return

    user_code = resp['user_code']
    device_code = resp['device_code']
    verify_url = resp.get('verification_uri') or resp.get('verification_url') or 'https://www.premiumize.me/device'
    interval = resp.get('interval', 5)
    expires_in = resp.get('expires_in', 600)

    def poll_token(dialog):
        poll_interval = interval
        start = time.time()
        while not dialog.cancelled and (time.time() - start) < expires_in:
            xbmc.sleep(poll_interval * 1000)
            try:
                poll = requests.post('https://www.premiumize.me/token', data={
                    'grant_type': 'device_code',
                    'code': device_code,
                    'client_id': client_id,
                }).json()
                if 'access_token' in poll:
                    dialog.response = poll
                    dialog.close()
                    return
                error = poll.get('error', '')
                if error == 'authorization_pending':
                    continue
                if error == 'slow_down':
                    poll_interval += 5
                    continue
                if error in ('access_denied', 'invalid_grant'):
                    dialog.response = poll
                    dialog.close()
                    return
            except Exception as e:
                dialog.error = e
                dialog.close()
                return
        dialog.cancelled = True
        try:
            dialog.close()
        except:
            pass

    poll = _show_debrid_qr_auth_window(addon_name, 'Premiumize', verify_url, user_code, poll_token)
    if poll and poll.get('error') in ('access_denied', 'invalid_grant'):
        xbmcgui.Dialog().ok(addon_name, f'Premiumize authorization failed.\n{poll.get("error_description", poll.get("error"))}')
        return
    token = poll.get('access_token', '') if poll else ''
    if not token:
        xbmcgui.Dialog().ok(addon_name, 'Premiumize authorization timed out or was cancelled.')
        return
    addon.setSetting('pm.token', token)
    xbmcgui.Dialog().ok(addon_name, '[B]Premiumize[/B] authorized successfully!')

def _auth_alldebrid(addon, addon_name):
    import xbmc, xbmcgui, json, time, requests
    try:
        from resources.lib.plugins import alldebrid_client
    except ImportError:
        from .resources.lib.plugins import alldebrid_client

    def store_token(token):
        addon.setSetting('ad.token', token)
        addon.setSetting('ad.enabled', 'true')

    choice = xbmcgui.Dialog().select(
        f'{addon_name} - AllDebrid',
        ['Authorize with PIN', 'Enter API key']
    )
    if choice == -1:
        return
    if choice == 1:
        api_key = xbmcgui.Dialog().input(f'{addon_name} - AllDebrid', 'Enter your AllDebrid API Key')
        api_key = (api_key or '').strip()
        if not api_key:
            return
        try:
            alldebrid_client.verify_api_key(requests, api_key)
        except Exception as e:
            xbmcgui.Dialog().ok(addon_name, f'AllDebrid API key verification failed.\n{str(e)}')
            return
        store_token(api_key)
        xbmcgui.Dialog().ok(addon_name, '[B]AllDebrid[/B] authorized successfully!')
        return

    data = alldebrid_client.get_pin(requests)
    user_code = data.get('pin', '')
    check = data.get('check', '')
    verify_url = data.get('user_url') or data.get('base_url') or 'https://alldebrid.com/pin/'
    expires_in = data.get('expires_in', 600)
    if not user_code or not check:
        xbmcgui.Dialog().ok(addon_name, 'AllDebrid did not return an authorization PIN.')
        return

    def poll_pin(dialog):
        start = time.time()
        while not dialog.cancelled and (time.time() - start) < expires_in:
            xbmc.sleep(5000)
            try:
                poll_data = alldebrid_client.check_pin(requests, user_code, check)
                if poll_data.get('activated'):
                    dialog.response = poll_data
                    dialog.close()
                    return
            except Exception as e:
                dialog.error = e
                dialog.close()
                return
        dialog.cancelled = True
        try:
            dialog.close()
        except:
            pass

    poll_data = _show_debrid_qr_auth_window(addon_name, 'AllDebrid', verify_url, user_code, poll_pin)
    token = poll_data.get('apikey', '') if poll_data else ''
    if not token:
        xbmcgui.Dialog().ok(addon_name, 'AllDebrid authorization timed out or was cancelled.')
        return
    store_token(token)
    xbmcgui.Dialog().ok(addon_name, '[B]AllDebrid[/B] authorized successfully!')

def _auth_torbox(addon, addon_name):
    import xbmc, xbmcgui, requests, time
    try:
        from resources.lib.plugins import torbox_client
    except ImportError:
        from .resources.lib.plugins import torbox_client

    choice = xbmcgui.Dialog().select(
        f'{addon_name} - TorBox',
        ['Authorize with QR Code', 'Enter API key']
    )
    if choice == -1:
        return
    if choice == 1:
        api_key = xbmcgui.Dialog().input(f'{addon_name} - TorBox', 'Enter your TorBox API Key')
        api_key = (api_key or '').strip()
        if not api_key:
            return
        try:
            torbox_client.verify_token(requests, api_key)
        except Exception as e:
            xbmcgui.Dialog().ok(addon_name, f'TorBox API key verification failed.\n{str(e)}')
            return
        addon.setSetting('tb.token', api_key)
        addon.setSetting('tb.enabled', 'true')
        xbmcgui.Dialog().ok(addon_name, '[B]TorBox[/B] authorized successfully!')
        return

    start_resp = requests.get(
        'https://api.torbox.app/v1/api/user/auth/device/start',
        params={'app': 'TheArchives'},
        timeout=20,
    ).json()
    data = start_resp.get('data', start_resp)
    device_code = data.get('device_code', '')
    user_code = data.get('code', '')
    verify_url = data.get('verification_url') or data.get('friendly_verification_url') or 'https://torbox.app/oauth/device'
    interval = int(data.get('interval') or 5)
    expires_in = int(data.get('expires_in') or data.get('expires') or 600)
    if interval < 1:
        interval = 5
    if not device_code or not user_code:
        error = start_resp.get('detail') or start_resp.get('error') or 'TorBox did not return an authorization code.'
        xbmcgui.Dialog().ok(addon_name, f'TorBox authorization failed.\n{error}')
        return

    def poll_token(dialog):
        start = time.time()
        while not dialog.cancelled and (time.time() - start) < expires_in:
            xbmc.sleep(interval * 1000)
            try:
                poll = requests.post(
                    'https://api.torbox.app/v1/api/user/auth/device/token',
                    json={'device_code': device_code},
                    timeout=20,
                ).json()
                poll_data = poll.get('data') or {}
                if poll.get('success') and poll_data.get('access_token'):
                    dialog.response = poll
                    dialog.close()
                    return
                error = (poll.get('error') or '').lower()
                detail = (poll.get('detail') or '').lower()
                pending_messages = (
                    'pending',
                    'not authorized',
                    'waiting',
                    'auth failed',
                    'auth_error',
                    'no auth',
                    'no token',
                    'not authenticated',
                )
                if any(text in error or text in detail for text in pending_messages):
                    continue
                terminal_messages = ('expired', 'denied', 'invalid device')
                if any(text in error or text in detail for text in terminal_messages):
                    dialog.response = poll
                    dialog.close()
                    return
                if poll.get('success') is False and error:
                    continue
            except Exception as e:
                dialog.error = e
                dialog.close()
                return
        dialog.cancelled = True
        try:
            dialog.close()
        except:
            pass

    poll = _show_debrid_qr_auth_window(addon_name, 'TorBox', verify_url, user_code, poll_token)
    poll_data = poll.get('data') if poll else {}
    api_key = poll_data.get('access_token', '') if isinstance(poll_data, dict) else ''
    if not api_key:
        if poll:
            xbmcgui.Dialog().ok(addon_name, f'TorBox authorization failed.\n{poll.get("detail") or poll.get("error") or "No token returned."}')
        else:
            xbmcgui.Dialog().ok(addon_name, 'TorBox authorization timed out or was cancelled.')
        return
    addon.setSetting('tb.token', api_key)
    addon.setSetting('tb.enabled', 'true')
    xbmcgui.Dialog().ok(addon_name, '[B]TorBox[/B] authorized successfully!')

@plugin.route("/revoke_service/<service>")
def revoke_service(service):
    import xbmcgui
    addon = xbmcaddon.Addon()
    addon_name = addon.getAddonInfo('name')
    service_names = {
        'rd': 'Real-Debrid',
        'pm': 'Premiumize',
        'ad': 'AllDebrid',
        'tb': 'TorBox'
    }
    name = service_names.get(service, service)
    confirm = xbmcgui.Dialog().yesno(addon_name, f'Revoke [B]{name}[/B] authorization?')
    if not confirm:
        return
    if service == 'rd':
        addon.setSetting('rd.token', '')
        addon.setSetting('rd.refresh', '')
        addon.setSetting('rd.client_id', '')
        addon.setSetting('rd.secret', '')
    elif service == 'pm':
        addon.setSetting('pm.token', '')
    elif service == 'ad':
        addon.setSetting('ad.token', '')
    elif service == 'tb':
        addon.setSetting('tb.token', '')
        addon.setSetting('tb.enabled', 'false')
    xbmcgui.Dialog().ok(addon_name, f'[B]{name}[/B] authorization revoked.')

def _finish_tmdb_auth(addon, addon_name, access_token, account_id, headers, requests, xbmcgui):
    session_resp = requests.post('https://api.themoviedb.org/3/authentication/session/convert/4',
        json={'access_token': access_token}, headers=headers, timeout=20).json()
    session_id = session_resp.get('session_id', '')
    if not session_resp.get('success') or not session_id:
        xbmcgui.Dialog().ok(addon_name, 'Failed to create TMDb session.\nAuthorization incomplete.')
        return False

    acct_resp = requests.get('https://api.themoviedb.org/3/account',
        params={'session_id': session_id}, headers=headers, timeout=20).json()
    username = acct_resp.get('username', '')
    account_session_id = str(acct_resp.get('id', ''))
    addon.setSetting('tmdb.token', access_token)
    addon.setSetting('tmdb.account_id', str(account_id))
    addon.setSetting('tmdb.username', username)
    addon.setSetting('tmdb.session_id', session_id)
    addon.setSetting('tmdb.account_session_id', account_session_id)
    xbmcgui.Dialog().ok(addon_name, f'[B]TMDb Account[/B] authorized successfully!\nUsername: [B]{username}[/B]')
    return True

def _poll_tmdb_auth(dialog, request_token, headers, requests, xbmc):
    count = 120
    while not dialog.cancelled and count >= 0 and dialog.response is None:
        count -= 1
        xbmc.sleep(2500)
        try:
            resp = requests.post('https://api.themoviedb.org/4/auth/access_token',
                json={'request_token': request_token}, headers=headers, timeout=20).json()
            if resp.get('success') and resp.get('access_token'):
                dialog.response = resp
                dialog.close()
                return
        except Exception as e:
            do_log(f'tmdb auth poll error: {e}')
    dialog.cancelled = True
    try:
        dialog.close()
    except:
        pass

def _show_tmdb_qr_auth_window(addon_name, qr_url, token_url, request_token, headers, requests, xbmc, xbmcgui):
    import threading

    class TMDbQRAuthDialog(xbmcgui.WindowXMLDialog):
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92

        def __init__(self, *args, **kwargs):
            super(TMDbQRAuthDialog, self).__init__(*args, **kwargs)
            self.cancelled = False
            self.response = None

        def onAction(self, action):
            if action.getId() in (self.ACTION_PREVIOUS_MENU, self.ACTION_NAV_BACK):
                self.cancelled = True
                self.close()

    dialog = TMDbQRAuthDialog('tmdb_auth_qr.xml', PATH, 'Default', '1080i')
    dialog.setProperty('tmdb.title', f'{addon_name} - TMDb Account')
    dialog.setProperty('tmdb.qr_url', qr_url)
    dialog.setProperty('tmdb.auth_url', token_url)
    worker = threading.Thread(target=_poll_tmdb_auth, args=(dialog, request_token, headers, requests, xbmc))
    worker.daemon = True
    worker.start()
    dialog.doModal()
    dialog.cancelled = True
    worker.join(0.1)
    return dialog.response

@plugin.route("/tmdb_auth")
def tmdb_auth():
    import xbmc, xbmcgui, xbmcvfs, requests
    try:
        from resources.lib.util.tmdb_qr import build_qr_image_url
    except ImportError:
        from .resources.lib.util.tmdb_qr import build_qr_image_url
    addon = xbmcaddon.Addon()
    addon_name = addon.getAddonInfo('name')
    read_access_token = get_tmdb_read_access_token()
    if not read_access_token:
        xbmcgui.Dialog().ok(addon_name, 'The addon is missing its TMDb Read Access Token.\nPlease add the addon API credentials before authorizing a TMDb account.')
        return
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'Authorization': 'Bearer %s' % read_access_token
    }
    try:
        data = requests.post('https://api.themoviedb.org/4/auth/request_token', headers=headers, timeout=20).json()
        if not data.get('success'):
            xbmcgui.Dialog().ok(addon_name, 'Failed to get TMDb request token.\nCheck your Read Access Token.')
            return
        request_token = data['request_token']
        token_url = 'https://www.themoviedb.org/auth/access?request_token=%s' % request_token
        qr_url = build_qr_image_url(token_url, size=800)
        url_file = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.thearchives/tmdb_auth_url.txt')
        try:
            with open(url_file, 'w') as handle:
                handle.write(token_url)
        except Exception as e:
            do_log(f'tmdb_auth url file error: {e}')
        response = _show_tmdb_qr_auth_window(addon_name, qr_url, token_url, request_token, headers, requests, xbmc, xbmcgui)
        if not response:
            xbmcgui.Dialog().ok(addon_name, 'TMDb authorization timed out or was cancelled.')
            return
        _finish_tmdb_auth(addon, addon_name, response['access_token'], response['account_id'], headers, requests, xbmcgui)
    except Exception as e:
        do_log(f'tmdb_auth error: {e}')
        xbmcgui.Dialog().ok(addon_name, f'TMDb authorization failed.\n{str(e)}')

@plugin.route("/tmdb_revoke")
def tmdb_revoke():
    import xbmcgui
    addon = xbmcaddon.Addon()
    addon_name = addon.getAddonInfo('name')
    if not xbmcgui.Dialog().yesno(addon_name, 'Revoke [B]TMDb Account[/B] authorization?'):
        return
    addon.setSetting('tmdb.token', '')
    addon.setSetting('tmdb.account_id', '')
    addon.setSetting('tmdb.username', '')
    addon.setSetting('tmdb.session_id', '')
    addon.setSetting('tmdb.account_session_id', '')
    xbmcgui.Dialog().ok(addon_name, '[B]TMDb Account[/B] authorization revoked.')

register_routes(plugin)

def main():
    plugin.run()
    return 0

if __name__ == "__main__":
    main()
