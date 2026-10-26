from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core.processes import (
    batch_find_running,
    find_running_processes,
    kill_processes,
)
from app.core.registry import RegistrySnapshot
from app.elevation import is_admin, relaunch_as_admin
from app.logging_setup import get_logger
from app.models.program import Leftovers, Program
from app.ui.dialogs import LeftoversDialog
from app.workers.cleanup import CleanupThread
from app.workers.leftovers import LeftoversThread
from app.workers.uninstall import UninstallThread

LOGGER = get_logger("uninstall-controller")

LEFTOVERS_TIMEOUT = 40.0
NEXT_SCAN_DELAY = 350


class UninstallController(QObject):
    summary_changed = Signal(str)
    progress_changed = Signal(int, int)
    progress_indeterminate = Signal(bool)
    progress_visible = Signal(bool)
    stats_changed = Signal(str)
    status_changed = Signal(str, str)
    busy_changed = Signal(bool)
    finished = Signal()

    def __init__(
        self,
        parent: QWidget,
        colors_provider: Callable[[], dict],
        snapshot_provider: Callable[[], RegistrySnapshot | None],
    ):
        super().__init__(parent)
        self._parent = parent
        self._colors_provider = colors_provider
        self._snapshot_provider = snapshot_provider
        self._uninstall_worker: UninstallThread | None = None
        self._leftover_worker: LeftoversThread | None = None
        self._cleanup_worker: CleanupThread | None = None
        self._dialog: LeftoversDialog | None = None
        self._queue: list[Program] = []
        self._budget_left = LEFTOVERS_TIMEOUT
        self._scan_started = 0.0
        self._scan_handled = False
        self._leftover_snapshot: RegistrySnapshot | None = None
        self._reboot_required: list[str] = []
        self._active = False
        self._closing = False
        self._fatal_error = ""

    @property
    def busy(self) -> bool:
        return self._active

    def uninstall(self, programs: list[Program], silent: bool) -> bool:
        if self._active or self._closing:
            LOGGER.info("Ignored a duplicate uninstall request")
            return False
        if not programs:
            return False
        if not self._ensure_admin():
            return False

        ready = self.confirm_running(programs)
        if ready is None:
            return False
        if not ready:
            self.summary_changed.emit("Nothing left to uninstall")
            return False

        self._active = True
        self._fatal_error = ""
        self._leftover_snapshot = None
        self._reboot_required = []
        self.busy_changed.emit(True)
        self.progress_visible.emit(True)
        self.progress_indeterminate.emit(False)
        self.progress_changed.emit(0, len(ready))
        self.summary_changed.emit("Starting the uninstaller…")

        worker = UninstallThread(ready, silent, self._parent)
        worker.progress.connect(self._on_progress)
        worker.stats.connect(self.stats_changed)
        worker.failed.connect(self._on_uninstall_error)
        worker.completed.connect(self._on_uninstall_completed)
        worker.finished.connect(worker.deleteLater)
        self._uninstall_worker = worker
        worker.start()
        return True

    def confirm_running(self, programs: list[Program]) -> list[Program] | None:
        snapshot = batch_find_running(programs)
        ready: list[Program] = []
        for program in programs:
            entries = snapshot.get(program.key, [])
            if not entries:
                ready.append(program)
                continue

            listing = "\n".join(f"PID {entry.pid}  -  {entry.name}" for entry in entries[:10])
            answer = QMessageBox.question(
                self._parent,
                "Program is running",
                f"{program.name} is currently running:\n\n{listing}\n\n"
                "Terminate it and continue?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return None
            if answer == QMessageBox.StandardButton.No:
                LOGGER.info("Skipped %s because it is running", program.name)
                continue

            result = kill_processes(entries)
            remaining = find_running_processes(program)
            if remaining:
                details = "; ".join(result.get("errors", [])[:3])
                QMessageBox.warning(
                    self._parent,
                    "Could not terminate",
                    f"{program.name} is still running and will be skipped.\n{details}",
                )
                continue
            ready.append(program)
        return ready

    def _ensure_admin(self) -> bool:
        if is_admin():
            return True
        answer = QMessageBox.question(
            self._parent,
            "Administrator rights required",
            "Administrator rights are required to uninstall programs.\n\n"
            "Restart the app as administrator?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            LOGGER.info("The user declined to restart with administrator rights")
            self.summary_changed.emit(
                "Administrator rights are required to uninstall programs"
            )
            return False
        if relaunch_as_admin():
            LOGGER.info("Relaunching with administrator rights")
            QTimer.singleShot(0, QApplication.instance().quit)
            return False
        QMessageBox.critical(
            self._parent,
            "Error",
            "Windows could not restart the application as administrator.",
        )
        return False

    def _on_progress(
        self,
        done: int,
        total: int,
        key: str,
        status: str,
        message: str,
    ) -> None:
        self.progress_changed.emit(done, total)
        self.status_changed.emit(key, status)
        if message:
            self.summary_changed.emit(message)

    def _on_uninstall_error(self, message: str) -> None:
        self._fatal_error = message
        LOGGER.error("Uninstall worker failed: %s", message)

    def _on_uninstall_completed(self) -> None:
        worker = self._uninstall_worker
        self._uninstall_worker = None
        if worker is None:
            self._finish("Uninstallation finished")
            return

        self._reboot_required = list(worker.reboot_required)
        if self._fatal_error:
            self.summary_changed.emit("The uninstaller stopped unexpectedly")
            QMessageBox.critical(
                self._parent,
                "Uninstall error",
                self._fatal_error,
            )

        pending = list(worker.uninstalled)
        if not pending:
            total = len(worker.programs)
            failed = len(worker.results)
            if total and failed:
                self.summary_changed.emit("No programs were uninstalled")
            self._finish("Uninstallation completed")
            return

        self._queue = pending
        self._budget_left = LEFTOVERS_TIMEOUT
        self.status_changed.emit("", "")
        self.progress_indeterminate.emit(True)
        self.summary_changed.emit("Checking for leftover files and registry entries…")
        QTimer.singleShot(NEXT_SCAN_DELAY, self._scan_next)

    def _scan_next(self) -> None:
        if self._closing:
            return
        if not self._queue:
            self._finish("Uninstallation completed")
            return
        if self._budget_left <= 0.5:
            self._abort_leftovers("Leftover search timed out")
            return

        program = self._queue[0]
        refresh_snapshot = self._leftover_snapshot is None
        snapshot = self._leftover_snapshot or self._snapshot_provider()
        self._scan_started = time.monotonic()
        self._scan_handled = False
        self.progress_indeterminate.emit(True)
        self.summary_changed.emit(
            f"Searching for leftovers: {program.name} "
            f"({int(self._budget_left)} s left)"
        )

        worker = LeftoversThread(
            program,
            snapshot,
            self._budget_left,
            refresh_snapshot=refresh_snapshot,
            parent=self._parent,
        )
        worker.done.connect(self._on_leftovers)
        worker.snapshot_ready.connect(self._on_leftover_snapshot_ready)
        worker.failed.connect(self._on_leftovers_failed)
        worker.completed.connect(self._on_leftovers_completed)
        worker.finished.connect(worker.deleteLater)
        self._leftover_worker = worker
        worker.start()

    def _on_leftover_snapshot_ready(self, snapshot: RegistrySnapshot) -> None:
        self._leftover_snapshot = snapshot

    def _consume_scan_time(self) -> None:
        elapsed = max(0.0, time.monotonic() - self._scan_started)
        self._budget_left = max(0.0, self._budget_left - elapsed)

    def _on_leftovers(self, result: Leftovers) -> None:
        if self._scan_handled:
            return
        self._scan_handled = True
        self._consume_scan_time()
        if self._queue:
            self._queue.pop(0)

        if result.has_items:
            self.summary_changed.emit("Leftover items found")
            self._show_leftovers(result)
        else:
            self.summary_changed.emit(f"No leftovers found for {result.program_name}")

        if result.timed_out or self._budget_left <= 0.5:
            self._abort_leftovers("Leftover search timed out")
            return
        QTimer.singleShot(NEXT_SCAN_DELAY, self._scan_next)

    def _on_leftovers_failed(self, message: str) -> None:
        if self._scan_handled:
            return
        self._scan_handled = True
        self._consume_scan_time()
        if self._queue:
            self._queue.pop(0)
        LOGGER.warning("Leftover scan failed: %s", message)
        self.summary_changed.emit("Leftover search failed")
        QTimer.singleShot(NEXT_SCAN_DELAY, self._scan_next)

    def _on_leftovers_completed(self) -> None:
        self._leftover_worker = None
        if self._scan_handled:
            return
        self._scan_handled = True
        self._consume_scan_time()
        if self._queue:
            self._queue.pop(0)
        LOGGER.warning("Leftover worker ended without a result")
        QTimer.singleShot(NEXT_SCAN_DELAY, self._scan_next)

    def _show_leftovers(self, result: Leftovers) -> None:
        dialog = LeftoversDialog(result, self._colors_provider(), self._parent)
        dialog.cleanup_requested.connect(
            lambda selection, current=dialog: self._start_cleanup(selection, current)
        )
        self._dialog = dialog
        dialog.exec()
        self._dialog = None

    def _start_cleanup(self, selection: Leftovers, dialog: LeftoversDialog) -> None:
        if self._cleanup_worker is not None:
            LOGGER.info("Ignored a duplicate cleanup request")
            dialog.set_busy(False)
            return
        if not selection.has_items:
            dialog.set_busy(False)
            return

        worker = CleanupThread(selection, self._parent)
        worker.done.connect(lambda result, target=dialog: target.finish_cleanup(result))
        worker.failed.connect(lambda message, target=dialog: target.fail_cleanup(message))
        worker.completed.connect(self._cleanup_completed)
        worker.finished.connect(worker.deleteLater)
        self._cleanup_worker = worker
        worker.start()

    def _cleanup_completed(self) -> None:
        self._cleanup_worker = None

    def _abort_leftovers(self, message: str) -> None:
        worker = self._leftover_worker
        if worker is not None:
            try:
                running = worker.isRunning()
            except RuntimeError:
                running = False
            if running:
                worker.requestInterruption()
        self._queue = []
        self._finish(message)

    def _finish(self, summary: str) -> None:
        self._active = False
        self._queue = []
        self.progress_indeterminate.emit(False)
        self.progress_visible.emit(False)
        self.summary_changed.emit(summary)
        self.busy_changed.emit(False)
        if self._reboot_required:
            names = "\n".join(self._reboot_required[:10])
            QMessageBox.information(
                self._parent,
                "Restart required",
                "These programs requested a restart to finish removal:\n\n"
                f"{names}\n\nPlease restart Windows when convenient.",
            )
            self._reboot_required = []
        self.finished.emit()

    def shutdown(self) -> bool:
        self._closing = True
        stopped = True
        for attr in ("_uninstall_worker", "_leftover_worker", "_cleanup_worker"):
            worker = getattr(self, attr)
            if worker is None:
                continue
            try:
                running = worker.isRunning()
            except RuntimeError:
                running = False
            if not running:
                continue
            worker.requestInterruption()
            if not worker.wait(5000):
                LOGGER.warning("Worker %s did not stop in time", attr)
                stopped = False
        if not stopped:
            self._closing = False
        return stopped
