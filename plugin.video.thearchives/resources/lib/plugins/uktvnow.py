import os, requests, time, json
import xbmc, xbmcaddon, xbmcgui
from xbmcvfs import translatePath
from base64 import b64encode, b64decode
from binascii import a2b_hex
from requests.sessions import HTTPAdapter
from resources.lib.plugin import Plugin, run_hook
from resources.lib.util.dialogs import link_dialog
try:
    from Crypto.Cipher import DES, PKCS1_v1_5
    from Crypto.Util.Padding import unpad
    from Crypto.PublicKey import RSA
except:
    try:
        from Cryptodome.Cipher import DES, PKCS1_v1_5
        from Cryptodome.Util.Padding import unpad
        from Cryptodome.PublicKey import RSA
    except:
        pass

addon = xbmcaddon.Addon()
USER_DATA_DIR = translatePath(addon.getAddonInfo("profile"))
ADDON_DATA_DIR = translatePath(addon.getAddonInfo("path"))
RESOURCES_DIR = os.path.join(ADDON_DATA_DIR, "resources")

class UKTVNow(Plugin):
    name = "uktvnow"
    priority = 100
    base_url = "https://rocktalk.net/tv/index.php"
    user_agent = "Dalvik/2.1.0 (Linux; U; Android 5.1.1; AFTS Build/LVY48F)"
    player_user_agent = "mediaPlayerhttp/2.5 (Linux;Android 5.1) ExoPlayerLib/2.6.1"
    json_config = {}

    def process_item(self, item):
        if self.name in item:
            link = item.get(self.name, "")
            if link == "categories":
                item["link"] = "uktvnow/categories"
                item["is_dir"] = True
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")), offscreen=True)
                return item
            elif type(link) == str and link.startswith("cat_"):
                item["link"] = "uktvnow/category/" + link[4:]
                item["is_dir"] = True
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")), offscreen=True)
                return item
            elif type(link) == int:
                item["link"] = "uktvnow/play/" + str(link)
                item["is_dir"] = False
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")), offscreen=True)
                return item
    
    def routes(self, plugin):
        @plugin.route("/uktvnow/categories")
        def categories():
            self.init_config()
            jen_list = [{
                "title": category,
                "thumbnail": "",
                "fanart": "",
                "uktvnow": "cat_" + category,
                "type": "dir",
            } for category in self.json_config["categories"]]

            jen_list = [run_hook("process_item", item) for item in jen_list]
            run_hook("display_list", jen_list)
        
        @plugin.route("/uktvnow/category/<category>")
        def category_channels(category):
            self.init_config()
            channels = list(filter(lambda x: x["cat_name"] == category, self.json_config["channels"]))
            jen_list = [{
                "title": f'[COLORblue]{channel["pk_id"]}[/COLOR] | {channel["channel_name"]}',
                "thumbnail": f"https://rocktalk.net/tv/{channel['img']}|User-Agent={self.user_agent}",
                "fanart": f"https://rocktalk.net/tv/{channel['img']}|User-Agent={self.user_agent}",
                "uktvnow": int(channel["pk_id"]),
                "type": "item"
            } for channel in channels]

            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item) for item in jen_list]
            run_hook("display_list", jen_list)
        
        @plugin.route("/uktvnow/play/<pk_id>")
        def play(pk_id):
            self.play_video(json.dumps({"uktvnow": pk_id}))
    
    def play_video(self, video):
        item = json.loads(video)
        if self.name in item:
            self.init_config()
            link = item.get(self.name)
            stream = self.get_channel_links(link)[0]
            if stream == None: return True
            xbmc.Player().play(stream)

    def init_config(self):
        if self.json_config != {}: return
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "USER-AGENT-tvtap-APP-V2"})
        self.s.mount("https://", HTTPAdapter(max_retries=5))
        config = os.path.join(USER_DATA_DIR, "uktvnow_config.json")
        if not os.path.exists(config):
            self.update_channels()
            self.write_config()
        else:
            f = open(config)
            json_config = json.loads(f.read())
            f.close()
            self.json_config = json_config
            if time.time() - json_config["data_age"] > 8 * 60 * 60:
                self.update_channels()
                self.write_config()
    
    def write_config(self):
        if not os.path.exists(USER_DATA_DIR):
            os.makedirs(USER_DATA_DIR)
        config = os.path.join(USER_DATA_DIR, "uktvnow_config.json")
        self.json_config["data_age"] = time.time()
        f = open(config, "w")
        f.write(json.dumps(self.json_config))
        f.close()
    
    def payload(self):
        pub_key = RSA.importKey(
            a2b_hex(
                "30819f300d06092a864886f70d010101050003818d003081890281"
                "8100bfa5514aa0550688ffde568fd95ac9130fcdd8825bdecc46f1"
                "8f6c6b440c3685cc52ca03111509e262dba482d80e977a938493ae"
                "aa716818efe41b84e71a0d84cc64ad902e46dbea2ec61071958826"
                "4093e20afc589685c08f2d2ae70310b92c04f9b4c27d79c8b5dbb9"
                "bd8f2003ab6a251d25f40df08b1c1588a4380a1ce8030203010001"
            )
        )
        msg = a2b_hex(
            "7b224d4435223a22695757786f45684237686167747948392b58563052513d3d5c6e222c22534"
            "84131223a2242577761737941713841327678435c2f5450594a74434a4a544a66593d5c6e227d"
        )
        cipher = PKCS1_v1_5.new(pub_key)
        return b64encode(cipher.encrypt(msg))

    def api_request(self, case, channel_id=None):
        headers = {"app-token": "37a6259cc0c1dae299a7866489dff0bd"}
        data = {"payload": self.payload(), "username": "603803577"}
        if channel_id:
            data["channel_id"] = channel_id
        params = {"case": case}
        r = self.s.post(self.base_url, headers=headers, params=params, data=data, timeout=5)
        r.raise_for_status()
        resp = r.json()
        if resp["success"] == 1:
            return resp["msg"]
        else:
            raise ValueError(resp["msg"])
    
    def update_channels(self):
        channels = self.api_request("get_all_channels")["channels"]
        categories = []
        [categories.append(category) for category in [channel.get("cat_name") for channel in channels] if category not in categories]
        self.json_config["categories"] = sorted(categories)
        self.json_config["channels"] = channels
    
    def get_channel_links(self, pk_id):
        _channel = self.api_request("get_channel_link_with_token_latest", pk_id)["channel"][0]
        links = []
        for stream in _channel.keys():
            if "stream" in stream or "chrome_cast" in stream:
                _crypt_link = _channel[stream]
                if _crypt_link:
                    d = DES.new(b"98221122", DES.MODE_ECB)
                    link = unpad(d.decrypt(b64decode(_crypt_link)), 8).decode("utf-8")
                    if not link == "dummytext" and link not in links:
                        links.append(link)
        return [l + (f"|User-Agent={self.player_user_agent}" if l.startswith("http") else "") for l in links]