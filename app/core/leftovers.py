from __future__ import annotations

import os
import time
from collections.abc import Callable

from app.core.naming import normalize_name
from app.core.registry import RegistrySnapshot, registry_entry_is_safe
from app.core.safety import (
    absolute_path,
    extra_roots,
    is_reparse_point,
    is_safe_removal_path,
    normalize_path,
    program_roots,
)
from app.logging_setup import get_logger
from app.models.program import Leftovers

LOGGER = get_logger("leftovers")
CancelCheck = Callable[[], bool]


def removal_roots() -> tuple[str, ...]:
    values = [*program_roots(), *extra_roots()]
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_path(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


def _versioned_match(entry_name: str, target: str) -> bool:
    if len(target) < 4 or not entry_name.startswith(target):
        return False
    remainder = entry_name[len(target) :]
    if not remainder or len(remainder) > 24:
        return False
    return any(character.isdigit() for character in remainder)


def _iter_directories(location: str):
    try:
        entries = os.scandir(location)
    except OSError:
        return
    with entries:
        for entry in entries:
            try:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if is_reparse_point(entry.path):
                    continue
                yield entry
            except OSError:
                continue


def _collect_from_root(
    location: str,
    target_name: str,
    target_publisher: str,
    found: list[str],
    should_stop: Callable[[], bool],
) -> bool:
    for entry in _iter_directories(location):
        if should_stop():
            return True
        entry_name = normalize_name(entry.name)
        if entry_name == target_name:
            found.append(entry.path)
        elif target_publisher and entry_name == target_publisher:
            for child in _iter_directories(entry.path):
                if should_stop():
                    return True
                if normalize_name(child.name) == target_name:
                    found.append(child.path)
        elif _versioned_match(entry_name, target_name):
            found.append(entry.path)
    return False


def search_leftovers(
    program,
    snapshot: RegistrySnapshot | None = None,
    budget_seconds: float = 40.0,
    cancel_check: CancelCheck | None = None,
) -> Leftovers:
    name = str(getattr(program, "name", "") or "")
    publisher = str(getattr(program, "publisher", "") or "")
    package_family = str(getattr(program, "package_family", "") or "")
    result = Leftovers(
        program_key=str(getattr(program, "key", "") or ""),
        program_name=name,
    )
    target_name = normalize_name(name)
    target_publisher = normalize_name(publisher)
    if not target_name:
        return result

    started = time.monotonic()
    files: list[str] = []

    def should_stop() -> bool:
        return (cancel_check is not None and cancel_check()) or (
            time.monotonic() - started >= budget_seconds
        )

    if package_family:
        packages = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages")
        candidate = os.path.join(packages, package_family)
        if os.path.isdir(candidate) and is_safe_removal_path(candidate, removal_roots()):
            files.append(absolute_path(candidate) or candidate)

    for location in (*program_roots(), *extra_roots()):
        if should_stop():
            result.timed_out = True
            break
        if _collect_from_root(
            location,
            target_name,
            target_publisher,
            files,
            should_stop,
        ):
            result.timed_out = True
            break

    unique_files: list[str] = []
    seen: set[str] = set()
    for path in files:
        normalized = normalize_path(path)
        if (
            normalized
            and normalized not in seen
            and os.path.exists(normalized)
            and is_safe_removal_path(normalized, removal_roots())
        ):
            seen.add(normalized)
            unique_files.append(absolute_path(path) or normalized)

    result.files = sorted(unique_files)

    if snapshot is not None and not result.timed_out:
        entries = [
            entry
            for entry in snapshot.find(name, publisher)
            if registry_entry_is_safe(entry)
        ]
        result.registry = sorted(entries, key=lambda entry: entry.path.casefold())

    LOGGER.info(
        "Leftovers for %s: %s paths, %s registry keys",
        name,
        len(result.files),
        len(result.registry),
    )
    return result
