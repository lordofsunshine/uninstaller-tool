from PyQt6.QtGui import QPixmap, QPainter, QIcon
from PyQt6.QtCore import Qt
from PyQt6.QtSvg import QSvgRenderer

def create_svg_icon(svg_str):
    renderer = QSvgRenderer(bytearray(svg_str, encoding='utf-8'))
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap

def format_size(size_bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    for unit in units:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} {units[-1]}"

def format_install_date(install_date):
    if install_date and len(install_date) == 8:
        try:
            year = install_date[:4]
            month = install_date[4:6]
            day = install_date[6:]
            return f"{day}/{month}/{year}"
        except:
            return install_date
    return install_date
