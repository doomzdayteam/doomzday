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

def _auth_real_debrid(addon, addon_name):
    import xbmc, xbmcgui, json, time, requests
    base_url = 'https://api.real-debrid.com/oauth/v2/'
    client_id = addon.getSetting('rd.client_id') or ''
    if not client_id:
        client_id = 'X245A4XAIBGVM'
    resp = requests.get(f'{base_url}device/code?client_id={client_id}&new_credentials=yes').json()
    user_code = resp['user_code']
    device_code = resp['device_code']
    verify_url = resp.get('verification_url', 'https://real-debrid.com/device')
    interval = resp.get('interval', 5)
    expires_in = resp.get('expires_in', 600)
    progress = xbmcgui.DialogProgress()
    progress.create(f'{addon_name} - Real-Debrid',
        f'Go to: [B]{verify_url}[/B]\nEnter code: [B][COLOR lawngreen]{user_code}[/COLOR][/B]')
    start = time.time()
    client_secret = ''
    new_client_id = ''
    while not progress.iscanceled() and (time.time() - start) < expires_in:
        xbmc.sleep(interval * 1000)
        percent = int(((time.time() - start) / expires_in) * 100)
        progress.update(percent)
        try:
            poll = requests.get(f'{base_url}device/credentials?client_id={client_id}&code={device_code}').json()
            if 'client_id' in poll:
                new_client_id = poll['client_id']
                client_secret = poll['client_secret']
                break
        except:
            continue
    progress.close()
    if not new_client_id:
        xbmcgui.Dialog().ok(addon_name, 'Real-Debrid authorization timed out or was cancelled.')
        return
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
    default_client_id = ''
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
    progress = xbmcgui.DialogProgress()
    progress.create(f'{addon_name} - Premiumize', _premiumize_activation_message(verify_url, user_code))
    start = time.time()
    token = ''
    while not progress.iscanceled() and (time.time() - start) < expires_in:
        xbmc.sleep(interval * 1000)
        percent = int(((time.time() - start) / expires_in) * 100)
        progress.update(percent)
        try:
            poll = requests.post('https://www.premiumize.me/token', data={
                'grant_type': 'device_code',
                'code': device_code,
                'client_id': client_id,
            }).json()
            if 'access_token' in poll:
                token = poll['access_token']
                break
            error = poll.get('error', '')
            if error == 'authorization_pending':
                continue
            if error == 'slow_down':
                interval += 5
                continue
            if error in ('access_denied', 'invalid_grant'):
                progress.close()
                xbmcgui.Dialog().ok(addon_name, f'Premiumize authorization failed.\n{poll.get("error_description", error)}')
                return
        except Exception as e:
            progress.close()
            xbmcgui.Dialog().ok(addon_name, f'Premiumize authorization failed.\n{str(e)}')
            return
    progress.close()
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
    progress = xbmcgui.DialogProgress()
    progress.create(f'{addon_name} - AllDebrid',
        f'Go to: [B]{verify_url}[/B]\nEnter code: [B][COLOR lawngreen]{user_code}[/COLOR][/B]')
    start = time.time()
    token = ''
    while not progress.iscanceled() and (time.time() - start) < expires_in:
        xbmc.sleep(5000)
        percent = int(((time.time() - start) / expires_in) * 100)
        progress.update(percent)
        try:
            poll_data = alldebrid_client.check_pin(requests, user_code, check)
            if poll_data.get('activated'):
                token = poll_data.get('apikey', '')
                break
        except Exception as e:
            progress.close()
            xbmcgui.Dialog().ok(addon_name, f'AllDebrid authorization failed.\n{str(e)}')
            return
    progress.close()
    if not token:
        xbmcgui.Dialog().ok(addon_name, 'AllDebrid authorization timed out or was cancelled.')
        return
    store_token(token)
    xbmcgui.Dialog().ok(addon_name, '[B]AllDebrid[/B] authorized successfully!')

def _auth_torbox(addon, addon_name):
    import xbmcgui, requests
    try:
        from resources.lib.plugins import torbox_client
    except ImportError:
        from .resources.lib.plugins import torbox_client

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

@plugin.route("/tmdb_auth")
def tmdb_auth():
    import xbmc, xbmcgui, time, requests
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
        progress = xbmcgui.DialogProgress()
        progress.create(f'{addon_name} - TMDb Account',
            f'Go to:\n[B][COLOR lawngreen]{token_url}[/COLOR][/B]\n\nApprove access to your TMDb account, then wait...')
        count = 120
        success = None
        response = None
        while not progress.iscanceled() and count >= 0 and success is None:
            count -= 1
            percent = int(((120 - count) / 120.0) * 100)
            progress.update(percent)
            xbmc.sleep(2500)
            try:
                resp = requests.post('https://api.themoviedb.org/4/auth/access_token',
                    json={'request_token': request_token}, headers=headers, timeout=20).json()
                if resp.get('success') and resp.get('access_token'):
                    success = True
                    response = resp
            except:
                pass
        progress.close()
        if not success:
            xbmcgui.Dialog().ok(addon_name, 'TMDb authorization timed out or was cancelled.')
            return
        access_token = response['access_token']
        account_id = response['account_id']
        session_resp = requests.post('https://api.themoviedb.org/3/authentication/session/convert/4',
            json={'access_token': access_token}, headers=headers, timeout=20).json()
        session_id = session_resp.get('session_id', '')
        if session_resp.get('success') and session_id:
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
        else:
            xbmcgui.Dialog().ok(addon_name, 'Failed to create TMDb session.\nAuthorization incomplete.')
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
