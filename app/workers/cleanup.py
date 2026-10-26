from __future__ import annotations

from PySide6.QtCore import Signal

from app.core.removal import remove_leftovers
from app.logging_setup import get_logger
from app.models.program import Leftovers
from app.workers.base import WorkerThread

LOGGER = get_logger("cleanup-worker")


class CleanupThread(WorkerThread):
    done = Signal(object)

    def __init__(self, leftovers: Leftovers, parent=None):
        super().__init__(parent)
        self.leftovers = leftovers

    def work(self) -> None:
        result = remove_leftovers(self.leftovers)
        LOGGER.info(
            "Cleanup finished: %s files, %s registry keys",
            result.removed_files,
            result.removed_registry,
        )
        self.done.emit(result)
