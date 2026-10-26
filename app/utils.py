from __future__ import annotations

import ctypes
import os
import re
import sys
from datetime import datetime
from functools import lru_cache

from app.paths import resource_path

_ICON_EXTENSIONS = {".ico"}
_ICON_CACHE: dict[tuple[str, int, int, int], object] = {}
_ICON_CACHE_LIMIT = 512
_ICON_REFERENCE = re.compile(r"^(.*?)(?:,\s*(-?\d+))?$", re.DOTALL)
_HICON = ctypes.c_void_p
_UINT = ctypes.c_uint32
_DWORD = ctypes.c_uint32
_LONG = ctypes.c_int32
_WORD = ctypes.c_uint16
_USER32 = None
_GDI32 = None
_ICON_PROVIDER = None


def _windows_api():
    global _USER32, _GDI32
    if _USER32 is not None:
        return _USER32, _GDI32

    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    user32.DrawIconEx.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HICON,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
        wintypes.HBRUSH,
        wintypes.UINT,
    ]
    user32.DrawIconEx.restype = wintypes.BOOL
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    user32.DestroyIcon.restype = wintypes.BOOL
    user32.PrivateExtractIconsW.argtypes = [
        wintypes.LPCWSTR,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(wintypes.HICON),
        ctypes.POINTER(wintypes.UINT),
        wintypes.UINT,
        wintypes.UINT,
    ]
    user32.PrivateExtractIconsW.restype = wintypes.UINT

    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = [
        wintypes.HDC,
        ctypes.c_void_p,
        wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p),
        wintypes.HANDLE,
        wintypes.DWORD,
    ]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL

    _USER32, _GDI32 = user32, gdi32
    return user32, gdi32


def create_svg_icon(svg: str, size: int = 24):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(bytearray(svg, encoding="utf-8"))
    ratio = 1.0
    screen = QGuiApplication.primaryScreen()
    if screen is not None:
        ratio = max(1.0, float(screen.devicePixelRatio()))
    pixels = max(1, round(size * ratio))
    pixmap = QPixmap(pixels, pixels)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def set_dark_title_bar(widget, dark: bool) -> None:
    if sys.platform != "win32":
        return
    try:
        handle = int(widget.winId())
        value = ctypes.c_int(1 if dark else 0)
        for attribute in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                handle, attribute, ctypes.byref(value), ctypes.sizeof(value)
            ) == 0:
                break
    except (AttributeError, OSError, RuntimeError):
        pass


def split_icon_reference(raw: str) -> tuple[str, int]:
    text = os.path.expandvars(str(raw or "")).strip()
    if not text:
        return "", 0
    if text.startswith('"'):
        end = text.find('"', 1)
        if end == -1:
            return text.strip('"'), 0
        path = text[1:end]
        rest = text[end + 1 :].strip()
        match = re.fullmatch(r",\s*(-?\d+)", rest)
        return path, int(match.group(1)) if match else 0
    match = _ICON_REFERENCE.match(text)
    if not match:
        return text, 0
    return match.group(1).strip().strip('"'), int(match.group(2) or 0)


class _BitmapInfoHeader(ctypes.Structure):
    _fields_ = [
        ("biSize", _DWORD),
        ("biWidth", _LONG),
        ("biHeight", _LONG),
        ("biPlanes", _WORD),
        ("biBitCount", _WORD),
        ("biCompression", _DWORD),
        ("biSizeImage", _DWORD),
        ("biXPelsPerMeter", _LONG),
        ("biYPelsPerMeter", _LONG),
        ("biClrUsed", _DWORD),
        ("biClrImportant", _DWORD),
    ]


class _BitmapInfo(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", _BitmapInfoHeader),
        ("bmiColors", ctypes.c_ubyte * 12),
    ]


def _hicon_to_pixmap(handle: int, size: int):
    from PySide6.QtGui import QImage, QPixmap

    user32, gdi32 = _windows_api()

    header = _BitmapInfoHeader()
    header.biSize = ctypes.sizeof(_BitmapInfoHeader)
    header.biWidth = size
    header.biHeight = -size
    header.biPlanes = 1
    header.biBitCount = 32
    header.biCompression = 0
    info = _BitmapInfo()
    info.bmiHeader = header

    screen = user32.GetDC(None)
    if not screen:
        return None
    memory = gdi32.CreateCompatibleDC(screen)
    if not memory:
        user32.ReleaseDC(None, screen)
        return None

    bits = ctypes.c_void_p()
    bitmap = gdi32.CreateDIBSection(
        memory, ctypes.byref(info), 0, ctypes.byref(bits), None, 0
    )
    if not bitmap:
        gdi32.DeleteDC(memory)
        user32.ReleaseDC(None, screen)
        return None

    previous = gdi32.SelectObject(memory, bitmap)
    try:
        if not user32.DrawIconEx(memory, 0, 0, handle, size, size, 0, None, 3):
            return None
        buffer = ctypes.string_at(bits, size * size * 4)
        if not any(buffer[3::4]):
            return None
        image = QImage(
            buffer, size, size, size * 4, QImage.Format.Format_ARGB32_Premultiplied
        ).copy()
        return QPixmap.fromImage(image)
    finally:
        gdi32.SelectObject(memory, previous)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory)
        user32.ReleaseDC(None, screen)


def _extract_hicon(path: str, index: int, size: int):
    if sys.platform != "win32":
        return None
    user32, _ = _windows_api()
    icon = _HICON()
    icon_id = _UINT()
    count = user32.PrivateExtractIconsW(
        path,
        index,
        size,
        size,
        ctypes.byref(icon),
        ctypes.byref(icon_id),
        1,
        0,
    )
    if not count or not icon.value:
        return None
    try:
        return _hicon_to_pixmap(icon.value, size)
    finally:
        user32.DestroyIcon(icon)


def _icon_cache_key(path: str, index: int, size: int) -> tuple[str, int, int, int] | None:
    try:
        modified = os.stat(path).st_mtime_ns
    except OSError:
        return None
    return (os.path.normcase(path), index, modified, size)


def _shell_icon(path: str):
    global _ICON_PROVIDER
    from PySide6.QtCore import QFileInfo
    from PySide6.QtWidgets import QFileIconProvider

    if _ICON_PROVIDER is None:
        _ICON_PROVIDER = QFileIconProvider()
    icon = _ICON_PROVIDER.icon(QFileInfo(path))
    return None if icon.isNull() else icon


def _cached_icon(path: str, index: int):
    from PySide6.QtGui import QIcon

    key = _icon_cache_key(path, index, 0)
    if key is None:
        return None
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached

    icon = QIcon()
    for size in (32, 48, 64, 96, 128):
        pixmap = _extract_hicon(path, index, size)
        if pixmap is not None and not pixmap.isNull():
            icon.addPixmap(pixmap)
    if icon.isNull():
        icon = _shell_icon(path) or QIcon(path)
    result = None if icon.isNull() else icon
    if len(_ICON_CACHE) >= _ICON_CACHE_LIMIT:
        _ICON_CACHE.clear()
    _ICON_CACHE[key] = result
    return result


def program_icon(program):
    from PySide6.QtGui import QIcon

    raw = program if isinstance(program, str) else str(getattr(program, "icon", "") or "")
    path, index = split_icon_reference(raw)
    if not path or not os.path.isfile(path):
        return None

    key = _icon_cache_key(path, index, 0)
    if key is not None and key in _ICON_CACHE:
        return _ICON_CACHE[key]

    extension = os.path.splitext(path)[1].casefold()
    if extension in _ICON_EXTENSIONS:
        icon = QIcon(path)
        result = None if icon.isNull() else icon
    else:
        result = _cached_icon(path, index)

    if key is not None:
        if len(_ICON_CACHE) >= _ICON_CACHE_LIMIT:
            _ICON_CACHE.clear()
        _ICON_CACHE[key] = result
    return result


@lru_cache(maxsize=2048)
def _parse_date(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    if re.fullmatch(r"\d{8}", text):
        try:
            return datetime.strptime(text, "%Y%m%d").date().isoformat()
        except ValueError:
            return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return ""
    return text


def format_install_date(raw) -> str:
    return _parse_date(str(raw or ""))


def format_size(size_bytes) -> str:
    try:
        value = max(0.0, float(size_bytes or 0))
    except (TypeError, ValueError, OverflowError):
        value = 0.0
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    for unit in units[:-1]:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} {units[-1]}"


__all__ = [
    "create_svg_icon",
    "format_install_date",
    "format_size",
    "program_icon",
    "resource_path",
    "set_dark_title_bar",
    "split_icon_reference",
]
