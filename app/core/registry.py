import os
import re
import winreg

# hacking the pentagon

UNINSTALL_KEYS = (
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
)


def _read_value(key, name, default=""):
    try:
        value = winreg.QueryValueEx(key, name)[0]
    except OSError:
        return default
    return value.strip() if isinstance(value, str) else value


def _icon_directory(display_icon):
    if not display_icon:
        return ""
    path = os.path.expandvars(display_icon).strip().strip('"')
    path = re.sub(r",-?\d+$", "", path).strip().strip('"')
    return os.path.dirname(path) if os.path.isfile(path) else ""


def get_installed_programs():
    programs = {}

    for hive, key_path in UNINSTALL_KEYS:
        try:
            root = winreg.OpenKey(hive, key_path)
        except OSError:
            continue

        with root:
            for index in range(winreg.QueryInfoKey(root)[0]):
                try:
                    subkey_name = winreg.EnumKey(root, index)
                    subkey = winreg.OpenKey(root, subkey_name)
                except OSError:
                    continue

                with subkey:
                    name = _read_value(subkey, "DisplayName")
                    regular_uninstall = _read_value(subkey, "UninstallString")
                    quiet_uninstall = _read_value(subkey, "QuietUninstallString")
                    uninstall_string = regular_uninstall or quiet_uninstall
                    if not name or not uninstall_string or str(_read_value(subkey, "SystemComponent", 0)) == "1":
                        continue

                    icon = _read_value(subkey, "DisplayIcon")
                    install_location = _read_value(subkey, "InstallLocation").rstrip("\\/")
                    if not install_location:
                        install_location = _icon_directory(icon)

                    size_kb = _read_value(subkey, "EstimatedSize", 0)
                    try:
                        size_kb = max(0, int(size_kb or 0))
                    except (TypeError, ValueError, OverflowError):
                        size_kb = 0

                    program = {
                        "name": name,
                        "uninstall_string": os.path.expandvars(uninstall_string),
                        "quiet_uninstall_string": os.path.expandvars(quiet_uninstall),
                        "install_location": os.path.expandvars(install_location),
                        "publisher": _read_value(subkey, "Publisher"),
                        "install_date": _read_value(subkey, "InstallDate"),
                        "version": _read_value(subkey, "DisplayVersion"),
                        "size": size_kb,
                        "url": _read_value(subkey, "URLInfoAbout"),
                        "contact": _read_value(subkey, "HelpTelephone"),
                        "icon": os.path.expandvars(icon),
                    }
                    ver = program["version"] if program["version"] else subkey_name
                    identity = (
                        name.casefold(),
                        str(ver).casefold(),
                        uninstall_string.casefold(),
                    )
                    programs.setdefault(identity, program)

    return sorted(programs.values(), key=lambda item: item["name"].casefold())


def search_leftover_registry(program_name):
    name = program_name.casefold()
    matches = []
    for hive, key_path in UNINSTALL_KEYS:
        try:
            root = winreg.OpenKey(hive, key_path)
        except OSError:
            continue
        with root:
            for index in range(winreg.QueryInfoKey(root)[0]):
                try:
                    subkey_name = winreg.EnumKey(root, index)
                    with winreg.OpenKey(root, subkey_name) as subkey:
                        display_name = str(_read_value(subkey, "DisplayName"))
                except OSError:
                    continue
                if name in display_name.casefold():
                    matches.append(f"{key_path}\\{subkey_name}")
    return matches
