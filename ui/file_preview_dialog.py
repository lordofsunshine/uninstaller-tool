from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core.file_operations import find_program_files
from utils.helpers import format_size


class FileScanThread(QThread):
    scanned = pyqtSignal(list, int)
    failed = pyqtSignal(str)

    def __init__(self, program, parent=None):
        super().__init__(parent)
        self.program = program

    def run(self):
        try:
            files, total_size = find_program_files(self.program, self.isInterruptionRequested)
            self.scanned.emit(files, total_size)
        except OSError as exc:
            self.failed.emit(str(exc))

class FilePreviewDialog(QDialog):
    def __init__(self, program, parent=None):
        super().__init__(parent)
        self.program = program
        self.setWindowTitle(f"Files Preview - {program['name']}")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setup_ui()

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
        
        self.loading_label = QLabel("Scanning program files...")
        self.loading_label.setStyleSheet("color: #666; padding: 20px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        list_layout.addWidget(self.loading_label)
        list_layout.addWidget(self.file_list)
        self.file_list.hide()
        
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
        
        self.file_count_label = QLabel("Total files: —")
        info_layout.addWidget(self.file_count_label)
        info_layout.addStretch()
        self.total_size_label = QLabel("Total size: —")
        info_layout.addWidget(self.total_size_label)
        
        layout.addWidget(info_container)
        
        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Close")
        self.close_button.setMinimumWidth(120)
        self.close_button.setEnabled(False)
        self.close_button.setStyleSheet("""
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
        self.close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        self.scan_thread = FileScanThread(self.program, self)
        self.scan_thread.scanned.connect(self.show_scan_results)
        self.scan_thread.failed.connect(self.show_scan_error)
        self.scan_thread.start()

    def show_scan_results(self, files_info, total_size):
        self.loading_label.hide()
        if files_info:
            self.file_list.show()
            for file_path, size in sorted(files_info, key=lambda item: item[1], reverse=True):
                self.file_list.addItem(QListWidgetItem(f"{file_path} ({format_size(size)})"))
        else:
            self.loading_label.setText("No program files could be identified safely")
            self.loading_label.show()
        self.file_count_label.setText(f"Total files: {len(files_info)}")
        self.total_size_label.setText(f"Total size: {format_size(total_size)}")
        self.close_button.setEnabled(True)

    def show_scan_error(self, message):
        self.loading_label.setText(f"Could not scan files: {message}")
        self.close_button.setEnabled(True)

    def closeEvent(self, event):
        if self.scan_thread.isRunning():
            self.scan_thread.requestInterruption()
            if not self.scan_thread.wait(2000):
                event.ignore()
                return
        super().closeEvent(event)
