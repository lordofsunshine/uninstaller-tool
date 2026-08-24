import ctypes
import os
import subprocess
import sys

from PySide6.QtCore import QObject, QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.config import APP_ID, APP_NAME, APP_VERSION
from app.theme.colors import system_palette
from app.ui.main_window import UninstallerTool
from app.utils import resource_path, set_dark_title_bar


class TitleBarTheme(QObject):
    # paints every top-level window title bar dark when theme is dark
    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show and isinstance(obj, QWidget):
            try:
                if hasattr(obj, 'isWindow') and obj.isWindow() and hasattr(obj, 'winId'):
                    set_dark_title_bar(obj, getattr(self.window, 'is_dark', False))
            except (AttributeError, RuntimeError, OSError):
                pass
        return False


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def run_as_admin():
    # relaunch self with elevation via shell
    if getattr(sys, "frozen", False):
        exe, args = sys.executable, sys.argv[1:]
    else:
        exe, args = sys.executable, [os.path.abspath(sys.argv[0]), *sys.argv[1:]]
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, subprocess.list2cmdline(args), None, 1)
    except (AttributeError, OSError):
        return False
    return result > 32


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon(resource_path("assets/app_icon.ico")))
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{APP_ID}.{APP_VERSION}")
    except (AttributeError, OSError):
        pass

    if not is_admin():
        answer = QMessageBox.question(
            None, "Administrator rights required",
            "Administrator rights are required to uninstall programs and clean up leftovers.\n\nRestart as administrator?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if answer != QMessageBox.StandardButton.Yes:
            return 0
        if run_as_admin():
            return 0
        QMessageBox.critical(None, "Error", "Windows could not restart the application as administrator.")
        return 1

    # theme just follows whatever windows is using
    window = UninstallerTool()
    window.apply_theme(system_palette())
    # filter must be installed before show, or the main window misses it
    app.installEventFilter(TitleBarTheme(window))
    window.show()
    try:
        app.styleHints().colorSchemeChanged.connect(lambda *_: window.on_system_theme_changed())
    except (AttributeError, RuntimeError):
        pass
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
