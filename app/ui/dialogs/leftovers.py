from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.models.program import Leftovers, RegistryEntry, RemovalResult


class LeftoversDialog(QDialog):
    cleanup_requested = Signal(object)

    def __init__(self, leftovers: Leftovers, colors, parent=None):
        super().__init__(parent)
        self.leftovers = leftovers
        self.colors = colors
        self._busy = False
        self._file_items: list[QListWidgetItem] = []
        self._registry_items: list[QListWidgetItem] = []
        self.setWindowTitle("Leftover Files and Entries")
        self.setMinimumSize(640, 420)
        self.resize(760, 560)
        self._setup()
        self.resize(760, min(780, max(440, self.sizeHint().height())))

    def _setup(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("Found leftover items:")
        self.title.setObjectName("sectionTitle")
        layout.addWidget(self.title)

        self.files_box = self._make_list(self.leftovers.files, self._file_items)
        if self.files_box is not None:
            layout.addWidget(
                self._label(f"Files ({self._items(len(self.leftovers.files))})")
            )
            layout.addWidget(self.files_box)

        self.registry_box = self._make_list(
            [entry.path for entry in self.leftovers.registry],
            self._registry_items,
        )
        if self.registry_box is not None:
            layout.addWidget(
                self._label(
                    f"Registry entries ({self._items(len(self.leftovers.registry))})"
                )
            )
            layout.addWidget(self.registry_box)

        hint = QLabel(
            "Uncheck items you want to keep. Registry keys are backed up as .reg files before removal."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"font-size: 12px; color: {self.colors['text_secondary']}; background: transparent;"
        )
        layout.addWidget(hint)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.clicked.connect(self.reject)
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.setObjectName("primaryButton")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self._start_cleanup)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.remove_button)
        layout.addLayout(buttons)

        for item in (*self._file_items, *self._registry_items):
            item.setCheckState(Qt.CheckState.Checked)
        self.remove_button.setEnabled(True)

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {self.colors['primary']}; background: transparent;"
        )
        return label

    @staticmethod
    def _items(count: int) -> str:
        return f"{count} item" if count == 1 else f"{count} items"

    def _make_list(
        self,
        items: list[str],
        target: list[QListWidgetItem],
    ) -> QListWidget | None:
        if not items:
            return None
        box = QListWidget()
        box.setUniformItemSizes(False)
        for text in items:
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setToolTip(text)
            box.addItem(item)
            target.append(item)
        row_height = box.sizeHintForRow(0) if items else 20
        box.setFixedHeight(min(220, max(84, len(items) * (row_height + 20) + 10)))
        box.itemChanged.connect(self._update_button)
        return box

    def _update_button(self) -> None:
        self.remove_button.setEnabled(not self._busy and bool(self._selected_items()))

    def _selected_items(self) -> tuple[list[str], list[RegistryEntry]]:
        files = [
            item.text()
            for item in self._file_items
            if item.checkState() == Qt.CheckState.Checked
        ]
        registry = [
            entry
            for entry, item in zip(self.leftovers.registry, self._registry_items)
            if item.checkState() == Qt.CheckState.Checked
        ]
        return files, registry

    def _start_cleanup(self) -> None:
        if self._busy:
            return
        files, registry = self._selected_items()
        if not files and not registry:
            self.reject()
            return
        selection = Leftovers(
            program_key=self.leftovers.program_key,
            program_name=self.leftovers.program_name,
            files=files,
            registry=registry,
        )
        self.set_busy(True)
        self.cleanup_requested.emit(selection)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self.title.setText("Removing leftover items…")
            self.remove_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            if self.files_box is not None:
                self.files_box.setEnabled(False)
            if self.registry_box is not None:
                self.registry_box.setEnabled(False)
        else:
            self.title.setText("Found leftover items:")
            self.remove_button.setEnabled(bool(self._selected_items()))
            self.cancel_button.setEnabled(True)
            if self.files_box is not None:
                self.files_box.setEnabled(True)
            if self.registry_box is not None:
                self.registry_box.setEnabled(True)

    def finish_cleanup(self, result: RemovalResult) -> None:
        summary = (
            f"Removed locations: {result.removed_files}\n"
            f"Registry entries: {result.removed_registry}"
        )
        if result.scheduled_files:
            summary += (
                f"\nLocked items scheduled after restart: {result.scheduled_files}"
                "\nPlease restart Windows to finish removal."
            )
        if result.backups:
            folder = os.path.dirname(result.backups[0])
            summary += f"\nRegistry backups: {len(result.backups)} file(s) in {folder}"
        if result.errors:
            details = "\n".join(result.errors[:5])
            if len(result.errors) > 5:
                details += f"\n… and {len(result.errors) - 5} more"
            QMessageBox.warning(
                self,
                "Cleanup completed with errors",
                f"{summary}\n\n{details}",
            )
        else:
            QMessageBox.information(self, "Cleanup completed", summary)
        self.accept()

    def fail_cleanup(self, message: str) -> None:
        self.set_busy(False)
        QMessageBox.critical(
            self,
            "Cleanup failed",
            f"Could not complete cleanup:\n{message}",
        )

    def closeEvent(self, event) -> None:
        if self._busy:
            event.ignore()
            return
        super().closeEvent(event)
