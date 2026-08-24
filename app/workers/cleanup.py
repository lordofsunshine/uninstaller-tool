from PySide6.QtCore import QThread, Signal

from app.core.files import remove_leftovers


class CleanupThread(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, leftovers, parent=None):
        super().__init__(parent)
        self.leftovers = leftovers

    def run(self):
        try:
            self.done.emit(remove_leftovers(self.leftovers))
        except OSError as exc:
            self.failed.emit(str(exc))
