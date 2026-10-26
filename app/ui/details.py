from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.program import Program
from app.utils import format_install_date, format_size

FIELDS = ["Publisher", "Version", "Installed", "Size", "Location"]


class DetailPanel(QFrame):
    preview_requested = Signal()
    info_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detailPanel")
        self.setMinimumWidth(260)
        self.setMaximumWidth(520)
        self.program: Program | None = None
        self._setup()

    def _setup(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        self.placeholder = QLabel("Select a program\nto see its details")
        self.placeholder.setObjectName("detailPlaceholder")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.placeholder.setWordWrap(True)
        layout.addWidget(self.placeholder)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        self.name_label = QLabel()
        self.name_label.setObjectName("detailName")
        self.name_label.setWordWrap(True)
        content_layout.addWidget(self.name_label)

        self.values: dict[str, QLabel] = {}
        for field in FIELDS:
            row = QVBoxLayout()
            row.setSpacing(1)
            caption = QLabel(field.upper())
            caption.setObjectName("detailCaption")
            value = QLabel("—")
            value.setObjectName("detailValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            row.addWidget(caption)
            row.addWidget(value)
            content_layout.addLayout(row)
            self.values[field] = value

        content_layout.addStretch()

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.preview_button = QPushButton("Preview files")
        self.preview_button.setObjectName("secondaryButton")
        self.preview_button.setAccessibleName("Preview files in the program folder")
        self.info_button = QPushButton("More info")
        self.info_button.setObjectName("secondaryButton")
        self.info_button.setAccessibleName("Show full program information")
        buttons.addWidget(self.preview_button, 1)
        buttons.addWidget(self.info_button, 1)
        content_layout.addLayout(buttons)

        layout.addWidget(self.content)
        self.content.hide()

        self.preview_button.clicked.connect(self.preview_requested.emit)
        self.info_button.clicked.connect(self.info_requested.emit)

    def set_program(self, program: Program | None) -> None:
        self.program = program
        if program is None:
            self.placeholder.show()
            self.content.hide()
            return

        self.placeholder.hide()
        self.content.show()
        self.name_label.setText(program.name)
        self.setAccessibleName(f"Details for {program.name}")
        size_text = format_size(program.size_bytes) if program.size_bytes else ""
        data = {
            "Publisher": program.publisher or "—",
            "Version": program.version or "—",
            "Installed": format_install_date(program.install_date) or "—",
            "Size": size_text or "—",
            "Location": program.install_location or "—",
        }
        for field, value in data.items():
            self.values[field].setText(value)
