from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.program import Program
from app.utils import format_install_date, format_size, program_icon


class InfoDialog(QDialog):
    def __init__(self, program: Program, colors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Program Information")
        self.setMinimumSize(640, 300)
        self.setMaximumSize(900, 700)
        self.resize(640, 10)
        self._fields: list[QTextEdit] = []
        self._fitting = False
        self._setup(program, colors)
        QTimer.singleShot(0, self._fit_fields)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_fields()

    def _fit_fields(self, depth: int = 0) -> None:
        if not self.isVisible() or self._fitting or depth > 2:
            return
        self._fitting = True
        try:
            for edit in self._fields:
                needed = math.ceil(edit.document().size().height()) + 2
                line = edit.fontMetrics().lineSpacing() + 4
                edit.setFixedHeight(max(line, needed))
            self.layout().activate()
            self.resize(self.width(), self.layout().totalMinimumSize().height())
        finally:
            self._fitting = False
        if depth < 2:
            QTimer.singleShot(40, lambda: self._fit_fields(depth + 1))

    def _value_field(self, text: str, colors) -> QTextEdit:
        edit = QTextEdit()
        edit.setReadOnly(True)
        edit.setFrameStyle(QFrame.Shape.NoFrame)
        edit.viewport().setAutoFillBackground(False)
        edit.setStyleSheet(
            f"color: {colors['text']}; background: transparent; border: none;"
        )
        edit.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
        edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        edit.document().setDocumentMargin(0)
        edit.setPlainText(text or "Not available")
        edit.setAccessibleName("Value")
        self._fields.append(edit)
        return edit

    def _setup(self, program: Program, colors) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 24, 28, 24)

        head = QHBoxLayout()
        head.setSpacing(12)
        icon = program_icon(program)
        if icon is not None:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(32, 32))
            icon_label.setFixedSize(32, 32)
            head.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        title = QLabel(program.name)
        title.setObjectName("sectionTitle")
        title.setStyleSheet("font-size: 19px;")
        title.setWordWrap(True)
        head.addWidget(title, 1)
        layout.addLayout(head)

        card = QWidget()
        card.setStyleSheet(
            f"QWidget {{ background-color: {colors['surface_alt']}; border-radius: 14px; }}"
        )
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        card_box = QVBoxLayout(card)
        card_box.setSpacing(10)
        card_box.setContentsMargins(18, 16, 18, 16)

        rows = [
            ("Publisher:", program.publisher),
            ("Install Date:", format_install_date(program.install_date)),
            ("Version:", program.version),
            ("Location:", program.install_location),
            ("Uninstall Command:", program.uninstall_string),
        ]
        if program.size_bytes:
            rows.append(("Size:", format_size(program.size_bytes)))
        if program.is_store_app:
            rows.append(("Store package:", program.package_full_name))

        for label, value in rows:
            row = QHBoxLayout()
            name = QLabel(label)
            name.setStyleSheet(
                f"color: {colors['text_secondary']}; font-weight: 600; "
                "min-width: 140px; background: transparent;"
            )
            row.addWidget(name)
            row.addWidget(self._value_field(value, colors), 1)
            card_box.addLayout(row)

        layout.addWidget(card)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.addStretch()
        done = QPushButton("Done")
        done.setObjectName("primaryButton")
        done.setMinimumSize(110, 38)
        done.clicked.connect(self.accept)
        buttons.addWidget(done)
        layout.addLayout(buttons)
