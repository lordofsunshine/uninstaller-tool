from __future__ import annotations

import time

from PySide6.QtCore import Signal

from app.core.registry import scan_installed_programs
from app.core.store import fetch_store_apps, load_store_cache, save_store_cache
from app.logging_setup import get_logger
from app.workers.base import WorkerThread

LOGGER = get_logger("loader")

STORE_SCAN_DELAY = 1.5


class LoaderThread(WorkerThread):
    registry_loaded = Signal(list)
    store_loaded = Signal(list)

    def work(self) -> None:
        programs = scan_installed_programs()
        if self.isInterruptionRequested():
            return
        self.registry_loaded.emit(programs)

        cached, fresh = load_store_cache()
        if cached:
            self.store_loaded.emit(cached)
        if fresh or self.isInterruptionRequested():
            return

        deadline = time.monotonic() + STORE_SCAN_DELAY
        while time.monotonic() < deadline:
            if self.isInterruptionRequested():
                return
            self.msleep(100)

        try:
            programs = fetch_store_apps()
        except (OSError, ValueError, TimeoutError) as exc:
            LOGGER.warning("Store apps are unavailable: %s", exc)
            return
        if self.isInterruptionRequested():
            return
        save_store_cache(programs)
        self.store_loaded.emit(programs)
