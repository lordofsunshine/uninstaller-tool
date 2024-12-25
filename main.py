import sys
import winreg
import subprocess
import os
import psutil
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QCheckBox, 
                             QProgressBar, QLabel, QMessageBox, QListWidgetItem,
                             QLineEdit, QScrollArea, QSizePolicy, QMenu, QFrame)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal, QTimer, QPoint, QParallelAnimationGroup
from PyQt6.QtGui import QColor, QPalette, QIcon, QFont, QPixmap, QPainter, QAction
from PyQt6.QtSvg import QSvgRenderer

REFRESH_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3"/>
</svg>
"""

UNINSTALL_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2M10 11v6M14 11v6"/>
</svg>
"""

COLORS = {
    'primary': '#4a90e2',
    'secondary': '#f5a623',
    'success': '#2ecc71',
    'error': '#e74c3c',
    'background': '#f8f8f8',
    'text': '#333333',
    'border': '#e0e0e0'
}

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
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.checkbox = QCheckBox(self.program['name'])
        self.checkbox.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.checkbox)
        
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.status_label)
        
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border-radius: 5px;
                margin: 2px;
                padding: 5px;
            }}
            QCheckBox {{
                spacing: 10px;
                color: {COLORS['text']};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
        """)

    def set_status(self, status):
        if status == "running":
            self.status_label.setText("Uninstalling...")
            self.status_label.setStyleSheet(f"color: {COLORS['secondary']}; font-weight: bold;")
        elif status == "success":
            self.status_label.setText("Uninstalled")
            self.status_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        elif status == "error":
            self.status_label.setText("Error")
            self.status_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: bold;")
        else:
            self.status_label.setText("")

class UninstallerTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Uninstaller Tool")
        self.setGeometry(100, 100, 800, 600)
        self.setup_ui()
        self.uninstalled_programs = []

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search programs...")
        self.search_input.textChanged.connect(self.filter_programs)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.program_list_widget = QWidget()
        self.program_list_layout = QVBoxLayout(self.program_list_widget)
        self.program_list_layout.setSpacing(5)
        self.program_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.program_list_widget)
        main_layout.addWidget(self.scroll_area)

        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh List")
        self.refresh_button.clicked.connect(self.refresh_program_list)
        self.refresh_button.setIcon(QIcon(self.create_svg_icon(REFRESH_ICON)))
        
        self.uninstall_button = QPushButton("Uninstall Selected")
        self.uninstall_button.clicked.connect(self.uninstall_selected)
        self.uninstall_button.setIcon(QIcon(self.create_svg_icon(UNINSTALL_ICON)))
        
        self.silent_checkbox = QCheckBox("Silent Uninstall")
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.uninstall_button)
        button_layout.addWidget(self.silent_checkbox)
        main_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        main_layout.addWidget(self.status_label)

        self.apply_modern_style()
        self.refresh_program_list()

    def apply_modern_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QWidget#program_list_widget {{
                background-color: transparent;
            }}
            QLineEdit {{
                padding: 8px;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {QColor(COLORS['primary']).darker(110).name()};
            }}
            QPushButton:pressed {{
                background-color: {QColor(COLORS['primary']).darker(120).name()};
            }}
            QCheckBox {{
                spacing: 5px;
                font-size: 14px;
            }}
            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: 5px;
                text-align: center;
                font-size: 12px;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 5px;
            }}
            QLabel {{
                font-size: 14px;
                color: {COLORS['text']};
            }}
        """)

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
        animation_group = QParallelAnimationGroup(self)
        
        for i in range(self.program_list_layout.count()):
            widget = self.program_list_layout.itemAt(i).widget()
            widget.setMaximumHeight(0)
            widget.show()
            
            animation = QPropertyAnimation(widget, b"maximumHeight", self)
            animation.setDuration(150)
            animation.setStartValue(0)
            animation.setEndValue(40)
            animation.setEasingCurve(QEasingCurve.Type.OutQuad)
            animation.finished.connect(lambda w=widget: setattr(w, 'setMaximumHeight', 16777215))
            animation_group.addAnimation(animation)
        
        animation_group.start()

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
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0].strip()
                            uninstall_string = winreg.QueryValueEx(subkey, "UninstallString")[0].strip()
                            
                            if not display_name or not uninstall_string:
                                continue

                            program_info = {
                                'name': display_name,
                                'uninstall_string': uninstall_string,
                                'install_location': '',
                                'publisher': '',
                                'install_date': ''
                            }

                            try:
                                program_info['install_location'] = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            except: pass

                            try:
                                program_info['publisher'] = winreg.QueryValueEx(subkey, "Publisher")[0]
                            except: pass

                            try:
                                program_info['install_date'] = winreg.QueryValueEx(subkey, "InstallDate")[0]
                            except: pass

                            if display_name not in programs:
                                programs[display_name] = program_info

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
            message = "Found leftover files and registry entries:\n\n"
            if leftovers['files']:
                message += "Files:\n" + "\n".join(leftovers['files'][:10])
                if len(leftovers['files']) > 10:
                    message += f"\n... and {len(leftovers['files']) - 10} more files"
                message += "\n\n"
            if leftovers['registry']:
                message += "Registry entries:\n" + "\n".join(leftovers['registry'][:10])
                if len(leftovers['registry']) > 10:
                    message += f"\n... and {len(leftovers['registry']) - 10} more entries"
            
            reply = QMessageBox.question(
                self,
                "Leftover Files and Entries",
                message + "\n\nDo you want to remove these leftovers?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.remove_leftovers(leftovers)
        else:
            QMessageBox.information(self, "Leftover Search", "No leftover files or registry entries found.")

        self.uninstalled_programs.pop(0)
        if self.uninstalled_programs:
            self.search_leftovers()
        else:
            QTimer.singleShot(2000, self.refresh_program_list)

    def remove_leftovers(self, leftovers):
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

        QMessageBox.information(self, "Leftover Removal", "Leftover files and entries successfully removed.")

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
        
        context_menu.exec(self.mapToGlobal(pos))

    def show_program_info(self, program):
        info = f"""
Name: {program['name']}
Publisher: {program['publisher']}
Install Date: {program['install_date']}
Location: {program['install_location']}
Uninstall Command: {program['uninstall_string']}
        """
        QMessageBox.information(self, "Program Information", info)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UninstallerTool()
    window.show()
    sys.exit(app.exec())
