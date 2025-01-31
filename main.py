import sys
import winreg
import subprocess
import os
import psutil
import shutil
import math
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QCheckBox, 
                             QProgressBar, QLabel, QMessageBox, QListWidgetItem,
                             QLineEdit, QScrollArea, QSizePolicy, QMenu, QFrame, QToolBar, QDialog, QComboBox, QTabWidget, QGroupBox)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal, QTimer, QPoint, QParallelAnimationGroup
from PyQt6.QtGui import QColor, QPalette, QIcon, QFont, QPixmap, QPainter, QAction
from PyQt6.QtSvg import QSvgRenderer

REFRESH_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
    <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
</svg>
"""

UNINSTALL_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
    <line x1="10" y1="11" x2="10" y2="17"/>
    <line x1="14" y1="11" x2="14" y2="17"/>
</svg>
"""

CHART_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
    <path d="M18 20V10"/>
    <path d="M12 20V4"/>
    <path d="M6 20v-6"/>
</svg>
"""

PREVIEW_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
    <circle cx="12" cy="12" r="3"/>
</svg>
"""

DOWN_ARROW_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M6 9l6 6 6-6"/>
</svg>
"""

COLORS = {
    'primary': '#0066FF',           # Pleasant blue
    'primary_hover': '#0052CC',     # Dark blue for hover
    'primary_pressed': '#004999',   # Adding color for pressed state
    'background': '#FFFFFF',        # White background
    'surface': '#F5F5F7',          # Light gray for elements
    'text': '#1A1A1A',             # Almost black for text
    'text_secondary': '#6E6E73',    # Gray for secondary text
    'border': '#E5E5EA',           # Light gray for borders
    'success': '#34C759',          # Green
    'error': '#FF3B30',            # Red
    'warning': '#FF9500',          # Orange
    'progress_bg': '#E5E5EA',      # Background for progress bar
    'scroll_bg': '#F2F2F7',        # Background for scrollbar
    'scroll_handle': '#C7C7CC',    # Color for scrollbar handle
    'input_bg': '#F2F2F7'          # Background for input fields
}

ENHANCED_STYLE = """
QMainWindow {
    background-color: %(background)s;
    border: none;
}

QWidget {
    background-color: %(background)s;
    color: %(text)s;
    font-family: 'Segoe UI', sans-serif;
    border: none;
}

QLineEdit {
    padding: 12px;
    background-color: %(surface)s;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    color: %(text)s;
    margin: 0 8px;
}

QLineEdit:focus {
    background-color: #FFFFFF;
    border: 2px solid %(primary)s;
}

QPushButton {
    background-color: %(primary)s;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: bold;
    margin: 0 4px;
}

QPushButton:hover {
    background-color: %(primary_hover)s;
}

QPushButton:pressed {
    background-color: %(primary_pressed)s;
}

QCheckBox {
    spacing: 8px;
    font-size: 14px;
    color: %(text)s;
    padding: 4px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid %(text_secondary)s;
}

QCheckBox::indicator:checked {
    background-color: %(primary)s;
    border-color: %(primary)s;
}

QProgressBar {
    border: none;
    border-radius: 6px;
    text-align: center;
    font-size: 12px;
    font-weight: bold;
    min-height: 12px;
    max-height: 12px;
    background-color: %(progress_bg)s;
    margin: 0 8px;
}

QProgressBar::chunk {
    background-color: %(primary)s;
    border-radius: 6px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background-color: %(scroll_bg)s;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: %(scroll_handle)s;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: %(primary)s;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}

QListWidget {
    border: none;
    background-color: transparent;
    outline: none;
    margin: 8px;
}

QListWidget::item {
    background-color: %(surface)s;
    border-radius: 8px;
    margin: 4px 8px;
    padding: 12px;
}

QListWidget::item:hover {
    background-color: #FFFFFF;
    border: 1px solid %(border)s;
}

QListWidget::item:selected {
    background-color: #FFFFFF;
    border: 2px solid %(primary)s;
}

QToolBar {
    background-color: %(background)s;
    border: none;
    spacing: 10px;
    padding: 10px;
}

QLabel {
    color: %(text)s;
    font-size: 14px;
}
"""

class UninstallThread(QThread):
    progress = pyqtSignal(int, str, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    silent_failed = pyqtSignal(dict)

    def __init__(self, programs, silent):
        super().__init__()
        self.programs = programs
        self.silent = silent
        self.current_process = None
        self.uninstalled_programs = []

    def run(self):
        for i, program in enumerate(self.programs):
            try:
                self.progress.emit(i, f"Uninstalling {program['name']}...", "running")
                
                if self.silent:
                    cmd = f"{program['uninstall_string']} /S"
                    self.current_process = subprocess.Popen(cmd, shell=True)
                    if self.current_process.wait(timeout=300) != 0:
                        self.silent_failed.emit(program)
                        continue
                else:
                    self.current_process = subprocess.Popen(program['uninstall_string'], shell=True)
                    self.current_process.wait()
                
                while self.check_child_processes(self.current_process.pid):
                    QThread.msleep(100)
                
                if self.current_process.returncode == 0:
                    self.progress.emit(i + 1, f"{program['name']} successfully uninstalled", "success")
                    self.uninstalled_programs.append(program)
                else:
                    self.progress.emit(i + 1, f"Error uninstalling {program['name']}", "error")
            except subprocess.TimeoutExpired:
                self.silent_failed.emit(program)
            except Exception as e:
                self.error.emit(f"Error uninstalling {program['name']}: {str(e)}")
        self.finished.emit()

    def check_child_processes(self, parent_pid):
        try:
            parent = psutil.Process(parent_pid)
            children = parent.children(recursive=True)
            return len(children) > 0
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

class LeftoverSearchThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, program):
        super().__init__()
        self.program = program

    def run(self):
        leftovers = {'files': [], 'registry': []}

        self.progress.emit("Searching for leftover files...")
        leftovers['files'] = self.search_leftover_files()

        self.progress.emit("Searching for leftover registry entries...")
        leftovers['registry'] = self.search_leftover_registry()

        self.finished.emit(leftovers)

    def search_leftover_files(self):
        leftover_files = []
        common_paths = [
            os.path.expandvars(r'%ProgramFiles%'),
            os.path.expandvars(r'%ProgramFiles(x86)%'),
            os.path.expandvars(r'%AppData%'),
            os.path.expandvars(r'%LocalAppData%'),
            os.path.expandvars(r'%ProgramData%'),
            os.path.expandvars(r'%UserProfile%'),
            os.path.expandvars(r'%Public%')
        ]
        
        program_name_parts = self.program['name'].lower().split()
        
        for path in common_paths:
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    for item in dirs + files:
                        item_lower = item.lower()
                        if any(part in item_lower for part in program_name_parts):
                            full_path = os.path.join(root, item)
                            leftover_files.append(full_path)

        return leftover_files

    def search_leftover_registry(self):
        leftover_registry = []
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        for hkey, key_path in registry_paths:
            try:
                key = winreg.OpenKey(hkey, key_path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0].strip()
                            if self.program['name'].lower() in display_name.lower():
                                leftover_registry.append(f"{key_path}\\{subkey_name}")
                        except WindowsError:
                            pass
                        finally:
                            winreg.CloseKey(subkey)
                    except WindowsError:
                        continue
                winreg.CloseKey(key)
            except WindowsError:
                continue

        return leftover_registry

class ProgramItem(QFrame):
    def __init__(self, program, parent=None):
        super().__init__(parent)
        self.program = program
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) 
        layout.setSpacing(8)
        
        self.checkbox = QCheckBox(self.program['name'])
        self.checkbox.setFont(QFont("Segoe UI", 10))
        
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setMinimumWidth(80)
        self.status_label.setMaximumWidth(80)
        
        layout.addWidget(self.checkbox, 1)
        layout.addWidget(self.status_label)
        
        self.setMinimumHeight(40)
        
        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #6E6E73;
            }
            QCheckBox::indicator:checked {
                background-color: #0066FF;
                border-color: #0066FF;
            }
            QLabel {
                color: #1A1A1A;
            }
        """)

    def set_status(self, status):
        if status == "running":
            self.status_label.setText("Uninstalling...")
            self.status_label.setStyleSheet(f"color: {COLORS['primary']}; font-weight: bold;")
        elif status == "success":
            self.status_label.setText("Uninstalled")
            self.status_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        elif status == "error":
            self.status_label.setText("Error")
            self.status_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: bold;")
        else:
            self.status_label.setText("")

class ThemeManager:
    def __init__(self):
        self.is_dark = False
        self._update_colors()

    def _update_colors(self):
        self.current_colors = {
            'background': COLORS['background'],        
            'text': COLORS['text'],                   
            'border': COLORS['border'],               
            'input_bg': COLORS['input_bg'],           
            'primary': COLORS['primary'],             
            'primary_hover': COLORS['primary_hover'], 
            'primary_pressed': COLORS['primary_pressed'],
            'progress_bg': COLORS['progress_bg'],      
            'scroll_bg': COLORS['scroll_bg'],         
            'scroll_handle': COLORS['scroll_handle'], 
            'surface': COLORS['surface'],             
            'text_secondary': COLORS['text_secondary'] 
        }

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self._update_colors()
        return self.get_stylesheet()

    def get_stylesheet(self):
        return ENHANCED_STYLE % self.current_colors

class UninstallerTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_manager = ThemeManager()
        self.setWindowTitle("Uninstaller Tool")
        
        self.setFixedSize(800, 600)
        
        self.center_window()
        
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)
        
        self.setup_ui()
        self.uninstalled_programs = []

    def center_window(self):
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
        self.search_input.setFixedHeight(40)
        self.search_input.textChanged.connect(self.filter_programs)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        tools_and_sort_layout = QHBoxLayout()
        tools_and_sort_layout.setContentsMargins(0, 0, 0, 0)  
        
        sort_layout = QHBoxLayout()
        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet("font-weight: bold;")
        sort_label.setFixedWidth(50)  
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Size", "Install Date", "Publisher"])
        self.sort_combo.setFixedWidth(200) 
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
        buttons_layout.setSpacing(8) 
        
        disk_space_button = QPushButton("  Disk Space Usage")
        disk_space_button.setIcon(QIcon(self.create_svg_icon(CHART_ICON)))
        disk_space_button.clicked.connect(self.show_disk_space)
        disk_space_button.setFixedWidth(180)  
        disk_space_button.setStyleSheet("""
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
        
        preview_button = QPushButton("  Preview Files")
        preview_button.setIcon(QIcon(self.create_svg_icon(PREVIEW_ICON)))
        preview_button.clicked.connect(self.show_file_preview)
        preview_button.setFixedWidth(150) 
        preview_button.setStyleSheet("""
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
        buttons_layout.addWidget(disk_space_button)
        buttons_layout.addWidget(preview_button)
        
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
        self.refresh_button.setFixedHeight(40)
        self.refresh_button.clicked.connect(self.refresh_program_list)
        self.refresh_button.setIcon(QIcon(self.create_svg_icon(REFRESH_ICON)))
        
        self.uninstall_button = QPushButton("Uninstall Selected")
        self.uninstall_button.setFixedHeight(40)
        self.uninstall_button.clicked.connect(self.uninstall_selected)
        self.uninstall_button.setIcon(QIcon(self.create_svg_icon(UNINSTALL_ICON)))
        
        self.silent_checkbox = QCheckBox("Silent Uninstall")
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.uninstall_button)
        button_layout.addWidget(self.silent_checkbox)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        main_layout.addWidget(self.status_label)

        self.apply_modern_style()
        self.refresh_program_list()

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

    def create_svg_icon(self, svg_str):
        renderer = QSvgRenderer(bytearray(svg_str, encoding='utf-8'))
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    def refresh_program_list(self):
        self.clear_program_list()
        programs = self.get_installed_programs()
        
        for program in programs:
            item = ProgramItem(program)
            item.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            item.customContextMenuRequested.connect(lambda pos, p=program: self.show_context_menu(pos, p))
            self.program_list_layout.addWidget(item)
            item.show()
        
        self.animate_list_refresh()

    def clear_program_list(self):
        while self.program_list_layout.count():
            child = self.program_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def animate_list_refresh(self):
        for i in range(self.program_list_layout.count()):
            widget = self.program_list_layout.itemAt(i).widget()
            if widget:
                widget.show()

    def get_installed_programs(self):
        programs = {}
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        for hkey, key_path in registry_paths:
            try:
                key = winreg.OpenKey(hkey, key_path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        
                        try:
                            program_info = {
                                'name': winreg.QueryValueEx(subkey, "DisplayName")[0].strip(),
                                'uninstall_string': winreg.QueryValueEx(subkey, "UninstallString")[0].strip(),
                                'install_location': '',
                                'publisher': '',
                                'install_date': '',
                                'version': '',
                                'size': '',
                                'url': '',
                                'contact': ''
                            }

                            try: program_info['install_location'] = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            except: pass
                            try: program_info['publisher'] = winreg.QueryValueEx(subkey, "Publisher")[0]
                            except: pass
                            try: program_info['install_date'] = winreg.QueryValueEx(subkey, "InstallDate")[0]
                            except: pass
                            try: program_info['version'] = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                            except: pass
                            try: program_info['size'] = winreg.QueryValueEx(subkey, "EstimatedSize")[0]
                            except: pass
                            try: program_info['url'] = winreg.QueryValueEx(subkey, "URLInfoAbout")[0]
                            except: pass
                            try: program_info['contact'] = winreg.QueryValueEx(subkey, "HelpTelephone")[0]
                            except: pass

                            if program_info['name'] not in programs:
                                programs[program_info['name']] = program_info

                        except WindowsError:
                            continue
                        finally:
                            winreg.CloseKey(subkey)
                    except WindowsError:
                        continue
                winreg.CloseKey(key)
            except WindowsError:
                continue

        return sorted(programs.values(), key=lambda x: x['name'].lower())

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
        QTimer.singleShot(2000, self.search_leftovers)

    def search_leftovers(self):
        if not self.uninstalled_programs:
            return

        self.leftover_search_thread = LeftoverSearchThread(self.uninstalled_programs[0])
        self.leftover_search_thread.progress.connect(self.update_leftover_search_progress)
        self.leftover_search_thread.finished.connect(self.show_leftovers)
        self.leftover_search_thread.start()

    def update_leftover_search_progress(self, status):
        self.status_label.setText(status)

    def show_leftovers(self, leftovers):
        if leftovers['files'] or leftovers['registry']:
            dialog = QDialog(self)
            dialog.setWindowTitle("Leftover Files and Entries")
            dialog.setFixedSize(600, 500)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(16)
            layout.setContentsMargins(20, 20, 20, 20)
            
            title = QLabel("Found leftover items:")
            title.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #1A1A1A;
                }
            """)
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
                    QListWidget::item:last {
                        border-bottom: none;
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
                    QListWidget::item:last {
                        border-bottom: none;
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
                QPushButton:hover {
                    background-color: #0052CC;
                }
                QPushButton:pressed {
                    background-color: #004999;
                }
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
                QPushButton:hover {
                    background-color: #E5E5EA;
                }
                QPushButton:pressed {
                    background-color: #D1D1D6;
                }
            """)
            
            button_layout.addWidget(cancel_button)
            button_layout.addWidget(remove_button)
            layout.addLayout(button_layout)
            
            remove_button.clicked.connect(lambda: [self.remove_leftovers(leftovers), dialog.accept()])
            cancel_button.clicked.connect(dialog.reject)
            
            dialog.exec()
            
            self.uninstalled_programs.pop(0)
            if self.uninstalled_programs:
                self.search_leftovers()
            else:
                QTimer.singleShot(2000, self.refresh_program_list)
        else:
            QMessageBox.information(self, "Leftover Search", "No leftover files or registry entries found.")

    def remove_leftovers(self, leftovers):
        try:
            for file in leftovers['files']:
                try:
                    if os.path.isfile(file):
                        os.remove(file)
                    elif os.path.isdir(file):
                        shutil.rmtree(file)
                except Exception as e:
                    print(f"Error removing file {file}: {str(e)}")

            for reg_key in leftovers['registry']:
                try:
                    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, reg_key)
                except Exception as e:
                    print(f"Error removing registry key {reg_key}: {str(e)}")

            self.status_label.setText("Cleanup completed successfully")
            self.progress_bar.setValue(self.progress_bar.maximum())
            
            QTimer.singleShot(2000, lambda: [
                self.refresh_program_list(),
                self.status_label.setText(""),
                self.progress_bar.setValue(0)
            ])

            QMessageBox.information(self, "Cleanup Complete", "Leftover files and entries successfully removed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during cleanup: {str(e)}")

    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def handle_silent_fail(self, program):
        reply = QMessageBox.question(
            self,
            "Silent Uninstall Failed",
            f"Failed to perform silent uninstall for {program['name']}. Do you want to try regular uninstall?",
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
        dialog.setFixedSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        header_layout = QHBoxLayout()
        info_icon = QLabel()
        info_icon.setPixmap(QIcon.fromTheme("dialog-information").pixmap(32, 32))
        header_layout.addWidget(info_icon)
        
        title = QLabel(program['name'])
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #1A1A1A;
            }
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
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
            label_widget.setStyleSheet("""
                QLabel {
                    color: #6E6E73;
                    font-weight: bold;
                    min-width: 120px;
                }
            """)
            row.addWidget(label_widget)
            
            value_widget = QLabel(value or "Not available")
            if is_multiline:
                value_widget.setWordWrap(True)
                value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value_widget.setStyleSheet("""
                QLabel {
                    color: #1A1A1A;
                }
            """)
            row.addWidget(value_widget, 1)
            info_layout.addLayout(row)
        
        install_date = program.get('install_date', '')
        if install_date and len(install_date) == 8: 
            try:
                year = install_date[:4]
                month = install_date[4:6]
                day = install_date[6:]
                formatted_date = f"{day}/{month}/{year}"
            except:
                formatted_date = install_date
        else:
            formatted_date = install_date
        
        add_info_row("Publisher:", program.get('publisher', ''))
        add_info_row("Install Date:", formatted_date)
        add_info_row("Version:", program.get('version', ''))
        add_info_row("Architecture:", "64-bit" if "64" in program.get('name', '').lower() else "32-bit")
        add_info_row("Location:", program.get('install_location', ''), True)
        add_info_row("Uninstall Command:", program.get('uninstall_string', ''), True)
        
        if program.get('size'):
            add_info_row("Size:", f"{int(program['size']) / 1024 / 1024:.2f} MB")
        if program.get('url'):
            add_info_row("Website:", program.get('url', ''))
        if program.get('contact'):
            add_info_row("Contact:", program.get('contact', ''))
        
        layout.addWidget(info_container)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("OK")
        ok_button.setFixedSize(100, 36)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #0066FF;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #0052CC;
            }
            QPushButton:pressed {
                background-color: #004999;
            }
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
        dialog = DiskSpaceDialog(self.get_installed_programs(), self)
        dialog.exec()

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

class FilePreviewDialog(QDialog):
    def __init__(self, program, parent=None):
        super().__init__(parent)
        self.program = program
        self.setWindowTitle(f"Files Preview - {program['name']}")
        self.setFixedSize(700, 500)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        
        self.common_paths = [
            os.path.expandvars(path) for path in [
                r'%ProgramFiles%',
                r'%ProgramFiles(x86)%',
                r'%LocalAppData%',
                r'%AppData%',
                r'%UserProfile%\AppData\Local',
                r'%UserProfile%\AppData\LocalLow',
                r'%UserProfile%\AppData\Roaming'
            ]
        ]
        
        self.setup_ui()

    def find_program_files(self):
        files_info = []
        total_size = 0
        program_name = self.program['name'].lower()
        
        install_location = self.program.get('install_location', '')
        if install_location and os.path.exists(install_location):
            files_info.extend(self._scan_directory(install_location))

        search_terms = {
            program_name,
            program_name.replace(' ', ''),
            ''.join(word[0] for word in program_name.split())
        }
        
        for base_path in self.common_paths:
            if not os.path.exists(base_path):
                continue
                
            try:
                for root, dirs, files in os.walk(base_path):
                    if any(term in root.lower() for term in search_terms):
                        files_info.extend(self._scan_directory(root))
                    else:
                        files_info.extend(self._scan_files(root, files, search_terms))
            except (PermissionError, OSError):
                continue

        total_size = sum(size for _, size in files_info)
        return files_info, total_size

    def _scan_directory(self, path):
        results = []
        try:
            for root, _, files in os.walk(path):
                results.extend(self._scan_files(root, files))
        except (OSError, PermissionError):
            pass
        return results

    def _scan_files(self, root, files, search_terms=None):
        results = []
        for file in files:
            if search_terms and not any(term in file.lower() for term in search_terms):
                continue
            try:
                full_path = os.path.join(root, file)
                size = os.path.getsize(full_path)
                results.append((full_path, size))
            except (OSError, FileNotFoundError):
                continue
        return results

    def format_size(self, size_bytes):
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        for unit in units:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} {units[-1]}"

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Files that will be removed:")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1A1A1A;")
        layout.addWidget(title)
        
        list_container = QWidget()
        list_container.setStyleSheet("QWidget { background-color: #F5F5F7; border-radius: 12px; }")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(12, 12, 12, 12)
        
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #E5E5EA;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #FFFFFF;
            }
        """)
        
        files_info, total_size = self.find_program_files()
        
        if not files_info:
            no_files_label = QLabel("No files found for this program")
            no_files_label.setStyleSheet("color: #666; padding: 20px;")
            no_files_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            list_layout.addWidget(no_files_label)
        else:
            files_info.sort(key=lambda x: x[1], reverse=True)
            for file_path, size in files_info:
                item = QListWidgetItem(f"{file_path} ({self.format_size(size)})")
                self.file_list.addItem(item)
            list_layout.addWidget(self.file_list)
        
        layout.addWidget(list_container)
        
        info_container = QWidget()
        info_container.setStyleSheet("""
            QWidget {
                background-color: #F5F5F7;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel { color: #1A1A1A; }
        """)
        
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(12, 8, 12, 8)
        
        info_layout.addWidget(QLabel(f"Total files: {len(files_info)}"))
        info_layout.addStretch()
        info_layout.addWidget(QLabel(f"Total size: {self.format_size(total_size)}"))
        
        layout.addWidget(info_container)
        
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.setFixedWidth(120)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #0066FF;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052CC;
            }
        """)
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

class DiskSpaceDialog(QDialog):
    def __init__(self, programs, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.programs = programs
        self.setWindowTitle("Disk Space Usage")
        self.setFixedSize(600, 500)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Disk Space Usage Analysis")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1A1A1A;
        """)
        layout.addWidget(title)
        
        total_size = sum(float(p.get('size', 0) or 0) for p in self.programs)
        stats_container = QWidget()
        stats_container.setStyleSheet("""
            QWidget {
                background-color: #F5F5F7;
                border-radius: 12px;
                padding: 16px;
            }
            QLabel {
                color: #1A1A1A;
            }
        """)
        stats_layout = QVBoxLayout(stats_container)
        
        total_label = QLabel(f"Total Size: {total_size/1024:.2f} GB")
        total_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        stats_layout.addWidget(total_label)
        
        program_count = QLabel(f"Total Programs: {len(self.programs)}")
        stats_layout.addWidget(program_count)
        
        layout.addWidget(stats_container)
        
        top_group = QGroupBox("Top 10 Largest Programs")
        top_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: #0066FF;
            }
        """)
        top_layout = QVBoxLayout(top_group)
        
        top_list = QListWidget()
        top_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #E5E5EA;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        
        sorted_programs = sorted(self.programs, 
                               key=lambda x: float(x.get('size', 0) or 0),
                               reverse=True)[:10]
        
        for program in sorted_programs:
            size = float(program.get('size', 0) or 0)
            if size > 0:
                item = QListWidgetItem()
                item.setText(f"{program['name']} - {size/1024:.2f} MB")
                top_list.addItem(item)
        
        top_layout.addWidget(top_list)
        layout.addWidget(top_group)
        
        publisher_group = QGroupBox("Usage by Publisher")
        publisher_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: #0066FF;
            }
        """)
        publisher_layout = QVBoxLayout(publisher_group)
        
        # Создаем список издателей
        publisher_list = QListWidget()
        publisher_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #E5E5EA;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        
        publisher_sizes = {}
        for program in self.programs:
            publisher = program.get('publisher', 'Unknown')
            size = float(program.get('size', 0) or 0)
            if publisher in publisher_sizes:
                publisher_sizes[publisher] += size
            else:
                publisher_sizes[publisher] = size
        
        top_publishers = sorted(publisher_sizes.items(),
                              key=lambda x: x[1],
                              reverse=True)[:10]
        
        for publisher, size in top_publishers:
            item = QListWidgetItem()
            item.setText(f"{publisher} - {size/1024:.2f} MB")
            publisher_list.addItem(item)
        
        publisher_layout.addWidget(publisher_list)
        layout.addWidget(publisher_group)
        
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #0066FF;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052CC;
            }
            QPushButton:pressed {
                background-color: #004999;
            }
        """)
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UninstallerTool()
    window.show()
    sys.exit(app.exec())
