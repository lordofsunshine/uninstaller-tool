from PyQt6.QtCore import QThread, pyqtSignal
from core.file_operations import search_leftover_files

class LeftoverSearchThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, program):
        super().__init__()
        self.program = program

    def run(self):
        try:
            self.progress.emit("Searching for leftover files and registry entries...")
            leftovers = search_leftover_files(self.program['name'])
            self.finished.emit(leftovers)
        except Exception as e:
            self.error.emit(f"Error searching leftovers: {str(e)}")
            self.finished.emit({'files': [], 'registry': []})
