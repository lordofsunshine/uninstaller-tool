import os
import shutil
import winreg
import re

def find_program_files(program):
    files_info = []
    total_size = 0
    
    install_location = program.get('install_location', '').strip()
    
    if install_location and os.path.exists(install_location):
        try:
            for root, dirs, files in os.walk(install_location):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        size = os.path.getsize(file_path)
                        files_info.append((file_path, size))
                        total_size += size
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
        
        return files_info, total_size
    
    uninstall_string = program.get('uninstall_string', '')
    if uninstall_string:
        exe_path = _extract_exe_path(uninstall_string)
        if exe_path and os.path.exists(exe_path):
            install_dir = os.path.dirname(exe_path)
            if install_dir and os.path.exists(install_dir):
                try:
                    for root, dirs, files in os.walk(install_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                size = os.path.getsize(file_path)
                                files_info.append((file_path, size))
                                total_size += size
                            except (OSError, PermissionError):
                                continue
                except (OSError, PermissionError):
                    pass
                
                return files_info, total_size
    
    program_name = program.get('name', '')
    publisher = program.get('publisher', '')
    
    found_dirs = _find_program_directories(program_name, publisher)
    
    for directory in found_dirs:
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        size = os.path.getsize(file_path)
                        files_info.append((file_path, size))
                        total_size += size
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            continue
    
    return files_info, total_size

def _extract_exe_path(uninstall_string):
    if not uninstall_string:
        return None
    
    uninstall_string = uninstall_string.strip()
    
    if uninstall_string.startswith('"'):
        match = re.search(r'"([^"]+)"', uninstall_string)
        if match:
            return match.group(1)
    
    parts = uninstall_string.split()
    if parts:
        potential_path = parts[0]
        if os.path.exists(potential_path):
            return potential_path
    
    match = re.search(r'([A-Za-z]:\\[^"\s]+\.exe)', uninstall_string, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None

def _find_program_directories(program_name, publisher):
    directories = []
    
    program_name_clean = _normalize_name(program_name)
    publisher_clean = _normalize_name(publisher) if publisher else ''
    
    search_locations = [
        os.environ.get('ProgramFiles', r'C:\Program Files'),
        os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
        os.path.join(os.environ.get('APPDATA', ''), 'Local', 'Programs')
    ]
    
    for location in search_locations:
        if not os.path.exists(location):
            continue
        
        try:
            for item in os.listdir(location):
                item_path = os.path.join(location, item)
                if not os.path.isdir(item_path):
                    continue
                
                item_normalized = _normalize_name(item)
                
                if _is_exact_match(item_normalized, program_name_clean):
                    directories.append(item_path)
                    continue
                
                if publisher_clean and _is_exact_match(item_normalized, publisher_clean):
                    subdir_path = os.path.join(item_path, program_name_clean)
                    if os.path.exists(subdir_path):
                        directories.append(subdir_path)
                    else:
                        for subitem in os.listdir(item_path):
                            subitem_path = os.path.join(item_path, subitem)
                            if os.path.isdir(subitem_path):
                                subitem_normalized = _normalize_name(subitem)
                                if _is_exact_match(subitem_normalized, program_name_clean):
                                    directories.append(subitem_path)
        except (OSError, PermissionError):
            continue
    
    return directories

def _normalize_name(name):
    if not name:
        return ''
    
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', '', name)
    return name

def _is_exact_match(name1, name2):
    return name1 == name2

def search_leftover_files(program_name):
    leftover_files = []
    leftover_registry = []
    
    program_name_clean = _normalize_name(program_name)
    
    search_locations = [
        os.environ.get('LOCALAPPDATA', ''),
        os.environ.get('APPDATA', ''),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'LocalLow'),
        os.environ.get('ProgramData', ''),
        os.environ.get('ProgramFiles', r'C:\Program Files'),
        os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
    ]
    
    for location in search_locations:
        if not location or not os.path.exists(location):
            continue
        
        try:
            for item in os.listdir(location):
                item_normalized = _normalize_name(item)
                
                if _is_exact_match(item_normalized, program_name_clean):
                    item_path = os.path.join(location, item)
                    leftover_files.append(item_path)
        except (OSError, PermissionError):
            continue
    
    leftover_registry = _search_leftover_registry(program_name)
    
    return {
        'files': leftover_files,
        'registry': leftover_registry
    }

def _search_leftover_registry(program_name):
    registry_entries = []
    program_name_normalized = _normalize_name(program_name)
    
    registry_locations = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE")
    ]
    
    for hkey, base_path in registry_locations:
        try:
            key = winreg.OpenKey(hkey, base_path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey_name_normalized = _normalize_name(subkey_name)
                    
                    if _is_exact_match(subkey_name_normalized, program_name_normalized):
                        hkey_name = "HKEY_LOCAL_MACHINE" if hkey == winreg.HKEY_LOCAL_MACHINE else "HKEY_CURRENT_USER"
                        registry_entries.append(f"{hkey_name}\\{base_path}\\{subkey_name}")
                except (OSError, WindowsError):
                    continue
            winreg.CloseKey(key)
        except (OSError, WindowsError):
            continue
    
    return registry_entries

def remove_leftovers(leftovers):
    errors = []
    removed_files = 0
    removed_registry = 0
    
    for file_path in leftovers.get('files', []):
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                removed_files += 1
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                removed_files += 1
        except PermissionError:
            errors.append(f"Permission denied: {file_path}")
        except FileNotFoundError:
            pass
        except Exception as e:
            errors.append(f"Error removing {file_path}: {str(e)}")
    
    for reg_entry in leftovers.get('registry', []):
        try:
            parts = reg_entry.split('\\', 1)
            if len(parts) < 2:
                continue
            
            hkey_name = parts[0]
            key_path = parts[1]
            
            if hkey_name == "HKEY_LOCAL_MACHINE":
                hkey = winreg.HKEY_LOCAL_MACHINE
            elif hkey_name == "HKEY_CURRENT_USER":
                hkey = winreg.HKEY_CURRENT_USER
            else:
                continue
            
            winreg.DeleteKey(hkey, key_path)
            removed_registry += 1
        except FileNotFoundError:
            pass
        except PermissionError:
            errors.append(f"Permission denied: {reg_entry}")
        except Exception as e:
            errors.append(f"Error removing registry key {reg_entry}: {str(e)}")
    
    if errors:
        print(f"Cleanup completed: {removed_files} files, {removed_registry} registry entries removed")
        print("Errors encountered:")
        for error in errors:
            print(f"  - {error}")
    
    return {
        'removed_files': removed_files,
        'removed_registry': removed_registry,
        'errors': errors
    }
