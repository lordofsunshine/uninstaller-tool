from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.files import FileScan, scan_program_files
from app.models.program import Program
from app.utils import format_size
from app.workers.base import WorkerThread

PREVIEW_LIMIT = 5000


class PreviewScanThread(WorkerThread):
    scanned = Signal(object)

    def __init__(self, program: Program, parent=None):
        super().__init__(parent)
        self.program = program

    def work(self) -> None:
        result = scan_program_files(
            self.program,
            PREVIEW_LIMIT,
            self.isInterruptionRequested,
        )
        self.scanned.emit(result)


class FilePreviewDialog(QDialog):
    def __init__(self, program: Program, colors, parent=None):
        super().__init__(parent)
        self.program = program
        self.colors = colors
        self._scan: PreviewScanThread | None = None
        self._finished = False
        self.setWindowTitle(f"Folder preview — {program.name}")
        self.setMinimumSize(720, 520)
        self.resize(840, 640)
        self._setup()
        self._start_scan()

    def _setup(self) -> None:
        colors = self.colors
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Files in the program folder")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Preview only. The program's own uninstaller decides what is actually removed."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"font-size: 12px; color: {colors['text_secondary']};"
        )
        layout.addWidget(subtitle)

        self.file_list = QListWidget()
        self.file_list.setUniformItemSizes(True)
        self.file_list.setAccessibleName("Files in the program folder")

        self.loading = QLabel("Scanning the program folder…")
        self.loading.setStyleSheet(
            f"color: {colors['text_secondary']}; padding: 24px;"
        )
        self.loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading)
        layout.addWidget(self.file_list, 1)
        self.file_list.hide()

        info = QWidget()
        info.setStyleSheet(
            f"QWidget {{ background-color: {colors['surface']}; border-radius: 12px; }}"
        )
        info_box = QHBoxLayout(info)
        info_box.setContentsMargins(16, 10, 16, 10)
        self.count_label = QLabel("Files found: —")
        self.count_label.setStyleSheet(
            f"font-size: 13px; color: {colors['text_secondary']}; background: transparent;"
        )
        info_box.addWidget(self.count_label)
        info_box.addStretch()
        self.size_label = QLabel("Total size: —")
        self.size_label.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {colors['primary']}; background: transparent;"
        )
        info_box.addWidget(self.size_label)
        layout.addWidget(info)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_btn = QPushButton("Cancel scan")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.setMinimumWidth(120)
        self.cancel_btn.clicked.connect(self._cancel_scan)
        buttons.addWidget(self.cancel_btn)
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("secondaryButton")
        self.close_btn.setMinimumWidth(120)
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

    def _start_scan(self) -> None:
        self._scan = PreviewScanThread(self.program, self)
        self._scan.scanned.connect(self._show_results)
        self._scan.failed.connect(self._show_error)
        self._scan.completed.connect(self._scan_completed)
        self._scan.finished.connect(self._scan_finished)
        self._scan.finished.connect(self._scan.deleteLater)
        self._scan.start()

    def _scan_finished(self) -> None:
        self._scan = None

    def _cancel_scan(self) -> None:
        scan = self._scan
        if scan is None:
            return
        try:
            running = scan.isRunning()
        except RuntimeError:
            running = False
        if running:
            scan.requestInterruption()
            self.loading.setText("Stopping the scan…")
            self.cancel_btn.setEnabled(False)

    def _scan_completed(self) -> None:
        if self._finished:
            return
        self._finished = True
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)

    def _show_results(self, result: FileScan) -> None:
        self.loading.hide()
        if result.files:
            self.file_list.show()
            self.file_list.addItems(
                [
                    f"{path}   ·   {format_size(size)}"
                    for path, size in result.files
                ]
            )
            if result.truncated:
                self.file_list.addItem(
                    f"… showing the {PREVIEW_LIMIT} largest files of {result.total_count}"
                )
        else:
            self.loading.setText("No safe program folder was found to preview")
            self.loading.show()

        self.count_label.setText(f"Files found: {result.total_count}")
        self.size_label.setText(f"Total size: {format_size(result.total_size)}")
        if result.cancelled:
            self.loading.setText("Scan stopped early")
            self.loading.show()
        self._scan_completed()

    def _show_error(self, message: str) -> None:
        self._finished = True
        self.loading.setText(f"Could not scan the folder: {message}")
        self.loading.show()
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)

    def closeEvent(self, event) -> None:
        scan = self._scan
        if scan is not None:
            try:
                running = scan.isRunning()
            except RuntimeError:
                running = False
            if running:
                scan.requestInterruption()
                if not scan.wait(2000):
                    event.ignore()
                    return
        super().closeEvent(event)
