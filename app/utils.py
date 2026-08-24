import ctypes
import os
import re
import sys


def create_svg_icon(svg_str):
    from PySide6.QtGui import QPixmap, QPainter
    from PySide6.QtCore import Qt
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(bytearray(svg_str, encoding='utf-8'))
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def set_dark_title_bar(widget, dark):
    # windows title bar stays white otherwise, which hurts eyes in dark theme
    if sys.platform != 'win32':
        return
    try:
        hwnd = int(widget.winId())
        value = ctypes.c_int(1 if dark else 0)
        # attribute 20 works on win10 20h1+, 19 on older builds
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), 4) == 0:
                break
    except (AttributeError, OSError, RuntimeError):
        pass


def program_icon(program):
    # pull the icon from the exe/dll listed in registry, if it exists
    from PySide6.QtGui import QIcon

    raw = str(program.get('icon') or '').strip()
    if not raw:
        return None
    path = re.sub(r",\s*-?\d+$", "", raw).strip().strip('"')
    if not path or not os.path.isfile(path):
        return None
    icon = QIcon(path)
    return None if icon.isNull() else icon


def resource_path(rel):
    # works in dev and inside pyinstaller bundle
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


def format_size(size_bytes):
    try:
        size_bytes = max(0.0, float(size_bytes or 0))
    except (TypeError, ValueError, OverflowError):
        size_bytes = 0.0
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def format_install_date(raw):
    # registry stores dates as yyyymmdd
    if raw and len(raw) == 8:
        try:
            return f"{raw[6:]}/{raw[4:6]}/{raw[:4]}"
        except (TypeError, ValueError):
            return raw
    return raw
