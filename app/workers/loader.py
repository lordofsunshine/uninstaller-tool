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
            programs = get_installed_programs()
            # store apps are invisible in registry, merge them in
            try:
                from app.core.store import get_store_apps
                if not self.isInterruptionRequested():
                    programs = list(programs) + get_store_apps()
            except (OSError, ValueError):
                pass
            self.loaded.emit(programs)
        except OSError as exc:
            self.failed.emit(str(exc))
