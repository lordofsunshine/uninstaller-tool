from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.logging_setup import get_logger

LOGGER = get_logger("worker")


class WorkerThread(QThread):
    failed = Signal(str)
    completed = Signal()

    def run(self) -> None:
        try:
            self.work()
        except Exception as exc:
            LOGGER.exception("Worker %s failed", type(self).__name__)
            self.failed.emit(str(exc) or type(exc).__name__)
        finally:
            self.completed.emit()

    def work(self) -> None:
        raise NotImplementedError
