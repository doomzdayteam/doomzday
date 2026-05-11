import sys
import json
import xbmc
import xbmcgui
import xbmcplugin
from .utils import add_dir
from uservar import buildfile, videos_url, changelog_dir
from .parser import XmlParser, TextParser, get_page
from .addonvar import addon_name, setting, addon_icon, addon_fanart, local_string, authorize, kodi_ver, kodi_versions, UPDATE_VERSION, CURRENT_BUILD, BUILD_VERSION
from .colors import colors

HANDLE = int(sys.argv[1])

COLOR1 = colors.color_text1
COLOR2 = colors.color_text2
COLOR3 = colors.color_text3
COLOR4 = colors.color_text4

def main_menu():
    xbmcplugin.setPluginCategory(HANDLE, COLOR1('Main Menu'))

    add_dir(COLOR1(f'<><> [B]Welcome to {addon_name}[/B] <><>'), '', '', addon_icon, addon_fanart, COLOR1(f'Welcome to {addon_name}'), isFolder=False)

    if UPDATE_VERSION > BUILD_VERSION:
        add_dir(COLOR3(f'[B]Build Update Available!!![/B]   [{CURRENT_BUILD} v{UPDATE_VERSION}]'), '', 32, addon_icon, addon_fanart, COLOR2(local_string(30110)), isFolder=False)  # Build Update Available
        
    elif CURRENT_BUILD not in ['No Build Installed', 'No Build']:
        add_dir(COLOR4(f'Installed Build:   {CURRENT_BUILD} v{BUILD_VERSION}'), '', '', addon_icon, addon_fanart, COLOR2(local_string(30111)), isFolder=False)  # Installed Build
    
    add_dir(COLOR2(local_string(30010)), '', 1, addon_icon, addon_fanart, COLOR2(local_string(30001)), isFolder=True)  # Build Menu
    
    add_dir(COLOR2(local_string(30011)), '', 5, addon_icon, addon_fanart, COLOR2(local_string(30002)), isFolder=True)  # Maintenance Menu
    
    add_dir(COLOR2(local_string(30026)),'',10,addon_icon,addon_fanart,COLOR2(local_string(30026)))  # Authorize Debrid Services

    if changelog_dir not in ['', 'http://', 'http://CHANGEME/'] and CURRENT_BUILD not in ['No Build Installed', 'No Build']:
        add_dir(COLOR2(f'View Build Changelog'), '', 101, addon_icon, addon_fanart, COLOR2(local_string(30109)), isFolder=False)  # View Build Changelog
    
    add_dir(COLOR2(local_string(30013)), '', 100, addon_icon, addon_fanart, COLOR2(local_string(30014)), isFolder=False)  # View Notification
    
    if videos_url not in ('', 'http://', 'http://CHANGEME'):
        add_dir(COLOR2('Videos'), videos_url, 30, addon_icon, addon_fanart, COLOR2('Videos'), isFolder=True) # Videos
    
    add_dir(COLOR2(local_string(30015)), '', 9, addon_icon, addon_fanart, COLOR2(local_string(30016)), isFolder=False)  # Settings

def build_menu():
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    xbmcplugin.setPluginCategory(HANDLE, local_string(30010))
    
    builds = []
    try:
       response = get_page(buildfile)
    except:
       xbmcgui.Dialog().notification(addon_name, 'No Build File Present!!', addon_icon, 3000)
       quit()
        
    if '"name":' in response or "'name':" in response:
        builds = json.loads(response)['builds']
    
    elif '<name>' in response:
        xml = XmlParser(response)
        builds = xml.parse_builds()
    
    elif 'name=' in response:
        text = TextParser(response)
        builds = text.parse_builds()
            
    for build in builds:
        name = (build.get('name', local_string(30018)))  # Unknown Name
        version = (build.get('version'))
        kodiversion = (build.get('kodi'))
        url = (build.get('url', ''))
        if url.startswith('https://www.dropbox.com'):
            url = url.replace('dl=0', 'dl=1')
        icon = (build.get('icon', addon_icon))
        fanart = (build.get('fanart', addon_fanart))
        description = (build.get('description', local_string(30019)))  # No Description Available.
        preview = (build.get('preview',None))
        
        if url.endswith('.xml') or url.endswith('.json') or url.endswith('.txt'):
            add_dir(COLOR2(name),url,1,icon,fanart,COLOR2(description),name2=name,version=version,kodi=kodiversion,isFolder=True)
            
        elif '20' in kodi_ver and version == '' and kodiversion == 'K20':
            add_dir(COLOR2(f'{name}'), url, '', icon, fanart, description, name2=name, isFolder=False) # K20 Build Menu Separators
        elif '21' in kodi_ver and version == '' and kodiversion == 'K21':
            add_dir(COLOR2(f'{name}'), url, '', icon, fanart, description, name2=name, isFolder=False) # K21 Build Menu Separators
        elif '22' in kodi_ver and version == '' and kodiversion == 'K22':
            add_dir(COLOR2(f'{name}'), url, '', icon, fanart, description, name2=name, isFolder=False) # K22 Build Menu Separators
            
        elif '20' in kodi_ver and kodiversion == 'K20':
            add_dir(COLOR2(f'{name}  (v{version})'), url, 3, icon, fanart, description, name2=name, version=version, kodi=kodiversion, isFolder=False) # K20 Build Menu
            if preview not in (None, '', 'http://', 'https://'):
                add_dir(COLOR1(local_string(30021) + ' ' + name + ' ' + local_string(30020) + ' ' + version), preview, 2, icon, fanart, COLOR2(description), name2=name, version=version, isFolder=False)  # Video Previews
                
        elif '21' in kodi_ver and kodiversion == 'K21':
            add_dir(COLOR2(f'{name}  (v{version})'), url, 3, icon, fanart, description, name2=name, version=version, kodi=kodiversion, isFolder=False) # K21 Build Menu
            if preview not in (None, '', 'http://', 'https://'):
                add_dir(COLOR1(local_string(30021) + ' ' + name + ' ' + local_string(30020) + ' ' + version), preview, 2, icon, fanart, COLOR2(description), name2=name, version=version, isFolder=False)  # Video Previews
                
        elif '22' in kodi_ver and kodiversion == 'K22':
            add_dir(COLOR2(f'{name}  (v{version})'), url, 3, icon, fanart, description, name2=name, version=version, kodi=kodiversion, isFolder=False) # K22 Build Menu
            if preview not in (None, '', 'http://', 'https://'):
                add_dir(COLOR1(local_string(30021) + ' ' + name + ' ' + local_string(30020) + ' ' + version), preview, 2, icon, fanart, COLOR2(description), name2=name, version=version, isFolder=False)  # Video Previews

        elif kodiversion == None or not any(x in kodiversion for x in kodi_versions):
            add_dir(COLOR2(f'{name} (v{version})'), url, 3, icon, fanart, description, name2=name, version=version, isFolder=False)  # Standard Build Menu
            if preview not in (None, '', 'http://', 'https://'):
                add_dir(COLOR1(local_string(30021) + ' ' + name + ' ' + local_string(30020) + ' ' + version), preview, 2, icon, fanart, COLOR2(description), name2=name, version=version, isFolder=False) 

def submenu_maintenance():
    xbmcplugin.setPluginCategory(HANDLE, COLOR1(local_string(30022)))  # Maintenance
    add_dir(COLOR1('<><> [B]Maintenance[/B] <><>'),'','',addon_icon,addon_fanart, COLOR1('***Maintenance***'),isFolder=False)
    add_dir(COLOR2(local_string(30023)),'',6,addon_icon,addon_fanart,COLOR2(local_string(30005)),isFolder=False)  # Clear Packages
    add_dir(COLOR2(local_string(30024)),'',7,addon_icon,addon_fanart,COLOR2(local_string(30008)),isFolder=False)  # Clear Thumbnails
    add_dir(COLOR2(local_string(30012)), '', 4, addon_icon, addon_fanart, COLOR2(local_string(30003)), isFolder=False)  # Fresh Start
    if '20' in kodi_ver:
        add_dir(COLOR2(local_string(30025)),'',8,addon_icon,addon_fanart,COLOR2(local_string(30009)),isFolder=False)  # Advanced Settings K20
    if '21' in kodi_ver:
        add_dir(COLOR2(local_string(30106)),'',29,addon_icon,addon_fanart,COLOR2(local_string(30009)),isFolder=False)  # Advanced Settings K21
    if '22' in kodi_ver:
        add_dir(COLOR2(local_string(30112)),'',31,addon_icon,addon_fanart,COLOR2(local_string(30009)),isFolder=False)  # Advanced Settings K22
    add_dir(COLOR2(local_string(30064)),'',11,addon_icon,addon_fanart,COLOR2(local_string(30064)), isFolder=False)  # Edit Whitelist
    add_dir(COLOR2('Backup/Restore Build'),'',12,addon_icon,addon_fanart, COLOR2('Backup and Restore Build'))  # Backup Build
    add_dir(COLOR2('Backup/Restore GUI & Skin Settings'),'',19,addon_icon,addon_fanart,COLOR2('Backup/Restore GUI & Skin Settings'))
    add_dir(COLOR2('Force Close'),'', 18, addon_icon,addon_fanart,COLOR2('Force Close Kodi'), isFolder=False)
    add_dir(COLOR2('Speedtest'),'',28,addon_icon,addon_fanart,COLOR2('Speedtest'), isFolder=False)
    add_dir(COLOR2('View Log'),'', 26, addon_icon,addon_fanart,COLOR2('View Log'), isFolder=False)

def backup_restore():
    xbmcplugin.setPluginCategory(HANDLE, COLOR1('Backup/Restore'))
    add_dir(COLOR1('<><> [B]Backup/Restore[/B] <><>'),'','',addon_icon,addon_fanart, COLOR1('Backup/Restore'), isFolder=False)
    add_dir(COLOR2('Backup Build'),'',13,addon_icon,addon_fanart, COLOR2('Backup Build'), isFolder=False)  # Backup Build
    add_dir(COLOR2('Restore Backup'),'',14, addon_icon,addon_fanart, COLOR2('Restore Backup'))  # Restore Backup
    add_dir(COLOR2('Change Backups Folder Location'),'',16,addon_icon,addon_fanart, COLOR2('Change the location where backups will be stored and accessed.'), isFolder=False)  # Backup Location
    add_dir(COLOR2('Reset Backups Folder Location'),'',17,addon_icon,addon_fanart, COLOR2('Set the backup location to its default.'), isFolder=False)  # Reset Backup Location

def restore_gui_skin():
    add_dir(COLOR1('<><> [B]Backup/Restore GUI & Skin Settings[/B] <><>'),'','',addon_icon,addon_fanart, COLOR1('Backup/Restore'), isFolder=False)
    add_dir(COLOR2('Backup GUI & Skin Settings'),'',22,addon_icon,addon_fanart,COLOR2('Backup GUI & Skin Settings'), isFolder=False)
    add_dir(COLOR2('Restore GUI Settings'),'',23, addon_icon,addon_fanart, COLOR2('Restore Your GUI Settings'), isFolder=False)
    add_dir(COLOR2('Restore Skin Settings'),'',24, addon_icon,addon_fanart, COLOR2('Restore Your Skin Settings'), isFolder=False)
    add_dir(COLOR2('Restore Build Default GUI Settings'),'',20,addon_icon,addon_fanart,COLOR2('Restore GUI Settings'), isFolder=False)  
    add_dir(COLOR2('Restore Build Default Skin Settings'),'',21, addon_icon,addon_fanart, COLOR2('Restore Skin Settings'), isFolder=False)


def authorize_menu():  ### deprecated use authorize.py methods
    xbmcplugin.setPluginCategory(HANDLE, local_string(30027))  # Authorize Services
    response = get_page(authorize)
    builds = json.loads(response)['items']
    for build in builds:
        name = (build.get('name', 'Unknown'))
        url = (build.get('url', ''))
        icon = (build.get('icon', addon_icon))
        fanart = (build.get('fanart', addon_fanart))
        add_dir(name,url,2,icon,fanart,name,name2=name,version='' ,isFolder=False)
