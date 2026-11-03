from __future__ import annotations

from PySide6.QtCore import Signal

from app.core.leftovers import search_leftovers
from app.core.registry import RegistrySnapshot
from app.logging_setup import get_logger
from app.workers.base import WorkerThread

LOGGER = get_logger("leftovers-worker")


class LeftoversThread(WorkerThread):
    done = Signal(object)
    snapshot_ready = Signal(object)

    def __init__(
        self,
        program,
        snapshot: RegistrySnapshot | None,
        budget_seconds: float,
        parent=None,
        refresh_snapshot: bool = False,
    ):
        super().__init__(parent)
        self.program = program
        self.snapshot = snapshot
        self.budget_seconds = budget_seconds
        self.refresh_snapshot = refresh_snapshot

    def work(self) -> None:
        if self.refresh_snapshot:
            self.snapshot = RegistrySnapshot.build()
            self.snapshot_ready.emit(self.snapshot)
        result = search_leftovers(
            self.program,
            self.snapshot,
            budget_seconds=self.budget_seconds,
            cancel_check=self.isInterruptionRequested,
        )
        LOGGER.info("Leftover scan finished for %s", self.program.name)
        self.done.emit(result)
