from PySide6.QtCore import QThread, Signal

from app.core.registry import get_installed_programs


class LoaderThread(QThread):
    # reads uninstall keys in background so ui stays responsive
    loaded = Signal(list)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            self.loaded.emit(get_installed_programs())
        except OSError as exc:
            self.failed.emit(str(exc))
