from __future__ import annotations

import ctypes
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime

from app.core.commands import reg_path
from app.core.naming import normalize_name
from app.core.safety import expand_path
from app.logging_setup import get_logger
from app.models.program import (
    Program,
    ProgramSource,
    RegistryEntry,
    RegistryEntryKind,
)
from app.utils import split_icon_reference

try:
    import winreg
except ImportError:
    winreg = None

LOGGER = get_logger("registry")

UNINSTALL_BASES: tuple[tuple[int, str, str], ...] = ()
SOFTWARE_BASES: tuple[tuple[int, str, str], ...] = ()

if winreg is not None:
    UNINSTALL_BASES = (
        (
            winreg.HKEY_LOCAL_MACHINE,
            "HKEY_LOCAL_MACHINE",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            "HKEY_LOCAL_MACHINE",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            "HKEY_CURRENT_USER",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
    )
    SOFTWARE_BASES = (
        (winreg.HKEY_LOCAL_MACHINE, "HKEY_LOCAL_MACHINE", r"SOFTWARE"),
        (winreg.HKEY_LOCAL_MACHINE, "HKEY_LOCAL_MACHINE", r"SOFTWARE\WOW6432Node"),
        (winreg.HKEY_CURRENT_USER, "HKEY_CURRENT_USER", r"SOFTWARE"),
    )

HIVES = {
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE if winreg is not None else 0,
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER if winreg is not None else 0,
}

RESERVED_SOFTWARE_KEYS = {
    "classes",
    "clients",
    "microsoft",
    "policies",
    "registeredapplications",
    "windows",
    "wow6432node",
    "uninstall",
    "microsoftoffice",
    "office",
}


def _read_value(key, name: str, default=""):
    if winreg is None:
        return default
    try:
        value = winreg.QueryValueEx(key, name)[0]
    except OSError:
        return default
    return value.strip() if isinstance(value, str) else value


def _safe_int(value, default: int = 0) -> int:
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError, OverflowError):
        return default


def clean_location(value: str | None) -> str:
    text = expand_path(value)
    if not text:
        return ""
    stripped = text.rstrip("\\/")
    if re.fullmatch(r"[A-Za-z]:", stripped):
        return stripped + "\\"
    return os.path.normpath(stripped)


def _icon_directory(display_icon: str) -> str:
    path, _ = split_icon_reference(display_icon)
    if path and os.path.isfile(path):
        return os.path.dirname(path)
    return ""


def scan_installed_programs() -> list[Program]:
    if winreg is None:
        return []

    programs: dict[tuple[str, str, str], Program] = {}
    for hive, hive_name, base_path in UNINSTALL_BASES:
        try:
            root = winreg.OpenKey(hive, base_path)
        except OSError:
            continue

        with root:
            try:
                count = winreg.QueryInfoKey(root)[0]
            except OSError:
                continue
            for index in range(count):
                try:
                    subkey_name = winreg.EnumKey(root, index)
                    subkey = winreg.OpenKey(root, subkey_name)
                except OSError:
                    continue

                with subkey:
                    name = str(_read_value(subkey, "DisplayName"))
                    regular = str(_read_value(subkey, "UninstallString"))
                    quiet = str(_read_value(subkey, "QuietUninstallString"))
                    uninstall = regular or quiet
                    system_component = str(_read_value(subkey, "SystemComponent", 0)) == "1"
                    if not name or not uninstall or system_component:
                        continue

                    icon = str(_read_value(subkey, "DisplayIcon"))
                    location = clean_location(_read_value(subkey, "InstallLocation"))
                    if not location:
                        location = clean_location(_icon_directory(icon))

                    version = str(_read_value(subkey, "DisplayVersion"))
                    program = Program(
                        name=name,
                        uninstall_string=os.path.expandvars(regular),
                        quiet_uninstall_string=os.path.expandvars(quiet),
                        install_location=location,
                        publisher=str(_read_value(subkey, "Publisher")),
                        install_date=str(_read_value(subkey, "InstallDate")),
                        version=version,
                        size_kb=_safe_int(_read_value(subkey, "EstimatedSize", 0)),
                        icon=os.path.expandvars(icon),
                        source=ProgramSource.REGISTRY,
                        registry_hive=hive_name,
                        registry_subkey=f"{base_path}\\{subkey_name}",
                    )
                    identity = (
                        name.casefold(),
                        version.casefold(),
                        uninstall.casefold(),
                    )
                    programs.setdefault(identity, program)

    return sorted(programs.values(), key=lambda item: item.name.casefold())


class RegistrySnapshot:
    def __init__(self, entries: list[RegistryEntry] | None = None):
        self.entries = list(entries or [])
        self._by_key_name: dict[str, list[RegistryEntry]] = defaultdict(list)
        self._by_display_name: dict[str, list[RegistryEntry]] = defaultdict(list)
        self._by_path: dict[str, RegistryEntry] = {}
        for entry in self.entries:
            self._by_path[entry.path.casefold()] = entry
            self._by_key_name[normalize_name(entry.key_name)].append(entry)
            if entry.display_name:
                self._by_display_name[normalize_name(entry.display_name)].append(entry)

    @classmethod
    def build(cls) -> RegistrySnapshot:
        if winreg is None:
            return cls([])

        entries: list[RegistryEntry] = []
        for hive, hive_name, base_path in UNINSTALL_BASES:
            for key_name, display_name in _iter_subkeys(hive, base_path):
                entries.append(
                    RegistryEntry(
                        hive=hive_name,
                        subkey=f"{base_path}\\{key_name}",
                        display_name=display_name,
                        key_name=key_name,
                        kind=RegistryEntryKind.UNINSTALL,
                    )
                )

        for hive, hive_name, base_path in SOFTWARE_BASES:
            for vendor_name in _iter_key_names(hive, base_path):
                if normalize_name(vendor_name) in RESERVED_SOFTWARE_KEYS:
                    continue
                vendor_path = f"{base_path}\\{vendor_name}"
                for product_name in _iter_key_names(hive, vendor_path):
                    if normalize_name(product_name) in RESERVED_SOFTWARE_KEYS:
                        continue
                    entries.append(
                        RegistryEntry(
                            hive=hive_name,
                            subkey=f"{vendor_path}\\{product_name}",
                            key_name=product_name,
                            kind=RegistryEntryKind.VENDOR,
                        )
                    )

        LOGGER.info("Registry snapshot contains %s entries", len(entries))
        return cls(entries)

    def find(self, name: str, publisher: str) -> list[RegistryEntry]:
        normalized_name = normalize_name(name)
        normalized_publisher = normalize_name(publisher)
        if not normalized_name:
            return []

        matches: list[RegistryEntry] = []
        seen: set[str] = set()

        def add(entry: RegistryEntry) -> None:
            key = entry.path.casefold()
            if key not in seen:
                seen.add(key)
                matches.append(entry)

        for entry in self._by_display_name.get(normalized_name, ()):
            if entry.kind is RegistryEntryKind.UNINSTALL:
                add(entry)

        for entry in self._by_key_name.get(normalized_name, ()):
            if entry.kind is RegistryEntryKind.VENDOR and normalized_publisher:
                vendor = _vendor_from_subkey(entry.subkey)
                if vendor == normalized_publisher:
                    add(entry)
            elif entry.kind is RegistryEntryKind.UNINSTALL and not entry.display_name:
                add(entry)

        return matches


def _iter_key_names(hive: int, path: str):
    if winreg is None:
        return
    try:
        key = winreg.OpenKey(hive, path)
    except OSError:
        return
    with key:
        try:
            count = winreg.QueryInfoKey(key)[0]
        except OSError:
            return
        for index in range(count):
            try:
                yield winreg.EnumKey(key, index)
            except OSError:
                continue


def _iter_subkeys(hive: int, path: str):
    if winreg is None:
        return
    for subkey in _iter_key_names(hive, path):
        try:
            with winreg.OpenKey(hive, f"{path}\\{subkey}") as key:
                display_name = str(_read_value(key, "DisplayName"))
        except OSError:
            display_name = ""
        yield subkey, display_name


def _subkey_parts(subkey: str) -> list[str]:
    return [part for part in subkey.split("\\") if part]


def _vendor_from_subkey(subkey: str) -> str:
    parts = _subkey_parts(subkey)
    if len(parts) == 3:
        return normalize_name(parts[1])
    if len(parts) == 4 and normalize_name(parts[1]) == "wow6432node":
        return normalize_name(parts[2])
    return ""


def registry_entry_is_safe(entry: RegistryEntry) -> bool:
    if winreg is None or entry.hive not in HIVES:
        return False
    subkey = entry.subkey
    if not subkey or "*" in subkey or "?" in subkey:
        return False

    if entry.kind is RegistryEntryKind.UNINSTALL:
        for _, _, base_path in UNINSTALL_BASES:
            prefix = base_path + "\\"
            if subkey.casefold().startswith(prefix.casefold()):
                remainder = subkey[len(prefix) :]
                return bool(remainder) and "\\" not in remainder
        return False

    parts = _subkey_parts(subkey)
    if not parts or normalize_name(parts[0]) != "software":
        return False
    if len(parts) == 3:
        vendor, product = parts[1], parts[2]
    elif len(parts) == 4 and normalize_name(parts[1]) == "wow6432node":
        vendor, product = parts[2], parts[3]
    else:
        return False
    if normalize_name(vendor) in RESERVED_SOFTWARE_KEYS:
        return False
    if normalize_name(product) in RESERVED_SOFTWARE_KEYS:
        return False
    return bool(vendor and product)


def export_registry_key(entry: RegistryEntry, directory) -> str:
    if not registry_entry_is_safe(entry):
        raise OSError(f"Refusing to export an unsafe registry key: {entry.path}")
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = re.sub(r"[^\w.-]+", "_", entry.path)[:120].strip("_")
    target = directory / f"{safe_name}-{timestamp}.reg"
    result = subprocess.run(
        [reg_path(), "export", entry.path, str(target), "/y"],
        capture_output=True,
        timeout=30,
        creationflags=0x08000000,
        check=False,
    )
    if result.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
        message = _decode_reg_output(
            b"\n".join(part for part in (result.stderr, result.stdout) if part)
        ).strip()
        raise OSError(message or f"Could not export {entry.path}")
    LOGGER.info("Exported registry backup: %s", target)
    return str(target)


def _decode_reg_output(output: bytes) -> str:
    encodings = ["utf-8-sig"]
    if os.name == "nt":
        try:
            code_page = ctypes.windll.kernel32.GetOEMCP()
            if code_page:
                encodings.append(f"cp{code_page}")
        except (AttributeError, OSError, ValueError):
            pass
    encodings.extend(("mbcs", "cp866", "cp1251"))
    for encoding in encodings:
        try:
            return output.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return output.decode("utf-8", errors="replace")


def delete_registry_entry(entry: RegistryEntry) -> None:
    if not registry_entry_is_safe(entry):
        raise OSError(f"Refusing to delete an unsafe registry key: {entry.path}")
    hive = HIVES[entry.hive]
    _delete_tree(hive, entry.subkey)
    LOGGER.info("Deleted registry key: %s", entry.path)


def _delete_tree(hive: int, path: str) -> None:
    if winreg is None:
        return
    try:
        key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except FileNotFoundError:
        return
    with key:
        while True:
            try:
                child = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_tree(hive, f"{path}\\{child}")
    winreg.DeleteKey(hive, path)
