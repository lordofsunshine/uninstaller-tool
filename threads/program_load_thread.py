from PyQt6.QtCore import QThread, pyqtSignal

from core.registry import get_installed_programs


class ProgramLoadThread(QThread):
    loaded = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.loaded.emit(get_installed_programs())
        except OSError as exc:
            self.error.emit(str(exc))
