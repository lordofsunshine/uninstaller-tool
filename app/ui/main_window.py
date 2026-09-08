import re
import time

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QCheckBox, QProgressBar, QLabel, QMessageBox, QLineEdit,
                               QScrollArea, QMenu, QComboBox, QDialog, QApplication, QSplitter,
                               QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QAction

from app.config import APP_NAME, APP_VERSION, UNINSTALL_ICON
from app.theme.colors import system_palette, DARK
from app.theme.style import build_style
from app.utils import create_svg_icon, format_size, format_install_date, resource_path, set_dark_title_bar
from app.workers import LoaderThread, UninstallThread, LeftoversThread, CleanupThread
from app.core.processes import find_running_processes, kill_processes
from app.ui.program_item import ProgramItem
from app.ui.details import DetailPanel
from app.ui.dialogs import DiskSpaceDialog, FilePreviewDialog, InfoDialog


# whole leftover phase budget, then give up and refresh the list
LEFTOVERS_TIMEOUT = 40


class UninstallerTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.programs = []
        self.pending_leftovers = []
        self.selected_item = None
        self._closing = False
        self._leftovers_deadline = 0.0
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(resource_path("assets/app_icon.ico")))
        self.setMinimumSize(860, 560)
        self.resize(1040, 700)
        self.center()
        self.setup_ui()

    def center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - self.width()) // 2 + screen.x(),
                  (screen.height() - self.height()) // 2 + screen.y())

    def setup_ui(self):
        central = QWidget()
        central.setObjectName("centralHost")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(24, 16, 24, 16)

        # thin progress line on top, only visible when busy
        self.progress = QProgressBar()
        self.progress.setObjectName("topProgress")
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        header = QHBoxLayout()
        header_column = QVBoxLayout()
        header_column.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        header_column.addWidget(title)
        self.subtitle = QLabel("Loading installed programs…")
        self.subtitle.setObjectName("appSubtitle")
        header_column.addWidget(self.subtitle)
        header.addLayout(header_column)
        header.addStretch()
        badge = QLabel(f"v{APP_VERSION}")
        badge.setObjectName("versionBadge")
        header.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        # one toolbar row for everything
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.search = QLineEdit()
        self.search.setObjectName("searchField")
        self.search.setPlaceholderText("Search programs…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_programs)
        toolbar.addWidget(self.search, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.setObjectName("sortCombo")
        self.sort_combo.addItems(["Name", "Size", "Install Date", "Publisher"])
        self.sort_combo.setMinimumWidth(160)
        self.sort_combo.currentTextChanged.connect(self.sort_programs)
        toolbar.addWidget(self.sort_combo)

        disk_btn = QPushButton("Disk usage")
        disk_btn.setObjectName("secondaryButton")
        disk_btn.clicked.connect(self.show_disk_space)
        self.disk_btn = disk_btn
        toolbar.addWidget(disk_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.clicked.connect(self.refresh_programs)
        toolbar.addWidget(self.refresh_btn)
        root.addLayout(toolbar)

        # master-detail: list on left, details card on right
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setMinimumWidth(400)
        list_host = QWidget()
        self.list_layout = QVBoxLayout(list_host)
        self.list_layout.setSpacing(8)
        self.list_layout.setContentsMargins(0, 2, 4, 0)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(list_host)

        self.details = DetailPanel()
        self.details.preview_requested.connect(self.show_file_preview)
        self.details.info_requested.connect(self.show_selected_info)

        # splitter: drag to give more room to either the list or the details
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(10)
        self.splitter.addWidget(self.scroll)
        self.splitter.addWidget(self.details)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([720, 300])
        root.addWidget(self.splitter, 1)

        # bottom bar: what is selected + main action
        footer = QHBoxLayout()
        footer.setSpacing(12)
        self.summary = QLabel("No programs selected")
        self.summary.setObjectName("summaryText")
        footer.addWidget(self.summary, 1, Qt.AlignmentFlag.AlignVCenter)

        self.silent = QCheckBox("Silent mode")
        footer.addWidget(self.silent, 0, Qt.AlignmentFlag.AlignVCenter)

        self.uninstall_btn = QPushButton("Uninstall selected")
        self.uninstall_btn.setObjectName("primaryButton")
        self.uninstall_btn.setIcon(QIcon(create_svg_icon(UNINSTALL_ICON)))
        self.uninstall_btn.setMinimumWidth(190)
        self.uninstall_btn.clicked.connect(self.uninstall_selected)
        footer.addWidget(self.uninstall_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(footer)

        self.apply_theme(system_palette())
        self.refresh_programs()

    def apply_theme(self, palette):
        self.colors = palette
        self.is_dark = palette == DARK
        self.setStyleSheet(build_style(palette))

    def on_system_theme_changed(self):
        self.apply_theme(system_palette())
        # window is already visible, repaint its title bar right away
        set_dark_title_bar(self, self.is_dark)

    def refresh_programs(self):
        # remember selection so refresh doesn't wipe it
        self._saved_checked = {p["name"] for p in self.checked_programs()}
        self._saved_selected = self.selected_item.program["name"] if self.selected_item else None
        self._saved_scroll = self.scroll.verticalScrollBar().value()
        self.clear_list()
        self.set_summary("Loading installed programs…")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.refresh_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)
        self.disk_btn.setEnabled(False)
        self.subtitle.setText("Reading the registry…")
        self.loader = LoaderThread(self)
        self.loader.loaded.connect(self.populate)
        self.loader.failed.connect(self.on_load_failed)
        self.loader.start()

    def populate(self, programs):
        self.programs = programs
        saved_checked = getattr(self, "_saved_checked", set())
        saved_selected = getattr(self, "_saved_selected", None)
        for program in programs:
            item = ProgramItem(program)
            item.clicked.connect(self.on_item_clicked)
            item.checkbox.toggled.connect(self.update_summary)
            item.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            item.customContextMenuRequested.connect(
                lambda pos, p=program, w=item: self.show_context_menu(pos, p, w))
            if program.get("name") in saved_checked:
                item.checkbox.setChecked(True)
            self.list_layout.addWidget(item)
            if saved_selected and program.get("name") == saved_selected:
                self.on_item_clicked(item)
        self.sort_programs()
        self.filter_programs()
        self.update_summary()
        if getattr(self, "_saved_scroll", None) is not None:
            self.scroll.verticalScrollBar().setValue(self._saved_scroll)
        self._saved_checked = set()
        self._saved_selected = None
        self.progress.setVisible(False)
        total_gb = sum(float(p.get('size', 0) or 0) for p in programs) / (1024 * 1024)
        size_text = f"{total_gb:.1f} GB installed" if total_gb >= 1 else "small footprint"
        self.subtitle.setText(f"{len(programs)} programs found   ·   {size_text}")
        self.refresh_btn.setEnabled(True)
        self.uninstall_btn.setEnabled(True)
        self.disk_btn.setEnabled(True)

    def on_load_failed(self, message):
        self.progress.setVisible(False)
        self.subtitle.setText("Could not load installed programs")
        self.set_summary("Registry error")
        self.refresh_btn.setEnabled(True)
        QMessageBox.critical(self, "Registry error", message)

    def clear_list(self):
        self.selected_item = None
        self.details.set_program(None)
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def on_item_clicked(self, item):
        if self.selected_item is item:
            return
        if self.selected_item:
            self.selected_item.set_selected(False)
        self.selected_item = item
        item.set_selected(True)
        self.details.set_program(item.program)

    def filter_programs(self):
        query = self.search.text().casefold()
        visible = 0
        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i).widget()
            if not isinstance(item, ProgramItem):
                continue
            # match name and publisher, not just the visible label
            haystack = f"{item.program.get('name', '')} {item.program.get('publisher', '')}".casefold()
            match = query in haystack
            item.setVisible(match)
            visible += int(match)
        if self.selected_item and not self.selected_item.isVisible():
            self.selected_item.set_selected(False)
            self.selected_item = None
            self.details.set_program(None)
        if self.programs:
            if query:
                self.subtitle.setText(f"{visible} of {len(self.programs)} programs shown")
            else:
                self.subtitle.setText(f"{len(self.programs)} programs found")

    def checked_programs(self):
        return [w.program for i in range(self.list_layout.count())
                if isinstance((w := self.list_layout.itemAt(i).widget()), ProgramItem) and w.checkbox.isChecked()]

    def update_summary(self):
        checked = self.checked_programs()
        if not checked:
            self.set_summary("No programs selected")
            return
        total_kb = sum(float(p.get('size', 0) or 0) for p in checked)
        if total_kb > 0:
            self.summary.setText(f"<b>{len(checked)}</b> selected   ·   ~{format_size(total_kb * 1024)} to be freed")
        else:
            # size unknown, show no guess at all
            self.summary.setText(f"<b>{len(checked)}</b> selected")

    def set_summary(self, text):
        self.summary.setText(text)

    @staticmethod
    def plain_text(html):
        return re.sub(r"<[^>]+>", "", html)

    def confirm_running(self, programs):
        # offer to kill processes that belong to the programs being removed
        ready = []
        for program in programs:
            procs = find_running_processes(program)
            if not procs:
                ready.append(program)
                continue
            listing = "\n".join(f"PID {p['pid']}  -  {p['name']}" for p in procs[:10])
            answer = QMessageBox.question(
                self, "Program is running",
                f"{program['name']} is currently running:\n\n{listing}\n\nTerminate it and continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes)
            if answer == QMessageBox.StandardButton.Cancel:
                return None
            if answer == QMessageBox.StandardButton.Yes:
                result = kill_processes(procs)
                # verify the processes are really gone, don't fail silently
                still_running = find_running_processes(program)
                if still_running:
                    details = "; ".join(result.get("errors", [])[:3])
                    QMessageBox.warning(
                        self, "Could not terminate",
                        f"{program['name']} is still running and will be skipped.\n{details}")
                    continue
                ready.append(program)
        return ready

    def start_uninstall(self, programs):
        self.progress.setVisible(True)
        self.progress.setRange(0, len(programs))
        self.progress.setValue(0)
        self.worker = UninstallThread(programs, self.silent.isChecked(), self)
        self.worker.progress.connect(self.on_uninstall_progress)
        self.worker.stats.connect(self.on_uninstall_stats)
        self.worker.completed.connect(self.on_uninstall_done)
        self.worker.failed.connect(self.show_error)
        self.worker.start()
        self.refresh_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)

    def on_uninstall_stats(self, text):
        if not text:
            return
        base = self.plain_text(self.summary.text())
        if "Elapsed:" in base:
            base = base.split("   |   ")[0]
        self.summary.setText(f"{base}   |   {text}")

    def uninstall_selected(self):
        programs = self.checked_programs()
        if not programs:
            QMessageBox.warning(self, "Warning", "No programs selected for uninstallation.")
            return
        answer = QMessageBox.question(
            self, "Confirmation",
            f"Are you sure you want to uninstall {len(programs)} selected programs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        ready = self.confirm_running(programs)
        if ready is None:
            return
        if not ready:
            self.set_summary("Nothing left to uninstall")
            return
        self.start_uninstall(ready)

    def on_uninstall_progress(self, value, status, status_type, name):
        self.progress.setValue(value)
        self.set_summary(status)
        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i).widget()
            if isinstance(item, ProgramItem) and item.program.get("name") == name:
                item.set_status(status_type)

    def on_uninstall_done(self):
        self.refresh_btn.setEnabled(True)
        self.uninstall_btn.setEnabled(True)
        self.set_summary("Uninstallation completed")
        reboot = list(getattr(self.worker, "reboot_required", []))
        if reboot:
            QMessageBox.information(
                self, "Restart required",
                "These programs requested a restart to finish removal:\n\n"
                + "\n".join(reboot[:10])
                + "\n\nPlease restart Windows when convenient.")
        self.pending_leftovers = list(self.worker.uninstalled)
        self._leftovers_deadline = time.monotonic() + LEFTOVERS_TIMEOUT
        if self.pending_leftovers:
            QTimer.singleShot(2000, self.check_next_leftovers)
        else:
            self.set_summary("No programs were uninstalled")
            QTimer.singleShot(2000, self.refresh_programs)

    def _abort_leftovers(self, message):
        # stop current scan if any, drop the queue, act as if done
        worker = getattr(self, 'leftovers_worker', None)
        if worker is not None and worker.isRunning():
            worker.requestInterruption()
        self.pending_leftovers = []
        self.set_summary(message)
        self.progress.setVisible(False)
        self.refresh_programs()

    def check_next_leftovers(self):
        if self._closing or not self.pending_leftovers:
            return
        if time.monotonic() >= self._leftovers_deadline:
            self._abort_leftovers("Leftover search timed out")
            return
        worker = getattr(self, 'leftovers_worker', None)
        if worker is not None and worker.isRunning():
            # previous scan still running, retry a bit later
            QTimer.singleShot(1000, self.check_next_leftovers)
            return
        self.leftovers_worker = LeftoversThread(self.pending_leftovers[0], self)
        self.leftovers_worker.finished.connect(self.leftovers_worker.deleteLater)
        self.leftovers_worker.done.connect(self.on_leftovers_found)
        self.leftovers_worker.start()
        remaining = max(0, int(self._leftovers_deadline - time.monotonic()))
        self.set_summary(f"Searching for leftover files and registry entries… ({remaining}s left)")

    def on_leftovers_found(self, leftovers):
        if self._closing or not self.pending_leftovers:
            return
        if time.monotonic() >= self._leftovers_deadline:
            self._abort_leftovers("Leftover search timed out")
            return
        if leftovers['files'] or leftovers['registry']:
            self.set_summary("Leftover files found")
            self.show_cleanup_dialog(leftovers)
        else:
            self.set_summary("No leftover files found")
            QMessageBox.information(self, "Leftover Search", "No leftover files or registry entries found.")
        self.pending_leftovers.pop(0)
        if self.pending_leftovers:
            QTimer.singleShot(1000, self.check_next_leftovers)
        else:
            QTimer.singleShot(2000, self.refresh_programs)

    def show_cleanup_dialog(self, leftovers):
        dialog = QDialog(self)
        dialog.setWindowTitle("Leftover Files and Entries")
        dialog.setMinimumSize(640, 540)
        dialog.resize(760, 640)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Found leftover items:")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        def make_list(items):
            box = QListWidget()
            box.setMinimumHeight(140)
            for entry in items:
                item = QListWidgetItem(entry)
                # let the user uncheck items they want to keep
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                box.addItem(item)
            return box

        files_box = make_list(leftovers['files']) if leftovers['files'] else None
        reg_box = make_list(leftovers['registry']) if leftovers['registry'] else None

        if files_box is not None:
            label = QLabel(f"Files ({len(leftovers['files'])} items)")
            label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.colors['primary']}; background: transparent;")
            layout.addWidget(label)
            layout.addWidget(files_box)

        if reg_box is not None:
            label = QLabel(f"Registry entries ({len(leftovers['registry'])} items)")
            label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.colors['primary']}; background: transparent;")
            layout.addWidget(label)
            layout.addWidget(reg_box)

        hint = QLabel("Uncheck items you want to keep.")
        hint.setStyleSheet(f"font-size: 12px; color: {self.colors['text_secondary']}; background: transparent;")
        layout.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        remove_btn = QPushButton("Remove selected")
        remove_btn.setObjectName("primaryButton")
        buttons.addWidget(cancel_btn)
        buttons.addWidget(remove_btn)
        layout.addLayout(buttons)

        def checked_entries(box):
            if box is None:
                return []
            out = []
            for i in range(box.count()):
                item = box.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    out.append(item.text())
            return out

        def start_cleanup():
            selected = {
                "files": checked_entries(files_box),
                "registry": checked_entries(reg_box),
            }
            if not selected["files"] and not selected["registry"]:
                dialog.reject()
                return
            remove_btn.setEnabled(False)
            cancel_btn.setEnabled(False)
            title.setText("Removing leftover items…")
            if hasattr(self, 'cleanup_worker') and self.cleanup_worker.isRunning():
                self.cleanup_worker.wait(500)
            self.cleanup_worker = CleanupThread(selected, self)
            self.cleanup_worker.finished.connect(self.cleanup_worker.deleteLater)
            self.cleanup_worker.done.connect(lambda result: self.on_cleanup_done(result, dialog))
            self.cleanup_worker.failed.connect(lambda msg: self.on_cleanup_failed(msg, dialog))
            self.cleanup_worker.start()

        remove_btn.clicked.connect(start_cleanup)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def on_cleanup_done(self, result, dialog):
        summary = f"Removed locations: {result['removed_files']}\nRegistry entries: {result['removed_registry']}"
        if result['scheduled_files']:
            summary += (f"\nLocked items scheduled after restart: {result['scheduled_files']}"
                        "\nPlease restart Windows to finish removal.")
        self.set_summary("Cleanup completed")
        self.progress.setVisible(False)
        dialog.accept()
        if result['errors']:
            details = "\n".join(result['errors'][:5])
            if len(result['errors']) > 5:
                details += f"\n... and {len(result['errors']) - 5} more"
            QMessageBox.warning(self, "Cleanup completed with errors", f"{summary}\n\n{details}")
        else:
            QMessageBox.information(self, "Cleanup completed", summary)

    def on_cleanup_failed(self, message, dialog):
        dialog.reject()
        QMessageBox.critical(self, "Cleanup failed", f"Could not complete cleanup:\n{message}")

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_context_menu(self, pos, program, widget):
        menu = QMenu(self)
        info_action = QAction("Program Information", self)
        info_action.triggered.connect(lambda: InfoDialog(program, self.colors, self).exec())
        menu.addAction(info_action)
        menu.addSeparator()
        uninstall_action = QAction("Uninstall", self)
        uninstall_action.triggered.connect(lambda: self.uninstall_one(program))
        menu.addAction(uninstall_action)
        menu.exec(widget.mapToGlobal(pos))

    def show_selected_info(self):
        if self.selected_item:
            InfoDialog(self.selected_item.program, self.colors, self).exec()

    def uninstall_one(self, program):
        answer = QMessageBox.question(
            self, "Confirmation",
            f"Are you sure you want to uninstall {program['name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        ready = self.confirm_running([program])
        if not ready:
            return
        self.start_uninstall(ready)

    def sort_programs(self):
        mode = self.sort_combo.currentText()
        items = [w for i in range(self.list_layout.count())
                 if isinstance((w := self.list_layout.itemAt(i).widget()), ProgramItem)]

        if mode == "Name":
            items.sort(key=lambda x: x.program['name'].casefold())
        elif mode == "Size":
            items.sort(key=lambda x: float(x.program.get('size', 0) or 0), reverse=True)
        elif mode == "Install Date":
            items.sort(key=lambda x: x.program.get('install_date', ''), reverse=True)
        elif mode == "Publisher":
            items.sort(key=lambda x: (x.program.get('publisher', '') or '').casefold())

        while self.list_layout.count():
            self.list_layout.takeAt(0)
        for item in items:
            self.list_layout.addWidget(item)
        # keep current search filter after reordering
        self.filter_programs()

    def closeEvent(self, event):
        self._closing = True
        for attr in ('loader', 'worker', 'leftovers_worker', 'cleanup_worker'):
            w = getattr(self, attr, None)
            if w is not None and w.isRunning():
                w.requestInterruption()
                w.wait(800)
        event.accept()

    def show_disk_space(self):
        DiskSpaceDialog(self.programs, self.colors, self).exec()

    def show_file_preview(self):
        program = self.details.program
        if program is None:
            checked = self.checked_programs()
            if not checked:
                QMessageBox.warning(self, "Warning", "Select a program first")
                return
            program = checked[0]
        FilePreviewDialog(program, self.colors, self).exec()
