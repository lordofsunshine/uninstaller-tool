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
