import ctypes
import os
import re
import stat
import winreg

def _normalize_name(name):
    return re.sub(r"[^\w]+", "", str(name or "").casefold())


def _unique_existing_paths(paths):
    result = []
    seen = set()
    for path in paths:
        if not path:
            continue
        normalized = os.path.normcase(os.path.abspath(os.path.expandvars(path)))
        if normalized not in seen and os.path.isdir(normalized):
            seen.add(normalized)
            result.append(normalized)
    return result


def _program_roots():
    return _unique_existing_paths(
        [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
            os.environ.get("LOCALAPPDATA"),
            os.environ.get("APPDATA"),
            os.environ.get("ProgramData"),
        ]
    )


def _is_safe_program_directory(path):
    if not path:
        return False
    candidate = os.path.normcase(os.path.abspath(os.path.expandvars(path.strip().strip('"'))))
    if not os.path.isdir(candidate):
        return False
    drive, tail = os.path.splitdrive(candidate)
    if not tail.strip("\\/") or candidate == os.path.normcase(os.path.abspath(drive + os.sep)):
        return False
    protected = {
        os.path.normcase(os.path.abspath(value))
        for value in (os.environ.get("WINDIR"), os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"))
        if value
    }
    if candidate in protected:
        return False
    windows_directory = os.environ.get("WINDIR")
    if windows_directory:
        try:
            if os.path.commonpath([candidate, os.path.normcase(os.path.abspath(windows_directory))]) == os.path.normcase(
                os.path.abspath(windows_directory)
            ):
                return False
        except ValueError:
            pass
    return True


def _walk_files(directory, cancel_check=None):
    files_info = []
    total_size = 0
    for root, directories, files in os.walk(directory, followlinks=False):
        if cancel_check and cancel_check():
            break
        directories[:] = [item for item in directories if not os.path.islink(os.path.join(root, item))]
        for filename in files:
            path = os.path.join(root, filename)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            files_info.append((path, size))
            total_size += size
    return files_info, total_size


def measure_dir_size(directory, cancel_check=None, file_cap=30000):
    # fast size-only walk for disk usage dialog, caps files to stay responsive
    total = 0
    counted = 0
    if not _is_safe_program_directory(directory):
        return 0
    for root, directories, files in os.walk(directory, followlinks=False):
        if cancel_check and cancel_check():
            break
        directories[:] = [item for item in directories if not os.path.islink(os.path.join(root, item))]
        for filename in files:
            try:
                total += os.path.getsize(os.path.join(root, filename))
            except OSError:
                continue
            counted += 1
            if counted >= file_cap:
                return total
    return total


def find_program_files(program, cancel_check=None):
    install_location = str(program.get("install_location") or "").strip()
    if _is_safe_program_directory(install_location):
        return _walk_files(install_location, cancel_check)

    directories = _find_program_directories(program.get("name", ""), program.get("publisher", ""))
    combined = []
    total_size = 0
    seen = set()
    for directory in directories:
        files, size = _walk_files(directory, cancel_check)
        for path, file_size in files:
            normalized = os.path.normcase(path)
            if normalized not in seen:
                seen.add(normalized)
                combined.append((path, file_size))
        total_size += size
    return combined, total_size


def _find_program_directories(program_name, publisher):
    program_name_clean = _normalize_name(program_name)
    publisher_clean = _normalize_name(publisher)
    if not program_name_clean:
        return []

    matches = []
    search_locations = _unique_existing_paths(
        [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        ]
    )
    for location in search_locations:
        try:
            entries = list(os.scandir(location))
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            entry_name = _normalize_name(entry.name)
            if entry_name == program_name_clean:
                matches.append(entry.path)
            elif publisher_clean and entry_name == publisher_clean:
                try:
                    subdirectories = os.scandir(entry.path)
                except OSError:
                    continue
                with subdirectories:
                    for subdirectory in subdirectories:
                        if subdirectory.is_dir(follow_symlinks=False) and _normalize_name(
                            subdirectory.name
                        ) == program_name_clean:
                            matches.append(subdirectory.path)
    return _unique_existing_paths(matches)


def _extra_leftover_roots():
    # temp, caches and shortcuts often survive uninstall
    appdata = os.environ.get("APPDATA", "")
    program_data = os.environ.get("ProgramData", "")
    return _unique_existing_paths(
        [
            os.environ.get("TEMP"),
            os.environ.get("TMP"),
            os.path.join(program_data, "Package Cache"),
            os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(program_data, r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup"),
            os.path.join(program_data, r"Microsoft\Windows\Start Menu\Programs\StartUp"),
        ]
    )


def search_leftover_files(program_name, publisher="", package_family=""):
    normalized_name = _normalize_name(program_name)
    normalized_pub = _normalize_name(publisher)
    files = []
    if package_family:
        # store app data lives one level deeper, plain scan never reaches it
        packages_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages", package_family)
        if os.path.isdir(packages_dir):
            files.append(os.path.normpath(packages_dir))
    if normalized_name:
        for location in (*_program_roots(), *_extra_leftover_roots()):
            try:
                entries = os.scandir(location)
            except OSError:
                continue
            with entries:
                for entry in entries:
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        continue
                    entry_clean = _normalize_name(entry.name)
                    if entry_clean == normalized_name:
                        files.append(entry.path)
                    elif normalized_pub and entry_clean == normalized_pub:
                        # publisher folder may contain the program as subfolder
                        try:
                            subs = os.scandir(entry.path)
                        except OSError:
                            continue
                        with subs:
                            for sub in subs:
                                try:
                                    if sub.is_dir(follow_symlinks=False) and _normalize_name(sub.name) == normalized_name:
                                        files.append(sub.path)
                                except OSError:
                                    continue
                    elif len(normalized_name) >= 4 and normalized_name in entry_clean and is_dir:
                        # versioned folders like "myapp_1.2.3"
                        files.append(entry.path)
    return {"files": sorted(set(files)), "registry": _search_leftover_registry(program_name, publisher)}


def _search_leftover_registry(program_name, publisher=""):
    normalized_name = _normalize_name(program_name)
    normalized_pub = _normalize_name(publisher)
    if not normalized_name:
        return []
    registry_locations = (
        (winreg.HKEY_LOCAL_MACHINE, "HKEY_LOCAL_MACHINE", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, "HKEY_LOCAL_MACHINE", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, "HKEY_CURRENT_USER", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, "HKEY_CURRENT_USER", r"SOFTWARE"),
        (winreg.HKEY_LOCAL_MACHINE, "HKEY_LOCAL_MACHINE", r"SOFTWARE"),
    )
    entries = []
    for hive, hive_name, base_path in registry_locations:
        try:
            root = winreg.OpenKey(hive, base_path)
        except OSError:
            continue
        with root:
            count = winreg.QueryInfoKey(root)[0]
            for index in range(count):
                try:
                    subkey_name = winreg.EnumKey(root, index)
                except OSError:
                    continue
                clean = _normalize_name(subkey_name)
                if clean == normalized_name:
                    entries.append(f"{hive_name}\\{base_path}\\{subkey_name}")
                elif len(normalized_name) >= 4 and normalized_name in clean:
                    # catches versioned keys like "myapp_is1"
                    entries.append(f"{hive_name}\\{base_path}\\{subkey_name}")
                elif normalized_pub and clean == normalized_pub and base_path.endswith("SOFTWARE"):
                    # settings often hide under vendor key, look one level deeper
                    entries.extend(_match_vendor_subkeys(hive, hive_name, base_path, subkey_name, normalized_name))
    return sorted(set(entries))


def _match_vendor_subkeys(hive, hive_name, base_path, vendor_key, normalized_name):
    found = []
    try:
        vendor = winreg.OpenKey(hive, f"{base_path}\\{vendor_key}")
    except OSError:
        return found
    with vendor:
        try:
            count = winreg.QueryInfoKey(vendor)[0]
        except OSError:
            return found
        for index in range(count):
            try:
                child = winreg.EnumKey(vendor, index)
            except OSError:
                continue
            clean = _normalize_name(child)
            if clean == normalized_name or (len(normalized_name) >= 4 and normalized_name in clean):
                found.append(f"{hive_name}\\{base_path}\\{vendor_key}\\{child}")
    return found


def _delete_registry_tree(hive, key_path):
    try:
        key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except FileNotFoundError:
        return
    with key:
        while True:
            try:
                child = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_registry_tree(hive, f"{key_path}\\{child}")
    winreg.DeleteKey(hive, key_path)


def _schedule_delete(path):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    move_file = kernel32.MoveFileExW
    move_file.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    move_file.restype = ctypes.c_int
    if move_file(path, None, 0x4):
        return
    raise ctypes.WinError(ctypes.get_last_error())


def _remove_file(path):
    try:
        os.remove(path)
        return False
    except FileNotFoundError:
        return False
    except OSError:
        try:
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
            os.remove(path)
            return False
        except FileNotFoundError:
            return False
        except OSError:
            _schedule_delete(path)
            return True


def _remove_tree(path):
    scheduled = 0
    errors = []

    def walk_error(exc):
        errors.append(str(exc))

    for root, directories, files in os.walk(path, topdown=False, onerror=walk_error, followlinks=False):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                scheduled += int(_remove_file(file_path))
            except OSError as exc:
                errors.append(f"{file_path}: {exc}")
        for directory in directories:
            directory_path = os.path.join(root, directory)
            try:
                if os.path.islink(directory_path):
                    scheduled += int(_remove_file(directory_path))
                else:
                    os.rmdir(directory_path)
            except FileNotFoundError:
                pass
            except OSError:
                try:
                    _schedule_delete(directory_path)
                    scheduled += 1
                except OSError as exc:
                    errors.append(f"{directory_path}: {exc}")

    try:
        os.rmdir(path)
        removed = True
    except FileNotFoundError:
        removed = True
    except OSError:
        try:
            _schedule_delete(path)
            scheduled += 1
            removed = False
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            removed = False
    return removed, scheduled, errors


def remove_leftovers(leftovers):
    errors = []
    removed_files = 0
    removed_registry = 0
    scheduled_files = 0
    allowed_roots = _program_roots()

    for path in leftovers.get("files", []):
        absolute = os.path.normcase(os.path.abspath(path))
        safe_path = False
        for root in allowed_roots:
            try:
                safe_path = os.path.commonpath([absolute, root]) == root and absolute != root
            except ValueError:
                safe_path = False
            if safe_path:
                break
        if not safe_path:
            errors.append(f"Skipped unsafe path: {path}")
            continue
        try:
            if os.path.isfile(absolute) or os.path.islink(absolute):
                scheduled_files += int(_remove_file(absolute))
                removed_files += int(not os.path.exists(absolute))
            elif os.path.isdir(absolute):
                removed, scheduled, remove_errors = _remove_tree(absolute)
                removed_files += int(removed)
                scheduled_files += scheduled
                errors.extend(remove_errors)
        except FileNotFoundError:
            pass
        except OSError as exc:
            errors.append(f"Could not remove {path}: {exc}")

    hives = {"HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE, "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER}
    for entry in leftovers.get("registry", []):
        hive_name, separator, key_path = entry.partition("\\")
        if not separator or hive_name not in hives:
            errors.append(f"Skipped invalid registry path: {entry}")
            continue
        try:
            _delete_registry_tree(hives[hive_name], key_path)
            removed_registry += 1
        except FileNotFoundError:
            pass
        except OSError as exc:
            errors.append(f"Could not remove registry key {entry}: {exc}")

    return {
        "removed_files": removed_files,
        "removed_registry": removed_registry,
        "scheduled_files": scheduled_files,
        "errors": errors,
    }
