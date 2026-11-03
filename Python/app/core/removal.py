from __future__ import annotations

import os
import subprocess
from pathlib import Path

from app.core.files import remove_file, remove_tree
from app.core.leftovers import removal_roots
from app.core.registry import (
    delete_registry_entry,
    export_registry_key,
    registry_entry_is_safe,
)
from app.core.safety import is_reparse_point, is_safe_removal_path, normalize_path
from app.logging_setup import get_logger
from app.models.program import Leftovers, RegistryEntry, RemovalResult
from app.paths import backup_dir

LOGGER = get_logger("removal")


def _remove_path(path: str, roots: tuple[str, ...], result: RemovalResult) -> None:
    normalized = normalize_path(path)
    if not normalized or not os.path.exists(normalized):
        return
    if not is_safe_removal_path(normalized, roots):
        result.errors.append(f"Skipped unsafe path: {path}")
        LOGGER.warning("Skipped unsafe leftover path: %s", path)
        return

    if is_reparse_point(normalized):
        try:
            if remove_file(normalized):
                result.scheduled_files += 1
            else:
                result.removed_files += 1
        except OSError as exc:
            result.errors.append(f"Could not remove {path}: {exc}")
        return

    if os.path.isdir(normalized):
        removed, scheduled, errors = remove_tree(normalized)
        if removed:
            result.removed_files += 1
        result.scheduled_files += scheduled
        result.errors.extend(errors)
        return

    try:
        if remove_file(normalized):
            result.scheduled_files += 1
        else:
            result.removed_files += 1
    except OSError as exc:
        result.errors.append(f"Could not remove {path}: {exc}")


def _remove_registry_entry(
    entry: RegistryEntry,
    result: RemovalResult,
    directory: Path,
) -> None:
    if not registry_entry_is_safe(entry):
        result.errors.append(f"Skipped unsafe registry key: {entry.path}")
        LOGGER.warning("Skipped unsafe registry key: %s", entry.path)
        return

    try:
        backup = export_registry_key(entry, directory)
    except (OSError, subprocess.SubprocessError) as exc:
        result.errors.append(f"Could not back up {entry.path}: {exc}")
        return

    result.backups.append(backup)
    try:
        delete_registry_entry(entry)
    except OSError as exc:
        result.errors.append(f"Could not remove {entry.path}: {exc}")
        return

    result.removed_registry += 1


def remove_leftovers(leftovers: Leftovers, directory: Path | None = None) -> RemovalResult:
    result = RemovalResult()
    roots = removal_roots()
    for path in leftovers.files:
        _remove_path(path, roots, result)

    if leftovers.registry:
        target = directory or backup_dir()
        for entry in leftovers.registry:
            _remove_registry_entry(entry, result, target)

    LOGGER.info(
        "Removal finished: %s files, %s registry keys, %s scheduled",
        result.removed_files,
        result.removed_registry,
        result.scheduled_files,
    )
    return result
