from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget

from app.utils import format_install_date, format_size

FIELDS = ["Publisher", "Version", "Installed", "Size", "Location"]


class DetailPanel(QFrame):
    # right-side card, shows info about the program user clicked
    preview_requested = Signal()
    info_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detailPanel")
        self.setMinimumWidth(260)
        self.setMaximumWidth(520)
        self.program = None
        self._setup()

    def _setup(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        self.placeholder = QLabel("Select a program\nto see its details")
        self.placeholder.setObjectName("detailPlaceholder")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.placeholder)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        self.name_label = QLabel()
        self.name_label.setObjectName("detailName")
        self.name_label.setWordWrap(True)
        content_layout.addWidget(self.name_label)

        self.values = {}
        for field in FIELDS:
            row = QVBoxLayout()
            row.setSpacing(1)
            caption = QLabel(field.upper())
            caption.setObjectName("detailCaption")
            value = QLabel("—")
            value.setObjectName("detailValue")
            value.setWordWrap(True)
            if field == "Location":
                value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(caption)
            row.addWidget(value)
            content_layout.addLayout(row)
            self.values[field] = value

        content_layout.addStretch()

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        preview_btn = QPushButton("Preview files")
        preview_btn.setObjectName("secondaryButton")
        info_btn = QPushButton("More info")
        info_btn.setObjectName("secondaryButton")
        buttons.addWidget(preview_btn, 1)
        buttons.addWidget(info_btn, 1)
        content_layout.addLayout(buttons)

        layout.addWidget(self.content)
        self.content.hide()

        preview_btn.clicked.connect(self.preview_requested.emit)
        info_btn.clicked.connect(self.info_requested.emit)

    def set_program(self, program):
        self.program = program
        if program is None:
            self.placeholder.show()
            self.content.hide()
            return
        self.placeholder.hide()
        self.content.show()
        self.name_label.setText(program.get('name', ''))
        size_kb = float(program.get('size', 0) or 0)
        data = {
            "Publisher": program.get('publisher') or "—",
            "Version": program.get('version') or "—",
            "Installed": format_install_date(program.get('install_date', '')) or "—",
            "Size": format_size(size_kb * 1024) if size_kb else "—",
            "Location": program.get('install_location') or "—",
        }
        for field, value in data.items():
            self.values[field].setText(value)
