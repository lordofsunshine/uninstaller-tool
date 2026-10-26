from __future__ import annotations

import ctypes
import heapq
import os
import stat
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from app.core.naming import normalize_name
from app.core.safety import (
    absolute_path,
    is_reparse_point,
    is_safe_program_directory,
    normalize_path,
    program_roots,
)
from app.logging_setup import get_logger

LOGGER = get_logger("files")
CancelCheck = Callable[[], bool]


@dataclass(slots=True)
class FileScan:
    files: list[tuple[str, int]] = field(default_factory=list)
    total_count: int = 0
    total_size: int = 0
    directories: list[str] = field(default_factory=list)
    truncated: bool = False
    cancelled: bool = False


def iter_files(directory: str, cancel_check: CancelCheck | None = None) -> Iterator[tuple[str, int]]:
    if not is_safe_program_directory(directory):
        return
    stack = [absolute_path(directory) or normalize_path(directory)]
    while stack:
        current = stack.pop()
        if cancel_check is not None and cancel_check():
            return
        try:
            entries = os.scandir(current)
        except OSError:
            continue
        with entries:
            for entry in entries:
                if cancel_check is not None and cancel_check():
                    return
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if not is_reparse_point(entry.path):
                            stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        try:
                            size = entry.stat(follow_symlinks=False).st_size
                        except OSError:
                            continue
                        yield entry.path, size
                except OSError:
                    continue


def scan_directory(
    directory: str,
    top_n: int = 5000,
    cancel_check: CancelCheck | None = None,
) -> FileScan:
    result = FileScan()
    if not is_safe_program_directory(directory):
        return result
    result.directories.append(absolute_path(directory) or normalize_path(directory))
    heap: list[tuple[int, int, str]] = []
    for counter, (path, size) in enumerate(iter_files(directory, cancel_check), start=1):
        result.total_count += 1
        result.total_size += size
        heapq.heappush(heap, (size, counter, path))
        if len(heap) > top_n:
            heapq.heappop(heap)
    result.files = [(path, size) for size, _, path in sorted(heap, reverse=True)]
    result.truncated = result.total_count > top_n
    result.cancelled = bool(cancel_check is not None and cancel_check())
    return result


def merge_scans(scans: list[FileScan], top_n: int = 5000) -> FileScan:
    merged = FileScan()
    heap: list[tuple[int, int, str]] = []
    counter = 0
    for scan in scans:
        merged.total_count += scan.total_count
        merged.total_size += scan.total_size
        merged.directories.extend(scan.directories)
        merged.truncated = merged.truncated or scan.truncated
        merged.cancelled = merged.cancelled or scan.cancelled
        for path, size in scan.files:
            counter += 1
            heapq.heappush(heap, (size, counter, path))
            if len(heap) > top_n:
                heapq.heappop(heap)
    merged.files = [(path, size) for size, _, path in sorted(heap, reverse=True)]
    merged.truncated = merged.truncated or merged.total_count > top_n
    return merged


def find_program_directories(program_name: str, publisher: str) -> list[str]:
    name = normalize_name(program_name)
    publisher_name = normalize_name(publisher)
    if not name:
        return []

    matches: list[str] = []
    for location in program_roots():
        try:
            entries = list(os.scandir(location))
        except OSError:
            continue
        for entry in entries:
            try:
                if not entry.is_dir(follow_symlinks=False) or is_reparse_point(entry.path):
                    continue
            except OSError:
                continue
            entry_name = normalize_name(entry.name)
            if entry_name == name:
                matches.append(entry.path)
            elif publisher_name and entry_name == publisher_name:
                try:
                    children = os.scandir(entry.path)
                except OSError:
                    continue
                with children:
                    for child in children:
                        try:
                            if (
                                child.is_dir(follow_symlinks=False)
                                and not is_reparse_point(child.path)
                                and normalize_name(child.name) == name
                            ):
                                matches.append(child.path)
                        except OSError:
                            continue

    result: list[str] = []
    seen: set[str] = set()
    for match in matches:
        normalized = normalize_path(match)
        if normalized and normalized not in seen and is_safe_program_directory(normalized):
            seen.add(normalized)
            result.append(absolute_path(match) or normalized)
    return result


def scan_program_files(
    program,
    top_n: int = 5000,
    cancel_check: CancelCheck | None = None,
) -> FileScan:
    location = str(getattr(program, "install_location", "") or "")
    if is_safe_program_directory(location):
        return scan_directory(location, top_n, cancel_check)

    directories = find_program_directories(
        str(getattr(program, "name", "") or ""),
        str(getattr(program, "publisher", "") or ""),
    )
    scans = [
        scan_directory(directory, top_n, cancel_check)
        for directory in directories
        if cancel_check is None or not cancel_check()
    ]
    return merge_scans(scans, top_n)


def measure_dir_size(directory: str, cancel_check: CancelCheck | None = None) -> int:
    if not is_safe_program_directory(directory):
        return 0
    total = 0
    for _, size in iter_files(directory, cancel_check):
        total += size
    return total


def directory_stamp(directory: str) -> int:
    try:
        return os.stat(directory).st_mtime_ns
    except OSError:
        return 0


def _delete_link(path: str) -> None:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode):
        os.rmdir(path)
    else:
        os.unlink(path)


def _schedule_delete(path: str) -> bool:
    if sys.platform != "win32":
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    move_file = kernel32.MoveFileExW
    move_file.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    move_file.restype = ctypes.c_int
    if move_file(path, None, 0x4):
        return True
    raise ctypes.WinError(ctypes.get_last_error())


def remove_file(path: str) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    if is_reparse_point(path):
        _delete_link(path)
        return False
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


def _remove_tree_inner(
    path: str,
    errors: list[str],
    scheduled: list[int],
    visited: set[str],
) -> bool:
    normalized = normalize_path(path)
    if not normalized or normalized in visited:
        return True
    visited.add(normalized)

    try:
        info = os.lstat(normalized)
    except FileNotFoundError:
        return True
    except OSError as exc:
        errors.append(f"{path}: {exc}")
        return False

    if is_reparse_point(normalized):
        try:
            _delete_link(normalized)
            return True
        except FileNotFoundError:
            return True
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            return False

    if not stat.S_ISDIR(info.st_mode):
        try:
            if remove_file(normalized):
                scheduled[0] += 1
                return False
            return True
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            return False

    removed = True
    try:
        children = list(os.scandir(normalized))
    except FileNotFoundError:
        return True
    except OSError as exc:
        errors.append(f"{path}: {exc}")
        return False

    for child in children:
        if not _remove_tree_inner(child.path, errors, scheduled, visited):
            removed = False

    try:
        os.rmdir(normalized)
        return removed
    except FileNotFoundError:
        return removed
    except OSError:
        try:
            if _schedule_delete(normalized):
                scheduled[0] += 1
                return False
        except OSError as exc:
            errors.append(f"{path}: {exc}")
        return False


def remove_tree(path: str) -> tuple[bool, int, list[str]]:
    errors: list[str] = []
    scheduled = [0]
    removed = _remove_tree_inner(path, errors, scheduled, set())
    return removed, scheduled[0], errors


__all__ = [
    "FileScan",
    "directory_stamp",
    "find_program_directories",
    "iter_files",
    "measure_dir_size",
    "merge_scans",
    "remove_file",
    "remove_tree",
    "scan_directory",
    "scan_program_files",
]
