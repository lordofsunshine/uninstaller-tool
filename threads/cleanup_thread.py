from PyQt6.QtCore import QThread, pyqtSignal

from core.file_operations import remove_leftovers


class CleanupThread(QThread):
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, leftovers, parent=None):
        super().__init__(parent)
        self.leftovers = leftovers

    def run(self):
        try:
            self.completed.emit(remove_leftovers(self.leftovers))
        except OSError as exc:
            self.failed.emit(str(exc))
