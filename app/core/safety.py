from __future__ import annotations

import os
import re
import stat
import sys

_REPARSE_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_DRIVE_ONLY = re.compile(r"^[A-Za-z]:$")


def expand_path(value: str | os.PathLike[str] | None) -> str:
    text = str(value or "").strip().strip('"').strip()
    if not text:
        return ""
    text = os.path.expandvars(text)
    if _DRIVE_ONLY.fullmatch(text):
        text = text + os.sep
    return text


def normalize_path(value: str | os.PathLike[str] | None) -> str:
    text = expand_path(value)
    if not text:
        return ""
    try:
        return os.path.normcase(os.path.abspath(text))
    except (OSError, ValueError):
        return ""


def absolute_path(value: str | os.PathLike[str] | None) -> str:
    text = expand_path(value)
    if not text:
        return ""
    try:
        return os.path.abspath(text)
    except (OSError, ValueError):
        return ""


def path_depth(path: str) -> int:
    _, tail = os.path.splitdrive(normalize_path(path))
    if not tail:
        return 0
    return len([part for part in tail.split(os.sep) if part])


def is_within(path: str, root: str) -> bool:
    child = normalize_path(path)
    parent = normalize_path(root)
    if not child or not parent:
        return False
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def is_reparse_point(path: str) -> bool:
    if not path:
        return False
    try:
        info = os.lstat(path)
    except (OSError, ValueError):
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & _REPARSE_FLAG)


def has_reparse_component(path: str) -> bool:
    current = normalize_path(path)
    if not current:
        return False
    drive, _ = os.path.splitdrive(current)
    while current and current != drive + os.sep:
        if is_reparse_point(current):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return False


def windows_directory() -> str:
    return normalize_path(os.environ.get("SYSTEMROOT") or os.environ.get("WINDIR") or r"C:\Windows")


def program_roots() -> tuple[str, ...]:
    candidates = [
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
    ]
    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = normalize_path(candidate)
        if normalized and normalized not in seen and os.path.isdir(normalized):
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


def extra_roots() -> tuple[str, ...]:
    appdata = os.environ.get("APPDATA", "")
    local = os.environ.get("LOCALAPPDATA", "")
    program_data = os.environ.get("PROGRAMDATA", "")
    candidates = [
        os.environ.get("TEMP"),
        os.environ.get("TMP"),
        os.path.join(program_data, "Package Cache"),
        os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(program_data, r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(local, "Packages"),
        os.path.join(local, "Temp"),
    ]
    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = normalize_path(candidate)
        if normalized and normalized not in seen and os.path.isdir(normalized):
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


def protected_directories() -> tuple[str, ...]:
    system_drive = normalize_path(os.environ.get("SYSTEMDRIVE", "C:") or "C:")
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    profile = os.environ.get("USERPROFILE", "")
    candidates = [
        system_drive,
        windows_directory(),
        os.path.join(windows_directory(), "System32"),
        os.path.join(windows_directory(), "SysWOW64"),
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("PROGRAMDATA"),
        local,
        roaming,
        os.path.join(local, "Temp"),
        os.environ.get("TEMP"),
        os.environ.get("TMP"),
        profile,
        os.path.join(profile, "Desktop"),
        os.path.join(profile, "Documents"),
        os.path.join(profile, "Downloads"),
    ]
    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = normalize_path(candidate)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


def is_safe_program_directory(path: str) -> bool:
    candidate = normalize_path(path)
    if not candidate or not os.path.isdir(candidate):
        return False
    drive, tail = os.path.splitdrive(candidate)
    if not drive or not tail.strip("\\/"):
        return False
    if path_depth(candidate) < 2:
        return False
    if is_reparse_point(candidate) or has_reparse_component(candidate):
        return False

    for protected in protected_directories():
        if candidate == protected:
            return False
        if is_within(protected, candidate):
            return False

    if is_within(candidate, windows_directory()):
        return False

    return not any(candidate == root for root in program_roots())


def is_safe_removal_path(path: str, allowed_roots: tuple[str, ...] | list[str]) -> bool:
    candidate = normalize_path(path)
    if not candidate:
        return False
    drive, tail = os.path.splitdrive(candidate)
    if not drive or not tail.strip("\\/"):
        return False
    if path_depth(candidate) < 2:
        return False
    if is_within(candidate, windows_directory()):
        return False

    for protected in protected_directories():
        if candidate == protected:
            return False
        if is_within(protected, candidate):
            return False

    normalized_roots = [normalize_path(root) for root in allowed_roots]
    if not any(is_within(candidate, root) and candidate != root for root in normalized_roots if root):
        return False

    if is_reparse_point(candidate):
        return True
    return not has_reparse_component(candidate)


def is_windows() -> bool:
    return sys.platform == "win32"
