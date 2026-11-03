from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, APP_VERSION, UNINSTALL_ICON
from app.models.program import Program, ProgramStatus
from app.settings import AppSettings
from app.theme.colors import DARK, system_palette
from app.theme.style import build_style
from app.ui.details import DetailPanel
from app.ui.program_model import (
    ProgramDelegate,
    ProgramFilterProxy,
    ProgramListView,
    ProgramModel,
)
from app.utils import create_svg_icon, format_size, resource_path, set_dark_title_bar
from app.workers.loader import LoaderThread

SEARCH_DELAY_MS = 160
REFRESH_DELAY_MS = 1600


class UninstallerTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.colors = system_palette()
        self.is_dark = self.colors == DARK
        self.programs: list[Program] = []
        self._registry_programs: list[Program] = []
        self._store_programs: list[Program] = []
        self._loader: LoaderThread | None = None
        self._controller = None
        self._selected_key = ""
        self._saved_checked: set[str] = set()
        self._saved_selected = ""
        self._saved_scroll = 0
        self._loading = False
        self._busy = False
        self._closing = False
        self._store_loading = False
        self._refresh_pending = False
        self._base_summary = ""
        self._progress_total = 1
        self._load_failed = False

        self._settings = AppSettings()
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(SEARCH_DELAY_MS)
        self._search_timer.timeout.connect(self._apply_filter)

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(resource_path("assets/app_icon.ico")))
        self.setMinimumSize(860, 560)
        self.resize(1040, 700)
        self.center()

        self.setup_ui()
        self.apply_theme(self.colors)
        self._restore_settings()
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        QTimer.singleShot(0, self.refresh_programs)

    def center(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        frame = screen.availableGeometry()
        self.move(
            frame.x() + (frame.width() - self.width()) // 2,
            frame.y() + (frame.height() - self.height()) // 2,
        )

    def setup_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralHost")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(24, 16, 24, 16)

        self.progress = QProgressBar()
        self.progress.setObjectName("topProgress")
        self.progress.setVisible(False)
        self.progress.setAccessibleName("Progress")
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

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.search = QLineEdit()
        self.search.setObjectName("searchField")
        self.search.setPlaceholderText("Search programs…")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Search installed programs")
        self.search.textChanged.connect(lambda _: self._search_timer.start())
        toolbar.addWidget(self.search, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.setObjectName("sortCombo")
        self.sort_combo.addItems(["Name", "Size", "Install Date", "Publisher"])
        self.sort_combo.setMinimumWidth(160)
        self.sort_combo.setAccessibleName("Sort programs")
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        toolbar.addWidget(self.sort_combo)

        self.disk_btn = QPushButton("Disk usage")
        self.disk_btn.setObjectName("secondaryButton")
        self.disk_btn.setAccessibleName("Open disk usage analysis")
        self.disk_btn.clicked.connect(self.show_disk_space)
        toolbar.addWidget(self.disk_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.setAccessibleName("Refresh the program list")
        self.refresh_btn.clicked.connect(self.refresh_programs)
        toolbar.addWidget(self.refresh_btn)
        root.addLayout(toolbar)

        self.program_model = ProgramModel(self)
        self.program_proxy = ProgramFilterProxy(self)
        self.program_proxy.setSourceModel(self.program_model)
        self.program_proxy.set_sort_mode(0)

        self.view = ProgramListView()
        self.view.setModel(self.program_proxy)
        self.delegate = ProgramDelegate(self.colors, self.view)
        self.view.setItemDelegate(self.delegate)
        self.view.selectionModel().currentChanged.connect(self._on_current_changed)
        self.view.customContextMenuRequested.connect(self._show_context_menu)
        self.view.uninstall_requested.connect(self.uninstall_selected)
        self.view.info_requested.connect(self.show_selected_info)
        self.program_model.checked_changed.connect(self.update_summary)
        self.program_proxy.modelReset.connect(self._on_proxy_reset)

        self.details = DetailPanel()
        self.details.preview_requested.connect(self.show_file_preview)
        self.details.info_requested.connect(self.show_selected_info)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(10)
        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.details)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([720, 300])
        root.addWidget(self.splitter, 1)

        footer = QHBoxLayout()
        footer.setSpacing(12)
        self.summary = QLabel("No programs selected")
        self.summary.setObjectName("summaryText")
        self.summary.setAccessibleName("Selection summary")
        footer.addWidget(self.summary, 1, Qt.AlignmentFlag.AlignVCenter)

        self.silent = QCheckBox("Silent mode")
        self.silent.setAccessibleName("Use silent uninstall mode")
        self.silent.setToolTip("Ask uninstallers to run without interactive prompts when possible")
        footer.addWidget(self.silent, 0, Qt.AlignmentFlag.AlignVCenter)

        self.uninstall_btn = QPushButton("Uninstall selected")
        self.uninstall_btn.setObjectName("primaryButton")
        self.uninstall_btn.setIcon(QIcon(create_svg_icon(UNINSTALL_ICON)))
        self.uninstall_btn.setMinimumWidth(190)
        self.uninstall_btn.setAccessibleName("Uninstall selected programs")
        self.uninstall_btn.clicked.connect(self.uninstall_selected)
        footer.addWidget(self.uninstall_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(footer)

        QShortcut(QKeySequence("F5"), self).activated.connect(self.refresh_programs)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self._focus_search)
        QShortcut(QKeySequence("Ctrl+U"), self).activated.connect(self.uninstall_selected)
        self.setTabOrder(self.search, self.sort_combo)
        self.setTabOrder(self.sort_combo, self.disk_btn)
        self.setTabOrder(self.disk_btn, self.refresh_btn)
        self.setTabOrder(self.refresh_btn, self.view)
        self.setTabOrder(self.view, self.details.preview_button)
        self.setTabOrder(self.details.preview_button, self.details.info_button)
        self.setTabOrder(self.details.info_button, self.silent)
        self.setTabOrder(self.silent, self.uninstall_btn)

    def _ensure_controller(self):
        if self._controller is None:
            from app.controllers.uninstall import UninstallController

            self._controller = UninstallController(self, lambda: self.colors)
            self._connect_controller()
        return self._controller

    def _connect_controller(self) -> None:
        controller = self._controller
        controller.summary_changed.connect(self.set_summary)
        controller.progress_changed.connect(self._on_progress_changed)
        controller.progress_indeterminate.connect(self._on_progress_indeterminate)
        controller.progress_visible.connect(self.progress.setVisible)
        controller.stats_changed.connect(self._on_stats)
        controller.status_changed.connect(self._on_status_changed)
        controller.busy_changed.connect(self._on_busy)
        controller.finished.connect(self._on_uninstall_finished)

    def _restore_settings(self) -> None:
        geometry = self._settings.geometry()
        if geometry is not None:
            self.restoreGeometry(geometry)
        splitter_state = self._settings.splitter_state()
        if splitter_state is not None:
            self.splitter.restoreState(splitter_state)
        self.silent.setChecked(self._settings.silent_mode())
        self.sort_combo.setCurrentIndex(self._settings.sort_mode())

    def apply_theme(self, palette) -> None:
        self.colors = palette
        self.is_dark = palette == DARK
        self.setStyleSheet(build_style(palette))
        self.delegate.set_colors(palette)
        self.view.viewport().update()

    def on_system_theme_changed(self) -> None:
        self.apply_theme(system_palette())
        set_dark_title_bar(self, self.is_dark)

    def refresh_programs(self) -> None:
        if self._closing or self._loading or self._busy or self._loader is not None:
            return
        self._saved_checked = self.program_model.checked_keys()
        self._saved_selected = self._selected_key
        self._saved_scroll = self.view.verticalScrollBar().value()
        self._registry_programs = []
        self._store_programs = []
        self.programs = []
        self._selected_key = ""
        self._base_summary = ""
        self._load_failed = False
        self._store_loading = False
        self._refresh_pending = False
        self.program_model.clear()
        self.details.set_program(None)
        self._set_loading(True)

        worker = LoaderThread(self)
        worker.registry_loaded.connect(self._on_registry_loaded)
        worker.store_loaded.connect(self._on_store_loaded)
        worker.failed.connect(self._on_loader_failed)
        worker.completed.connect(self._on_loader_completed)
        worker.finished.connect(worker.deleteLater)
        self._loader = worker
        worker.start()

    def _set_loading(self, loading: bool) -> None:
        self._loading = loading
        if loading:
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)
            self.subtitle.setText("Reading the registry…")
            self.set_summary("Loading installed programs…")
        else:
            self.progress.setVisible(False)
        self.refresh_btn.setEnabled(not loading)
        self.disk_btn.setEnabled(not loading)
        self.sort_combo.setEnabled(not loading)
        self.uninstall_btn.setEnabled(not loading and not self._busy)

    def _on_registry_loaded(self, programs: list[Program]) -> None:
        if self._closing:
            return
        self._registry_programs = list(programs)
        self._rebuild_programs(initial=True)
        self._set_loading(False)
        self._store_loading = True
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._update_subtitle()

    def _on_store_loaded(self, programs: list[Program]) -> None:
        if self._closing:
            return
        self._store_programs = list(programs)
        self._rebuild_programs()
        self._update_subtitle()

    def _rebuild_programs(self, initial: bool = False) -> None:
        combined: list[Program] = []
        seen: set[str] = set()
        for program in (*self._registry_programs, *self._store_programs):
            if program.key in seen:
                continue
            seen.add(program.key)
            combined.append(program)
        combined.sort(key=lambda item: item.name.casefold())
        self.programs = combined

        checked = self._saved_checked if initial else self.program_model.checked_keys()
        selected = self._saved_selected if initial else self._selected_key
        scroll = self._saved_scroll if initial else self.view.verticalScrollBar().value()

        self.program_model.set_programs(self.programs)
        self.program_model.set_checked_keys(checked)
        if initial:
            self._saved_checked = set()
            self._saved_selected = ""
            self._saved_scroll = 0

        if selected:
            index = self.program_proxy.index_for_key(selected)
            if index.isValid():
                self.view.setCurrentIndex(index)
                self.view.scrollTo(index)
        QTimer.singleShot(0, lambda: self.view.verticalScrollBar().setValue(scroll))
        self.update_summary()
        self._update_subtitle()

    def _on_loader_completed(self) -> None:
        worker = self._loader
        self._loader = None
        self._store_loading = False
        if worker is not None and not self._load_failed:
            self._rebuild_programs()
        self._set_loading(False)
        self.progress.setVisible(False)
        if self._load_failed:
            return
        if not self.programs:
            self.subtitle.setText("No programs found")
        else:
            self._update_subtitle()
        self.update_summary()
        if self._refresh_pending:
            self._refresh_pending = False
            QTimer.singleShot(REFRESH_DELAY_MS, self.refresh_programs)

    def _on_loader_failed(self, message: str) -> None:
        self._load_failed = True
        self._set_loading(False)
        self.subtitle.setText("Could not load installed programs")
        self.set_summary("Registry error")
        QMessageBox.critical(self, "Registry error", message)

    def _on_proxy_reset(self) -> None:
        self.view.selectionModel().clearSelection()

    def _on_current_changed(self, current: QModelIndex, previous: QModelIndex) -> None:
        program = self.program_proxy.program_at(current)
        self._selected_key = program.key if program is not None else ""
        self.details.set_program(program)

    def _focus_search(self) -> None:
        self.search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.search.selectAll()

    def _apply_filter(self) -> None:
        self.program_proxy.set_filter_text(self.search.text())
        if self._selected_key:
            index = self.program_proxy.index_for_key(self._selected_key)
            if index.isValid():
                if self.view.currentIndex() != index:
                    self.view.setCurrentIndex(index)
            else:
                self.view.clearSelection()
                self.details.set_program(None)
                self._selected_key = ""
        self._update_subtitle()

    def _on_sort_changed(self, index: int) -> None:
        self.program_proxy.set_sort_mode(index)
        self._settings.set_sort_mode(index)
        if self._selected_key:
            target = self.program_proxy.index_for_key(self._selected_key)
            if target.isValid():
                self.view.setCurrentIndex(target)
                self.view.scrollTo(target)
        self._update_subtitle()

    def _update_subtitle(self) -> None:
        if self._loading and not self.programs:
            self.subtitle.setText("Reading the registry…")
            return
        total = len(self.programs)
        if self._store_loading and total:
            self.subtitle.setText(f"{total} programs found   ·   loading Store apps…")
            return
        if total == 0:
            self.subtitle.setText("No programs found")
            return
        query = self.search.text().strip()
        if query:
            self.subtitle.setText(
                f"{self.program_proxy.rowCount()} of {total} programs shown"
            )
            return
        size = sum(program.size_bytes for program in self.programs)
        if size > 0:
            self.subtitle.setText(
                f"{total} programs found   ·   {format_size(size)} installed"
            )
        else:
            self.subtitle.setText(f"{total} programs found")

    def checked_programs(self) -> list[Program]:
        return self.program_model.checked_programs()

    def update_summary(self) -> None:
        if self._loading or self._busy:
            return
        checked = self.checked_programs()
        if not checked:
            self.set_summary("No programs selected")
            return
        size = sum(program.size_bytes for program in checked)
        if size > 0:
            self.set_summary(
                f"<b>{len(checked)}</b> selected   ·   ~{format_size(size)} to be freed"
            )
        else:
            self.set_summary(f"<b>{len(checked)}</b> selected")

    def set_summary(self, text: str) -> None:
        self._base_summary = text
        self.summary.setText(text)

    def _on_stats(self, text: str) -> None:
        if text:
            self.summary.setText(f"{self._base_summary}   |   {text}")
        else:
            self.summary.setText(self._base_summary)

    def _on_progress_changed(self, done: int, total: int) -> None:
        self._progress_total = max(1, total)
        self.progress.setRange(0, self._progress_total)
        self.progress.setValue(done)

    def _on_progress_indeterminate(self, enabled: bool) -> None:
        if enabled:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, self._progress_total)
            self.progress.setValue(0)

    def _on_status_changed(self, key: str, status: str) -> None:
        if not key or not status:
            return
        try:
            value = ProgramStatus(status)
        except ValueError:
            return
        self.program_model.set_status(key, value)

    def _on_busy(self, busy: bool) -> None:
        self._busy = busy
        self.refresh_btn.setEnabled(not busy and not self._loading)
        self.disk_btn.setEnabled(not busy and not self._loading)
        self.sort_combo.setEnabled(not busy and not self._loading)
        self.silent.setEnabled(not busy)
        self.uninstall_btn.setEnabled(not busy and not self._loading)
        self.program_model.set_checkable(not busy)
        if not busy:
            self.update_summary()

    def _on_uninstall_finished(self) -> None:
        if self._closing:
            return
        if self._loader is not None:
            self._refresh_pending = True
            return
        QTimer.singleShot(REFRESH_DELAY_MS, self.refresh_programs)

    def uninstall_selected(self) -> None:
        if self._loading or self._busy:
            return
        programs = self.checked_programs()
        if not programs:
            QMessageBox.warning(
                self,
                "Nothing selected",
                "Select at least one program to uninstall.",
            )
            return
        if not self._confirm(programs):
            return
        self._ensure_controller().uninstall(programs, self.silent.isChecked())

    def uninstall_one(self, program: Program) -> None:
        if self._loading or self._busy:
            return
        if not self._confirm([program]):
            return
        self._ensure_controller().uninstall([program], self.silent.isChecked())

    def _confirm(self, programs: list[Program]) -> bool:
        if len(programs) == 1:
            message = f"Are you sure you want to uninstall {programs[0].name}?"
        else:
            message = f"Are you sure you want to uninstall {len(programs)} selected programs?"
        answer = QMessageBox.question(
            self,
            "Confirmation",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def show_selected_info(self) -> None:
        from app.ui.dialogs import InfoDialog

        program = self.details.program
        if program is None:
            index = self.view.currentIndex()
            program = self.program_proxy.program_at(index)
        if program is not None:
            InfoDialog(program, self.colors, self).exec()

    def show_file_preview(self) -> None:
        from app.ui.dialogs import FilePreviewDialog

        program = self.details.program
        if program is None:
            checked = self.checked_programs()
            if not checked:
                QMessageBox.warning(self, "No program selected", "Select a program first.")
                return
            program = checked[0]
        FilePreviewDialog(program, self.colors, self).exec()

    def show_disk_space(self) -> None:
        from app.ui.dialogs import DiskSpaceDialog

        if self._busy or self._loading:
            return
        DiskSpaceDialog(self.programs, self.colors, self).exec()

    def _show_context_menu(self, position) -> None:
        from app.ui.dialogs import FilePreviewDialog, InfoDialog

        index = self.view.indexAt(position)
        program = self.program_proxy.program_at(index)
        if program is None:
            return
        menu = QMenu(self)
        info_action = QAction("Program Information", self)
        info_action.triggered.connect(
            lambda: InfoDialog(program, self.colors, self).exec()
        )
        menu.addAction(info_action)
        preview_action = QAction("Preview files", self)
        preview_action.triggered.connect(
            lambda: FilePreviewDialog(program, self.colors, self).exec()
        )
        menu.addAction(preview_action)
        menu.addSeparator()
        uninstall_action = QAction("Uninstall", self)
        uninstall_action.triggered.connect(lambda: self.uninstall_one(program))
        menu.addAction(uninstall_action)
        menu.exec(self.view.viewport().mapToGlobal(position))

    def closeEvent(self, event) -> None:
        controller = self._controller
        if controller is not None and controller.busy:
            event.ignore()
            self.set_summary(
                "Cleaning up — the window will close when the operation finishes"
            )
            return
        if controller is not None and not controller.shutdown():
            event.ignore()
            self.set_summary("Finishing background work — try closing again shortly")
            return
        self._closing = True
        self._settings.set_geometry(self.saveGeometry())
        self._settings.set_splitter_state(self.splitter.saveState())
        self._settings.set_silent_mode(self.silent.isChecked())
        self._settings.set_sort_mode(self.sort_combo.currentIndex())
        self._settings.sync()
        loader = self._loader
        if loader is not None:
            try:
                running = loader.isRunning()
            except RuntimeError:
                running = False
            if running:
                loader.requestInterruption()
                if not loader.wait(2000):
                    loader.terminate()
                    loader.wait(500)
        event.accept()
