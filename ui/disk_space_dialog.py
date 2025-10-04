from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QGroupBox
from PyQt6.QtCore import Qt

class DiskSpaceDialog(QDialog):
    def __init__(self, programs, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.programs = programs
        self.setWindowTitle("Disk Space Usage")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Disk Space Usage Analysis")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1A1A1A;")
        layout.addWidget(title)
        
        total_size_kb = sum(float(p.get('size', 0) or 0) for p in self.programs)
        total_size_mb = total_size_kb / 1024
        total_size_gb = total_size_mb / 1024
        
        stats_container = QLabel()
        stats_container.setStyleSheet("""
            QLabel {
                background-color: #F5F5F7;
                border-radius: 12px;
                padding: 16px;
                color: #1A1A1A;
            }
        """)
        
        if total_size_gb >= 1:
            size_text = f"{total_size_gb:.2f} GB"
        else:
            size_text = f"{total_size_mb:.2f} MB"
            
        stats_container.setText(f"Total Size: {size_text}\nTotal Programs: {len(self.programs)}")
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
        """)
        
        sorted_programs = sorted(self.programs, key=lambda x: float(x.get('size', 0) or 0), reverse=True)[:10]
        
        for program in sorted_programs:
            size_kb = float(program.get('size', 0) or 0)
            if size_kb > 0:
                size_mb = size_kb / 1024
                item = QListWidgetItem()
                if size_mb >= 1024:
                    size_gb = size_mb / 1024
                    item.setText(f"{program['name']} - {size_gb:.2f} GB")
                else:
                    item.setText(f"{program['name']} - {size_mb:.2f} MB")
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
        """)
        
        publisher_sizes = {}
        for program in self.programs:
            publisher = program.get('publisher', 'Unknown')
            size = float(program.get('size', 0) or 0)
            if publisher in publisher_sizes:
                publisher_sizes[publisher] += size
            else:
                publisher_sizes[publisher] = size
        
        top_publishers = sorted(publisher_sizes.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for publisher, size_kb in top_publishers:
            size_mb = size_kb / 1024
            item = QListWidgetItem()
            if size_mb >= 1024:
                size_gb = size_mb / 1024
                item.setText(f"{publisher} - {size_gb:.2f} GB")
            else:
                item.setText(f"{publisher} - {size_mb:.2f} MB")
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
        """)
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
