from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QGroupBox, QWidget, QSizePolicy,
                               QFrame, QTextEdit)

from app.core.files import find_program_files
from app.utils import format_size, format_install_date, program_icon


def _fmt_kb(size_kb):
    try:
        size_kb = float(size_kb or 0)
    except (TypeError, ValueError):
        size_kb = 0
    if size_kb <= 0:
        return ""
    mb = size_kb / 1024
    return f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.1f} MB"


class DiskSpaceDialog(QDialog):
    def __init__(self, programs, colors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Disk Space Usage")
        self.setMinimumSize(640, 540)
        self.resize(760, 640)
        self._measure = None
        self._setup(programs, colors)

    def _setup(self, programs, colors):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Disk space usage analysis")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        total_kb = sum(float(p.get('size', 0) or 0) for p in programs)
        unknown = sum(1 for p in programs if not float(p.get('size', 0) or 0))
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        cards = [("Total size", _fmt_kb(total_kb)), ("Programs", str(len(programs)))]
        if unknown:
            cards.append(("No size info", str(unknown)))
        for caption, value in cards:
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
        self.top_list = QListWidget()
        self.top_list.setUniformItemSizes(True)
        sized = [p for p in sorted(programs, key=lambda x: float(x.get('size', 0) or 0), reverse=True) if float(p.get('size', 0) or 0) > 0][:10]
        for p in sized:
            kb = float(p.get('size', 0) or 0)
            self.top_list.addItem(QListWidgetItem(f"{p['name']}   ·   {_fmt_kb(kb)}"))
        top_box = QVBoxLayout(top_group)
        top_box.addWidget(self.top_list)
        self.measure_label = QLabel("Measuring real folder sizes…")
        self.measure_label.setStyleSheet(f"font-size: 12px; color: {colors['text_secondary']}; background: transparent;")
        top_box.addWidget(self.measure_label)
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

        # registry sizes are often missing, measure real folders in background
        candidates = [p for p in programs if not float(p.get('size', 0) or 0) and p.get('install_location')][:15]
        if candidates:
            self._measure = _MeasureThread(candidates, self)
            self._measure.measured.connect(self._show_measured)
            self._measure.start()
        else:
            self.measure_label.hide()

    def _show_measured(self, rows):
        # rows: list of (name, bytes)
        rows = [(n, b) for n, b in rows if b > 0]
        if not rows:
            self.measure_label.setText("Could not measure real sizes")
            return
        rows.sort(key=lambda r: r[1], reverse=True)
        self.measure_label.setText("Real folder sizes (measured):")
        for name, size in rows[:10]:
            self.top_list.addItem(QListWidgetItem(f"{name}   ·   {format_size(size)} (on disk)"))

    def closeEvent(self, event):
        if self._measure is not None and self._measure.isRunning():
            self._measure.requestInterruption()
            self._measure.wait(1000)
        super().closeEvent(event)


class _MeasureThread(QThread):
    measured = Signal(list)

    def __init__(self, programs, parent=None):
        super().__init__(parent)
        self.programs = list(programs)

    def run(self):
        from app.core.files import measure_dir_size
        out = []
        for program in self.programs:
            if self.isInterruptionRequested():
                break
            try:
                size = measure_dir_size(program.get("install_location", ""), self.isInterruptionRequested)
            except OSError:
                size = 0
            if size > 0:
                out.append((program.get("name", "?"), size))
        self.measured.emit(out)


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
    PREVIEW_LIMIT = 5000

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
        self.file_list.setUniformItemSizes(True)

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

    def _cancel_scan(self):
        # stop background walk, keep dialog usable
        if self.scan.isRunning():
            self.scan.requestInterruption()
            self.loading.setText("Cancelling scan…")
            self.cancel_btn.setEnabled(False)

    def _show_results(self, files, total_size):
        self.loading.hide()
        self.cancel_btn.setEnabled(False)
        if files:
            self.file_list.show()
            ranked = sorted(files, key=lambda i: i[1], reverse=True)
            shown = ranked[:self.PREVIEW_LIMIT]
            # batch insert, much faster than one-by-one for big folders
            self.file_list.addItems([f"{path}   ·   {format_size(size)}" for path, size in shown])
            if len(ranked) > self.PREVIEW_LIMIT:
                self.file_list.addItem(f"… and {len(ranked) - self.PREVIEW_LIMIT} more files (showing largest {self.PREVIEW_LIMIT})")
        else:
            self.loading.setText("No program files could be identified safely")
            self.loading.show()
        self.count_label.setText(f"Total files: {len(files)}")
        self.size_label.setText(f"Total size: {format_size(total_size)}")
        self.close_btn.setEnabled(True)

    def _show_error(self, message):
        self.loading.setText(f"Could not scan files: {message}")
        self.close_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

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
        self.setMinimumSize(640, 300)
        self.setMaximumSize(900, 700)
        self.resize(640, 10)
        self._fields = []
        self._setup(program, colors)
        QTimer.singleShot(0, self._fit_fields)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_fields()

    def _fit_fields(self, depth=0):
        if not self.isVisible() or getattr(self, "_fitting", False) or depth > 2:
            return
        self._fitting = True
        try:
            import math
            for edit in getattr(self, "_fields", []):
                need = math.ceil(edit.document().size().height()) + 2
                line = edit.fontMetrics().lineSpacing() + 4
                edit.setFixedHeight(max(line, need))
            self.layout().activate()
            self.resize(self.width(), self.layout().totalMinimumSize().height())
        finally:
            self._fitting = False
        if depth < 2:
            QTimer.singleShot(40, lambda: self._fit_fields(depth + 1))

    def _value_field(self, text, colors):
        edit = QTextEdit()
        edit.setReadOnly(True)
        edit.setFrameStyle(QFrame.Shape.NoFrame)
        edit.viewport().setAutoFillBackground(False)
        edit.setStyleSheet(f"color: {colors['text']}; background: transparent; border: none;")
        edit.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
        edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        edit.document().setDocumentMargin(0)
        edit.setPlainText(text or "Not available")
        self._fields.append(edit)
        return edit

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
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
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
