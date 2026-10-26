from __future__ import annotations

from PySide6.QtCore import Signal

from app.core.sizes import FolderSizeCache, measure_programs
from app.logging_setup import get_logger
from app.workers.base import WorkerThread

LOGGER = get_logger("sizes-worker")


class SizesThread(WorkerThread):
    progress = Signal(int, int, str)
    measured = Signal(object)

    def __init__(self, programs, parent=None):
        super().__init__(parent)
        self.programs = list(programs)

    def work(self) -> None:
        cache = FolderSizeCache()
        results = measure_programs(
            self.programs,
            cache,
            progress=lambda done, total, name: self.progress.emit(done, total, name),
            cancel_check=self.isInterruptionRequested,
        )
        self.measured.emit(results)
