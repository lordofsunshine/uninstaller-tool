from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QCheckBox, QProgressBar, QLabel, QMessageBox, QLineEdit, 
                             QScrollArea, QMenu, QComboBox, QDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction
from config.constants import COLORS, REFRESH_ICON, UNINSTALL_ICON, CHART_ICON, PREVIEW_ICON
from config.styles import ENHANCED_STYLE
from utils.theme_manager import ThemeManager
from utils.helpers import create_svg_icon, format_install_date
from core.registry import get_installed_programs
from core.file_operations import remove_leftovers
from threads.uninstall_thread import UninstallThread
from threads.leftover_search_thread import LeftoverSearchThread
from ui.program_item import ProgramItem
from ui.disk_space_dialog import DiskSpaceDialog
from ui.file_preview_dialog import FilePreviewDialog

class UninstallerTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_manager = ThemeManager()
        self.setWindowTitle("Uninstaller Tool")
        self.setMinimumSize(600, 400)
        self.resize(800, 600)
        self.center_window()
        self.setup_ui()
        self.uninstalled_programs = []

    def center_window(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 16, 16, 16)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search programs...")
        self.search_input.setMinimumHeight(40)
        self.search_input.textChanged.connect(self.filter_programs)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        tools_and_sort_layout = QHBoxLayout()
        tools_and_sort_layout.setContentsMargins(0, 0, 0, 0)
        tools_and_sort_layout.setSpacing(8)
        
        sort_layout = QHBoxLayout()
        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet("font-weight: bold;")
        sort_label.setMinimumWidth(50)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Size", "Install Date", "Publisher"])
        self.sort_combo.setMinimumWidth(200)
        self.sort_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                padding: 8px 12px;
                background: white;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
        """)
        self.sort_combo.currentTextChanged.connect(self.sort_programs)
        
        sort_layout.addWidget(sort_label)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        
        tools_and_sort_layout.addLayout(sort_layout)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        self.disk_space_button = QPushButton("  Disk Space Usage")
        self.disk_space_button.setIcon(QIcon(create_svg_icon(CHART_ICON)))
        self.disk_space_button.clicked.connect(self.show_disk_space)
        self.disk_space_button.setMinimumWidth(120)
        self.disk_space_button.setMaximumWidth(200)
        self.disk_space_button.setStyleSheet("""
            QPushButton {
                background-color: #0066FF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: bold;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:hover {
                background-color: #0052CC;
            }
        """)
        
        self.preview_button = QPushButton("  Preview Files")
        self.preview_button.setIcon(QIcon(create_svg_icon(PREVIEW_ICON)))
        self.preview_button.clicked.connect(self.show_file_preview)
        self.preview_button.setMinimumWidth(100)
        self.preview_button.setMaximumWidth(180)
        self.preview_button.setStyleSheet("""
            QPushButton {
                background-color: #0066FF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: bold;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:hover {
                background-color: #0052CC;
            }
        """)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.disk_space_button)
        buttons_layout.addWidget(self.preview_button)
        
        tools_and_sort_layout.addLayout(buttons_layout)
        main_layout.addLayout(tools_and_sort_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.program_list_widget = QWidget()
        self.program_list_layout = QVBoxLayout(self.program_list_widget)
        self.program_list_layout.setSpacing(8)
        self.program_list_layout.setContentsMargins(0, 0, 0, 0)
        self.program_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.program_list_widget)
        main_layout.addWidget(self.scroll_area)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.refresh_button = QPushButton("Refresh List")
        self.refresh_button.setMinimumHeight(40)
        self.refresh_button.clicked.connect(self.refresh_program_list)
        self.refresh_button.setIcon(QIcon(create_svg_icon(REFRESH_ICON)))
        
        self.uninstall_button = QPushButton("Uninstall Selected")
        self.uninstall_button.setMinimumHeight(40)
        self.uninstall_button.clicked.connect(self.uninstall_selected)
        self.uninstall_button.setIcon(QIcon(create_svg_icon(UNINSTALL_ICON)))
        
        self.silent_checkbox = QCheckBox("Silent Uninstall")
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.uninstall_button)
        button_layout.addWidget(self.silent_checkbox)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(8)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        main_layout.addWidget(self.status_label)

        self.apply_modern_style()
        self.refresh_program_list()
        
        self.resizeEvent = self.on_resize

    def apply_modern_style(self):
        self.setStyleSheet(ENHANCED_STYLE % {
            'background': COLORS['background'],
            'text': COLORS['text'],
            'primary': COLORS['primary'],
            'primary_hover': COLORS['primary_hover'],
            'primary_pressed': COLORS['primary_pressed'],
            'input_bg': COLORS['input_bg'],
            'border': COLORS['border'],
            'progress_bg': COLORS['progress_bg'],
            'scroll_bg': COLORS['scroll_bg'],
            'scroll_handle': COLORS['scroll_handle'],
            'surface': COLORS['surface'],
            'text_secondary': COLORS['text_secondary']
        })

    def refresh_program_list(self):
        self.clear_program_list()
        programs = get_installed_programs()
        
        for program in programs:
            item = ProgramItem(program)
            item.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            item.customContextMenuRequested.connect(lambda pos, p=program: self.show_context_menu(pos, p))
            self.program_list_layout.addWidget(item)
            item.show()
        
        self.status_label.setText("")
        self.progress_bar.setValue(0)

    def clear_program_list(self):
        while self.program_list_layout.count():
            child = self.program_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def filter_programs(self):
        search_text = self.search_input.text().lower()
        for i in range(self.program_list_layout.count()):
            item = self.program_list_layout.itemAt(i).widget()
            if search_text in item.checkbox.text().lower():
                item.show()
            else:
                item.hide()

    def uninstall_selected(self):
        programs_to_uninstall = []
        for i in range(self.program_list_layout.count()):
            item = self.program_list_layout.itemAt(i).widget()
            if isinstance(item, ProgramItem) and item.checkbox.isChecked():
                programs_to_uninstall.append(item.program)

        if not programs_to_uninstall:
            QMessageBox.warning(self, "Warning", "No programs selected for uninstallation.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirmation",
            f"Are you sure you want to uninstall {len(programs_to_uninstall)} selected programs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.progress_bar.setMaximum(len(programs_to_uninstall))
            self.progress_bar.setValue(0)
            
            self.uninstall_thread = UninstallThread(programs_to_uninstall, self.silent_checkbox.isChecked())
            self.uninstall_thread.progress.connect(self.update_progress)
            self.uninstall_thread.finished.connect(self.uninstall_finished)
            self.uninstall_thread.error.connect(self.show_error)
            self.uninstall_thread.silent_failed.connect(self.handle_silent_fail)
            self.uninstall_thread.start()
            
            self.refresh_button.setEnabled(False)
            self.uninstall_button.setEnabled(False)

    def update_progress(self, value, status, status_type):
        self.progress_bar.setValue(value)
        self.status_label.setText(status)
        for i in range(self.program_list_layout.count()):
            item = self.program_list_layout.itemAt(i).widget()
            if isinstance(item, ProgramItem) and item.checkbox.text() in status:
                item.set_status(status_type)

    def uninstall_finished(self):
        self.refresh_button.setEnabled(True)
        self.uninstall_button.setEnabled(True)
        self.status_label.setText("Uninstallation completed")
        self.uninstalled_programs = self.uninstall_thread.uninstalled_programs
        
        if self.uninstalled_programs:
            QTimer.singleShot(2000, self.search_leftovers)
        else:
            self.status_label.setText("No programs were uninstalled")
            QTimer.singleShot(2000, self.refresh_program_list)

    def search_leftovers(self):
        if not self.uninstalled_programs:
            return

        self.leftover_search_thread = LeftoverSearchThread(self.uninstalled_programs[0])
        self.leftover_search_thread.progress.connect(self.update_leftover_search_progress)
        self.leftover_search_thread.finished.connect(self.show_leftovers)
        self.leftover_search_thread.error.connect(self.show_error)
        self.leftover_search_thread.start()

    def update_leftover_search_progress(self, status):
        self.status_label.setText(status)

    def show_leftovers(self, leftovers):
        if leftovers['files'] or leftovers['registry']:
            self.status_label.setText("Leftover files found")
            dialog = self.create_leftovers_dialog(leftovers)
            dialog.exec()
            
            self.uninstalled_programs.pop(0)
            if self.uninstalled_programs:
                self.search_leftovers()
            else:
                QTimer.singleShot(2000, self.refresh_program_list)
        else:
            self.status_label.setText("No leftover files found")
            QMessageBox.information(self, "Leftover Search", "No leftover files or registry entries found.")
            
            self.uninstalled_programs.pop(0)
            if self.uninstalled_programs:
                QTimer.singleShot(1000, self.search_leftovers)
            else:
                QTimer.singleShot(2000, self.refresh_program_list)

    def create_leftovers_dialog(self, leftovers):
        from PyQt6.QtWidgets import QListWidget
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Leftover Files and Entries")
        dialog.setMinimumSize(600, 500)
        dialog.resize(700, 600)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Found leftover items:")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #1A1A1A; }")
        layout.addWidget(title)
        
        if leftovers['files']:
            files_group = QWidget()
            files_layout = QVBoxLayout(files_group)
            files_layout.setSpacing(8)
            
            files_header = QLabel(f"Files ({len(leftovers['files'])} items):")
            files_header.setStyleSheet("font-weight: bold; color: #0066FF;")
            files_layout.addWidget(files_header)
            
            files_list = QListWidget()
            files_list.setMinimumHeight(150)
            files_list.setStyleSheet("""
                QListWidget {
                    border: 1px solid #E5E5EA;
                    border-radius: 8px;
                    background: #F5F5F7;
                    padding: 8px;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #E5E5EA;
                }
            """)
            for file in leftovers['files']:
                files_list.addItem(file)
            files_layout.addWidget(files_list)
            layout.addWidget(files_group)
        
        if leftovers['registry']:
            registry_group = QWidget()
            registry_layout = QVBoxLayout(registry_group)
            registry_layout.setSpacing(8)
            
            registry_header = QLabel(f"Registry entries ({len(leftovers['registry'])} items):")
            registry_header.setStyleSheet("font-weight: bold; color: #0066FF;")
            registry_layout.addWidget(registry_header)
            
            registry_list = QListWidget()
            registry_list.setMinimumHeight(150)
            registry_list.setStyleSheet("""
                QListWidget {
                    border: 1px solid #E5E5EA;
                    border-radius: 8px;
                    background: #F5F5F7;
                    padding: 8px;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #E5E5EA;
                }
            """)
            for entry in leftovers['registry']:
                registry_list.addItem(entry)
            registry_layout.addWidget(registry_list)
            layout.addWidget(registry_group)
        
        button_layout = QHBoxLayout()
        remove_button = QPushButton("Remove All")
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #0066FF;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0052CC; }
        """)
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F7;
                color: #1A1A1A;
                border: 1px solid #E5E5EA;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E5E5EA; }
        """)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(remove_button)
        layout.addLayout(button_layout)
        
        remove_button.clicked.connect(lambda: [self.remove_leftovers_action(leftovers), dialog.accept()])
        cancel_button.clicked.connect(dialog.reject)
        
        return dialog

    def remove_leftovers_action(self, leftovers):
        try:
            result = remove_leftovers(leftovers)
            removed_files = result['removed_files']
            removed_registry = result['removed_registry']
            errors = result['errors']
            
            self.status_label.setText(f"Cleanup completed: {removed_files} files, {removed_registry} registry entries removed")
            self.progress_bar.setValue(self.progress_bar.maximum())
            
            QTimer.singleShot(2000, lambda: [
                self.refresh_program_list(),
                self.status_label.setText(""),
                self.progress_bar.setValue(0)
            ])

            if errors:
                error_msg = f"Cleanup completed with {len(errors)} errors:\n\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    error_msg += f"\n... and {len(errors) - 5} more errors"
                QMessageBox.warning(self, "Cleanup Complete with Errors", error_msg)
            else:
                QMessageBox.information(self, "Cleanup Complete", f"Successfully removed {removed_files} files and {removed_registry} registry entries.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during cleanup: {str(e)}")

    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def handle_silent_fail(self, program):
        uninstall_string = program.get('uninstall_string', '')
        reply = QMessageBox.question(
            self,
            "Silent Uninstall Failed",
            f"Failed to perform silent uninstall for {program['name']}.\n\nUninstall command: {uninstall_string}\n\nDo you want to try regular uninstall?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.uninstall_program(program, silent=False)

    def show_context_menu(self, pos, program):
        context_menu = QMenu(self)
        
        info_action = QAction("Program Information", self)
        info_action.triggered.connect(lambda: self.show_program_info(program))
        context_menu.addAction(info_action)
        
        uninstall_action = QAction("Uninstall", self)
        uninstall_action.triggered.connect(lambda: self.uninstall_program(program))
        context_menu.addAction(uninstall_action)
        
        global_pos = self.sender().mapToGlobal(pos)
        context_menu.exec(global_pos)

    def show_program_info(self, program):
        dialog = QDialog(self)
        dialog.setWindowTitle("Program Information")
        dialog.setMinimumSize(500, 400)
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title = QLabel(program['name'])
        title.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #1A1A1A; }")
        layout.addWidget(title)
        
        info_container = QWidget()
        info_container.setStyleSheet("""
            QWidget {
                background-color: #F5F5F7;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        info_layout = QVBoxLayout(info_container)
        info_layout.setSpacing(12)
        
        def add_info_row(label, value, is_multiline=False):
            row = QHBoxLayout()
            label_widget = QLabel(label)
            label_widget.setStyleSheet("QLabel { color: #6E6E73; font-weight: bold; min-width: 120px; }")
            row.addWidget(label_widget)
            
            value_widget = QLabel(value or "Not available")
            if is_multiline:
                value_widget.setWordWrap(True)
                value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value_widget.setStyleSheet("QLabel { color: #1A1A1A; }")
            row.addWidget(value_widget, 1)
            info_layout.addLayout(row)
        
        add_info_row("Publisher:", program.get('publisher', ''))
        add_info_row("Install Date:", format_install_date(program.get('install_date', '')))
        add_info_row("Version:", program.get('version', ''))
        add_info_row("Location:", program.get('install_location', ''), True)
        add_info_row("Uninstall Command:", program.get('uninstall_string', ''), True)
        
        if program.get('size'):
            add_info_row("Size:", f"{int(program['size']) / 1024 / 1024:.2f} MB")
        
        layout.addWidget(info_container)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("OK")
        ok_button.setMinimumSize(100, 36)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #0066FF;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #0052CC; }
        """)
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        dialog.exec()

    def uninstall_program(self, program, silent=None):
        if silent is None:
            silent = self.silent_checkbox.isChecked()

        confirm = QMessageBox.question(
            self,
            "Confirmation",
            f"Are you sure you want to uninstall {program['name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.uninstall_thread = UninstallThread([program], silent)
            self.uninstall_thread.progress.connect(self.update_progress)
            self.uninstall_thread.finished.connect(self.uninstall_finished)
            self.uninstall_thread.error.connect(self.show_error)
            self.uninstall_thread.silent_failed.connect(self.handle_silent_fail)
            self.uninstall_thread.start()
            
            self.refresh_button.setEnabled(False)
            self.uninstall_button.setEnabled(False)

    def sort_programs(self):
        sort_type = self.sort_combo.currentText()
        items = []
        
        for i in range(self.program_list_layout.count()):
            widget = self.program_list_layout.itemAt(i).widget()
            if isinstance(widget, ProgramItem):
                items.append(widget)
        
        if sort_type == "Name":
            items.sort(key=lambda x: x.program['name'].lower())
        elif sort_type == "Size":
            items.sort(key=lambda x: float(x.program.get('size', 0) or 0), reverse=True)
        elif sort_type == "Install Date":
            items.sort(key=lambda x: x.program.get('install_date', ''), reverse=True)
        elif sort_type == "Publisher":
            items.sort(key=lambda x: (x.program.get('publisher', '') or '').lower())
        
        while self.program_list_layout.count():
            self.program_list_layout.takeAt(0)
        
        for item in items:
            self.program_list_layout.addWidget(item)

    def show_disk_space(self):
        dialog = DiskSpaceDialog(get_installed_programs(), self)
        dialog.exec()

    def on_resize(self, event):
        width = self.width()
        
        if width < 600:
            self.disk_space_button.setText("  Disk Spa...")
            self.preview_button.setText("  Preview...")
        elif width < 700:
            self.disk_space_button.setText("  Disk Space...")
            self.preview_button.setText("  Preview...")
        else:
            self.disk_space_button.setText("  Disk Space Usage")
            self.preview_button.setText("  Preview Files")
        
        super().resizeEvent(event)

    def show_file_preview(self):
        selected_programs = []
        for i in range(self.program_list_layout.count()):
            item = self.program_list_layout.itemAt(i).widget()
            if isinstance(item, ProgramItem) and item.checkbox.isChecked():
                selected_programs.append(item.program)
        
        if not selected_programs:
            QMessageBox.warning(self, "Warning", "Please select programs to preview")
            return
        
        program = selected_programs[0]
        dialog = FilePreviewDialog(program, self)
        dialog.exec()
