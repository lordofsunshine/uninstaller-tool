from __future__ import annotations

from PySide6.QtCore import Signal

from app.core.registry import RegistrySnapshot, scan_installed_programs
from app.core.store import fetch_store_apps, load_store_cache, save_store_cache
from app.logging_setup import get_logger
from app.workers.base import WorkerThread

LOGGER = get_logger("loader")


class LoaderThread(WorkerThread):
    registry_loaded = Signal(list)
    store_loaded = Signal(list)
    snapshot_ready = Signal(object)

    def work(self) -> None:
        programs = scan_installed_programs()
        if self.isInterruptionRequested():
            return

        snapshot = RegistrySnapshot.build()
        if self.isInterruptionRequested():
            return
        self.snapshot_ready.emit(snapshot)
        self.registry_loaded.emit(programs)

        cached, fresh = load_store_cache()
        if cached:
            self.store_loaded.emit(cached)
        if self.isInterruptionRequested():
            return

        if fresh or self.isInterruptionRequested():
            return

        try:
            programs = fetch_store_apps()
        except (OSError, ValueError, TimeoutError) as exc:
            LOGGER.warning("Store apps are unavailable: %s", exc)
            return
        if self.isInterruptionRequested():
            return
        save_store_cache(programs)
        self.store_loaded.emit(programs)

