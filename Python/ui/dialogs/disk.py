from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.sizes import FolderSizeCache
from app.models.program import Program
from app.utils import format_size
from app.workers.sizes import SizesThread


class DiskSpaceDialog(QDialog):
    def __init__(self, programs: list[Program], colors, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.programs = list(programs)
        self._sizes: dict[str, int] = {
            program.key: program.size_bytes for program in self.programs
        }
        self._measured: set[str] = set()
        self._worker: SizesThread | None = None
        self._failed = False
        self.setWindowTitle("Disk Space Usage")
        self.setMinimumSize(640, 540)
        self.resize(760, 640)
        self._setup()
        self._start_measurement()

    def _setup(self) -> None:
        colors = self.colors
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Disk space usage analysis")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        total_bytes = sum(self._sizes.values())
        unknown = sum(1 for program in self.programs if program.size_bytes == 0)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        cards = [
            ("Total size", format_size(total_bytes) if total_bytes else "Unknown"),
            ("Programs", str(len(self.programs))),
        ]
        if unknown:
            cards.append(("No size info", str(unknown)))
        for caption, value in cards:
            card = QWidget()
            card.setStyleSheet(
                f"QWidget {{ background-color: {colors['surface']}; border-radius: 14px; }}"
            )
            box = QVBoxLayout(card)
            box.setContentsMargins(18, 14, 18, 14)
            box.setSpacing(2)
            value_label = QLabel(value)
            value_label.setStyleSheet(
                f"font-size: 22px; font-weight: 700; color: {colors['primary']}; background: transparent;"
            )
            caption_label = QLabel(caption)
            caption_label.setStyleSheet(
                f"font-size: 12px; color: {colors['text_secondary']}; background: transparent;"
            )
            box.addWidget(value_label)
            box.addWidget(caption_label)
            stats_row.addWidget(card, 1)
        layout.addLayout(stats_row)

        top_group = QGroupBox("Top 10 largest programs")
        self.top_list = QListWidget()
        self.top_list.setUniformItemSizes(True)
        self.top_list.setAccessibleName("Largest programs")
        top_box = QVBoxLayout(top_group)
        top_box.addWidget(self.top_list)
        self.measure_label = QLabel("Measuring folder sizes…")
        self.measure_label.setStyleSheet(
            f"font-size: 12px; color: {colors['text_secondary']}; background: transparent;"
        )
        top_box.addWidget(self.measure_label)
        layout.addWidget(top_group, 1)

        publisher_group = QGroupBox("Usage by publisher")
        self.publisher_list = QListWidget()
        self.publisher_list.setUniformItemSizes(True)
        self.publisher_list.setAccessibleName("Usage by publisher")
        publisher_box = QVBoxLayout(publisher_group)
        publisher_box.addWidget(self.publisher_list)
        layout.addWidget(publisher_group, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self._refresh_lists()

    def _refresh_lists(self) -> None:
        self.top_list.clear()
        ranked = sorted(
            (
                (program, self._sizes.get(program.key, 0))
                for program in self.programs
                if self._sizes.get(program.key, 0) > 0
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        for program, size in ranked[:10]:
            suffix = " (on disk)" if program.key in self._measured else ""
            self.top_list.addItem(
                QListWidgetItem(f"{program.name}   ·   {format_size(size)}{suffix}")
            )

        self.publisher_list.clear()
        by_publisher: dict[str, int] = {}
        for program in self.programs:
            publisher = program.publisher or "Unknown"
            by_publisher[publisher] = by_publisher.get(publisher, 0) + self._sizes.get(
                program.key, 0
            )
        for publisher, size in sorted(
            by_publisher.items(), key=lambda item: item[1], reverse=True
        )[:10]:
            if size > 0:
                self.publisher_list.addItem(
                    QListWidgetItem(f"{publisher}   ·   {format_size(size)}")
                )

    def _start_measurement(self) -> None:
        cache = FolderSizeCache()
        candidates = [
            program
            for program in self.programs
            if program.size_bytes == 0
            and program.install_location
            and not program.is_store_app
            and cache.get(program.install_location) is None
        ]
        if not candidates:
            self.measure_label.hide()
            return
        self._worker = SizesThread(candidates, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.measured.connect(self._on_measured)
        self._worker.failed.connect(self._on_failed)
        self._worker.completed.connect(self._on_completed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_worker_finished(self) -> None:
        self._worker = None

    def _on_progress(self, done: int, total: int, name: str) -> None:
        self.measure_label.setText(
            f"Measuring folder sizes… {done + 1} of {total}: {name}"
        )

    def _on_measured(self, sizes: dict[str, int]) -> None:
        for key, size in sizes.items():
            self._sizes[key] = max(0, int(size))
            self._measured.add(key)
        self._refresh_lists()

    def _on_failed(self, message: str) -> None:
        self._failed = True
        self.measure_label.setText(f"Could not measure folder sizes: {message}")

    def _on_completed(self) -> None:
        self._worker = None
        if self._failed:
            return
        if not self._measured:
            self.measure_label.setText("Folder sizes are already up to date")
        else:
            self.measure_label.setText("Folder sizes measured and cached")

    def closeEvent(self, event) -> None:
        worker = self._worker
        if worker is not None:
            try:
                running = worker.isRunning()
            except RuntimeError:
                running = False
            if running:
                worker.requestInterruption()
                if not worker.wait(2000):
                    event.ignore()
                    return
        super().closeEvent(event)
