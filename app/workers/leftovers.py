from PySide6.QtCore import QThread, Signal

from app.core.files import search_leftover_files


class LeftoversThread(QThread):
    # don't name a custom signal "finished" - it shadows the qthread one
    # and crashes the app when run() exits
    done = Signal(dict)

    def __init__(self, program, parent=None):
        super().__init__(parent)
        self.program = program

    def run(self):
        try:
            self.done.emit(search_leftover_files(
                self.program.get('name', ''), self.program.get('publisher', ''),
                self.program.get('package_family', '')))
        except (OSError, ValueError):
            self.done.emit({'files': [], 'registry': []})
