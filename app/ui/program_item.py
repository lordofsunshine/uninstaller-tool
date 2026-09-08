from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QCheckBox, QLabel


class ProgramItem(QFrame):
    # emitted with self when user clicks the card anywhere
    clicked = Signal(object)

    def __init__(self, program, parent=None):
        super().__init__(parent)
        self.program = program
        self.setObjectName("programCard")
        self.setProperty("isSelected", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup()

    def _setup(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        self.checkbox = QCheckBox()
        self.checkbox.setCursor(Qt.CursorShape.ArrowCursor)

        text = QVBoxLayout()
        text.setSpacing(3)

        self.name_label = QLabel(self.program.get('name', ''))
        self.name_label.setObjectName("programName")
        text.addWidget(self.name_label)

        self.meta_label = QLabel(self._meta_text())
        self.meta_label.setObjectName("programMeta")
        text.addWidget(self.meta_label)

        self.status_label = QLabel()
        self.status_label.setObjectName("statusPill")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFixedWidth(100)
        self.status_label.hide()

        layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(text, 1)
        layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setMinimumHeight(64)

    def _meta_text(self):
        parts = []
        if self.program.get('store_app'):
            parts.append("Store")
        if self.program.get('publisher'):
            parts.append(self.program['publisher'])
        if self.program.get('version'):
            parts.append(f"v{self.program['version']}")
        size_kb = float(self.program.get('size', 0) or 0)
        if size_kb > 0:
            mb = size_kb / 1024
            parts.append(f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.1f} MB")
        return "   ·   ".join(parts) or "No details available"

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)

    def set_selected(self, on):
        self.setProperty("isSelected", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_status(self, status):
        texts = {"running": "Removing…", "success": "Removed", "error": "Failed"}
        if status in texts:
            self.status_label.setText(texts[status])
            self.status_label.setProperty("statusVariant", status)
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            self.status_label.show()
        else:
            self.status_label.hide()
