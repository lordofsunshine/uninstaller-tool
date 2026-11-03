from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings

from app.paths import settings_path


class AppSettings:
    def __init__(self):
        self._settings = QSettings(str(settings_path()), QSettings.Format.IniFormat)

    def geometry(self) -> QByteArray | None:
        value = self._settings.value("window/geometry")
        return value if isinstance(value, QByteArray) else None

    def set_geometry(self, value: QByteArray) -> None:
        self._settings.setValue("window/geometry", value)

    def splitter_state(self) -> QByteArray | None:
        value = self._settings.value("window/splitter")
        return value if isinstance(value, QByteArray) else None

    def set_splitter_state(self, value: QByteArray) -> None:
        self._settings.setValue("window/splitter", value)

    def sort_mode(self) -> int:
        try:
            return max(0, int(self._settings.value("list/sort", 0)))
        except (TypeError, ValueError):
            return 0

    def set_sort_mode(self, value: int) -> None:
        self._settings.setValue("list/sort", int(value))

    def silent_mode(self) -> bool:
        value = self._settings.value("uninstall/silent", False)
        if isinstance(value, str):
            return value.strip().casefold() in {"1", "true", "yes"}
        return bool(value)

    def set_silent_mode(self, value: bool) -> None:
        self._settings.setValue("uninstall/silent", bool(value))

    def sync(self) -> None:
        self._settings.sync()
