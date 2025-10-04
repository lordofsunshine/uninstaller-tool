from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
from core.file_operations import find_program_files
from utils.helpers import format_size

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
        
        files_info, total_size = find_program_files(self.program)
        
        if not files_info:
            no_files_label = QLabel("No files found for this program")
            no_files_label.setStyleSheet("color: #666; padding: 20px;")
            no_files_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            list_layout.addWidget(no_files_label)
        else:
            files_info.sort(key=lambda x: x[1], reverse=True)
            for file_path, size in files_info:
                item = QListWidgetItem(f"{file_path} ({format_size(size)})")
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
        info_layout.addWidget(QLabel(f"Total size: {format_size(total_size)}"))
        
        layout.addWidget(info_container)
        
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.setMinimumWidth(120)
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
