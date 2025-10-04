import winreg
import os

def get_installed_programs():
    programs = {}
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]

    for hkey, key_path in registry_paths:
        try:
            key = winreg.OpenKey(hkey, key_path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    
                    try:
                        program_info = {
                            'name': winreg.QueryValueEx(subkey, "DisplayName")[0].strip(),
                            'uninstall_string': winreg.QueryValueEx(subkey, "UninstallString")[0].strip(),
                            'install_location': '',
                            'publisher': '',
                            'install_date': '',
                            'version': '',
                            'size': '',
                            'url': '',
                            'contact': '',
                            'icon': ''
                        }

                        try: 
                            install_loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            if install_loc:
                                program_info['install_location'] = install_loc.strip().rstrip('\\')
                        except: pass
                        
                        try: program_info['publisher'] = winreg.QueryValueEx(subkey, "Publisher")[0]
                        except: pass
                        
                        try: program_info['install_date'] = winreg.QueryValueEx(subkey, "InstallDate")[0]
                        except: pass
                        
                        try: program_info['version'] = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                        except: pass
                        
                        try: 
                            size_value = winreg.QueryValueEx(subkey, "EstimatedSize")[0]
                            if size_value:
                                program_info['size'] = int(size_value)
                        except: pass
                        
                        try: program_info['url'] = winreg.QueryValueEx(subkey, "URLInfoAbout")[0]
                        except: pass
                        
                        try: program_info['contact'] = winreg.QueryValueEx(subkey, "HelpTelephone")[0]
                        except: pass
                        
                        try:
                            icon = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                            if icon:
                                program_info['icon'] = icon.strip()
                                if not program_info['install_location'] and '\\' in icon:
                                    icon_dir = icon.split(',')[0] if ',' in icon else icon
                                    if icon_dir and os.path.exists(icon_dir):
                                        install_dir = os.path.dirname(icon_dir)
                                        if install_dir:
                                            program_info['install_location'] = install_dir
                        except: pass

                        if program_info['name'] not in programs:
                            programs[program_info['name']] = program_info

                    except WindowsError:
                        continue
                    finally:
                        winreg.CloseKey(subkey)
                except WindowsError:
                    continue
            winreg.CloseKey(key)
        except WindowsError:
            continue

    return sorted(programs.values(), key=lambda x: x['name'].lower())

def search_leftover_registry(program_name):
    leftover_registry = []
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]

    for hkey, key_path in registry_paths:
        try:
            key = winreg.OpenKey(hkey, key_path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    try:
                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0].strip()
                        if program_name.lower() in display_name.lower():
                            leftover_registry.append(f"{key_path}\\{subkey_name}")
                    except WindowsError:
                        pass
                    finally:
                        winreg.CloseKey(subkey)
                except WindowsError:
                    continue
            winreg.CloseKey(key)
        except WindowsError:
            continue

    return leftover_registry
