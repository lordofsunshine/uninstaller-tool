from PyQt6.QtWidgets import QFrame, QHBoxLayout, QCheckBox, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from config.constants import COLORS

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
