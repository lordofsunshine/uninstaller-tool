from __future__ import annotations

import contextlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path

from app.core.files import directory_stamp, measure_dir_size
from app.core.safety import is_safe_program_directory, normalize_path
from app.logging_setup import get_logger
from app.paths import cache_dir

LOGGER = get_logger("sizes")
CACHE_FILE = cache_dir() / "folder_sizes.json"
ProgressCallback = Callable[[int, int, str], None]
CancelCheck = Callable[[], bool]


class FolderSizeCache:
    def __init__(self, path: Path = CACHE_FILE):
        self.path = path
        self._entries: dict[str, dict[str, int]] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    try:
                        mtime = max(0, int(value.get("mtime") or 0))
                        size = max(0, int(value.get("size") or 0))
                    except (TypeError, ValueError, OverflowError):
                        continue
                    self._entries[str(key)] = {"mtime": mtime, "size": size}

    def get(self, directory: str) -> int | None:
        key = normalize_path(directory)
        if not key:
            return None
        entry = self._entries.get(key)
        if not entry:
            return None
        if entry["mtime"] != directory_stamp(key):
            return None
        return max(0, entry["size"])

    def put(self, directory: str, size: int) -> None:
        key = normalize_path(directory)
        if not key:
            return
        self._entries[key] = {
            "mtime": directory_stamp(key),
            "size": max(0, int(size)),
        }
        self._dirty = True

    def save(self) -> None:
        if not self._dirty:
            return
        temporary = self.path.with_suffix(".tmp")
        try:
            temporary.write_text(
                json.dumps(self._entries, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(temporary, self.path)
            self._dirty = False
        except OSError as exc:
            LOGGER.warning("Could not save the folder size cache: %s", exc)
            with contextlib.suppress(OSError):
                temporary.unlink(missing_ok=True)


def measure_program(program, cache: FolderSizeCache, cancel_check: CancelCheck | None = None) -> int:
    directory = str(getattr(program, "install_location", "") or "")
    if not is_safe_program_directory(directory):
        return 0
    cached = cache.get(directory)
    if cached is not None:
        return cached
    started = time.monotonic()
    size = measure_dir_size(directory, cancel_check)
    cache.put(directory, size)
    LOGGER.info("Measured %s in %.1fs: %s bytes", directory, time.monotonic() - started, size)
    return size


def measure_programs(
    programs,
    cache: FolderSizeCache,
    progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> dict[str, int]:
    results: dict[str, int] = {}
    total = len(programs)
    for index, program in enumerate(programs):
        if cancel_check is not None and cancel_check():
            break
        if progress is not None:
            progress(index, total, str(getattr(program, "name", "") or ""))
        size = measure_program(program, cache, cancel_check)
        if size > 0:
            results[program.key] = size
    cache.save()
    return results
