from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QGroupBox, QWidget, QSizePolicy)

from app.core.files import find_program_files
from app.utils import format_size, format_install_date, program_icon


def _fmt_kb(size_kb):
    mb = size_kb / 1024
    return f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.1f} MB"


class DiskSpaceDialog(QDialog):
    def __init__(self, programs, colors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Disk Space Usage")
        self.setMinimumSize(640, 540)
        self.resize(760, 640)
        self._setup(programs, colors)

    def _setup(self, programs, colors):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Disk space usage analysis")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        total_kb = sum(float(p.get('size', 0) or 0) for p in programs)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        for caption, value in [("Total size", _fmt_kb(total_kb)), ("Programs", str(len(programs)))]:
            card = QWidget()
            card.setStyleSheet(f"QWidget {{ background-color: {colors['surface']}; border-radius: 14px; }}")
            box = QVBoxLayout(card)
            box.setContentsMargins(18, 14, 18, 14)
            box.setSpacing(2)
            value_label = QLabel(value)
            value_label.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {colors['primary']}; background: transparent;")
            caption_label = QLabel(caption)
            caption_label.setStyleSheet(f"font-size: 12px; color: {colors['text_secondary']}; background: transparent;")
            box.addWidget(value_label)
            box.addWidget(caption_label)
            stats_row.addWidget(card, 1)
        layout.addLayout(stats_row)

        top_group = QGroupBox("Top 10 largest programs")
        top_list = QListWidget()
        for p in sorted(programs, key=lambda x: float(x.get('size', 0) or 0), reverse=True)[:10]:
            kb = float(p.get('size', 0) or 0)
            if kb > 0:
                top_list.addItem(QListWidgetItem(f"{p['name']}   ·   {_fmt_kb(kb)}"))
        top_box = QVBoxLayout(top_group)
        top_box.addWidget(top_list)
        layout.addWidget(top_group, 1)

        pub_group = QGroupBox("Usage by publisher")
        pub_list = QListWidget()
        sizes = {}
        for p in programs:
            pub = p.get('publisher') or 'Unknown'
            sizes[pub] = sizes.get(pub, 0) + float(p.get('size', 0) or 0)
        for pub, kb in sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:10]:
            if kb > 0:
                pub_list.addItem(QListWidgetItem(f"{pub}   ·   {_fmt_kb(kb)}"))
        pub_box = QVBoxLayout(pub_group)
        pub_box.addWidget(pub_list)
        layout.addWidget(pub_group, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)


class _ScanThread(QThread):
    scanned = Signal(list, int)
    failed = Signal(str)

    def __init__(self, program, parent=None):
        super().__init__(parent)
        self.program = program

    def run(self):
        try:
            files, total = find_program_files(self.program, self.isInterruptionRequested)
            self.scanned.emit(files, total)
        except OSError as exc:
            self.failed.emit(str(exc))


class FilePreviewDialog(QDialog):
    def __init__(self, program, colors, parent=None):
        super().__init__(parent)
        self.program = program
        self.colors = colors
        self.setWindowTitle(f"Files Preview - {program['name']}")
        self.setMinimumSize(720, 520)
        self.resize(840, 640)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._setup()
        self.scan = _ScanThread(program, self)
        self.scan.scanned.connect(self._show_results)
        self.scan.failed.connect(self._show_error)
        self.scan.start()

    def _setup(self):
        colors = self.colors
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Files that will be removed:")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(self.program['name'])
        subtitle.setStyleSheet(f"font-size: 12px; color: {colors['text_secondary']};")
        layout.addWidget(subtitle)

        self.file_list = QListWidget()

        self.loading = QLabel("Scanning program files…")
        self.loading.setStyleSheet(f"color: {colors['text_secondary']}; padding: 24px;")
        self.loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading)
        layout.addWidget(self.file_list, 1)
        self.file_list.hide()

        info = QWidget()
        info.setStyleSheet(f"QWidget {{ background-color: {colors['surface']}; border-radius: 12px; }}")
        info_box = QHBoxLayout(info)
        info_box.setContentsMargins(16, 10, 16, 10)
        self.count_label = QLabel("Total files: —")
        self.count_label.setStyleSheet(f"font-size: 13px; color: {colors['text_secondary']}; background: transparent;")
        info_box.addWidget(self.count_label)
        info_box.addStretch()
        self.size_label = QLabel("Total size: —")
        self.size_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {colors['primary']}; background: transparent;")
        info_box.addWidget(self.size_label)
        layout.addWidget(info)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("secondaryButton")
        self.close_btn.setMinimumWidth(120)
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

    def _show_results(self, files, total_size):
        self.loading.hide()
        if files:
            self.file_list.show()
            for path, size in sorted(files, key=lambda i: i[1], reverse=True):
                self.file_list.addItem(QListWidgetItem(f"{path}   ·   {format_size(size)}"))
        else:
            self.loading.setText("No program files could be identified safely")
            self.loading.show()
        self.count_label.setText(f"Total files: {len(files)}")
        self.size_label.setText(f"Total size: {format_size(total_size)}")
        self.close_btn.setEnabled(True)

    def _show_error(self, message):
        self.loading.setText(f"Could not scan files: {message}")
        self.close_btn.setEnabled(True)

    def closeEvent(self, event):
        if self.scan.isRunning():
            self.scan.requestInterruption()
            if not self.scan.wait(2000):
                event.ignore()
                return
        super().closeEvent(event)


class InfoDialog(QDialog):
    # compact program info popup
    def __init__(self, program, colors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Program Information")
        self.setMinimumSize(560, 300)
        self.setMaximumSize(900, 700)
        self.resize(640, 10)
        self._setup(program, colors)

    def _setup(self, program, colors):
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
        title = QLabel(program['name'])
        title.setObjectName("sectionTitle")
        title.setStyleSheet("font-size: 19px;")
        head.addWidget(title, 1)
        layout.addLayout(head)

        card = QWidget()
        card.setStyleSheet(f"QWidget {{ background-color: {colors['surface_alt']}; border-radius: 14px; }}")
        # hug the content, don't stretch over the whole dialog
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        card_box = QVBoxLayout(card)
        card_box.setSpacing(10)
        card_box.setContentsMargins(18, 16, 18, 16)

        rows = [
            ("Publisher:", program.get('publisher', '')),
            ("Install Date:", format_install_date(program.get('install_date', ''))),
            ("Version:", program.get('version', '')),
            ("Location:", program.get('install_location', '')),
            ("Uninstall Command:", program.get('uninstall_string', '')),
        ]
        if program.get('size'):
            rows.append(("Size:", format_size(int(program['size']) * 1024)))

        for label, value in rows:
            row = QHBoxLayout()
            name = QLabel(label)
            name.setStyleSheet(f"color: {colors['text_secondary']}; font-weight: 600; min-width: 140px; background: transparent;")
            row.addWidget(name)
            val = QLabel(value or "Not available")
            val.setStyleSheet(f"color: {colors['text']}; background: transparent;")
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(val, 1)
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
