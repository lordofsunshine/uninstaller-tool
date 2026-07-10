import ctypes
import os
import subprocess
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from config.version import APP_ID, APP_NAME, APP_VERSION
from ui.main_window import UninstallerTool
from utils.helpers import resource_path


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def run_as_admin():
    if getattr(sys, "frozen", False):
        executable = sys.executable
        arguments = sys.argv[1:]
    else:
        executable = sys.executable
        arguments = [os.path.abspath(sys.argv[0]), *sys.argv[1:]]
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, subprocess.list2cmdline(arguments), None, 1
        )
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
            None,
            "Administrator rights required",
            "Administrator rights are required to uninstall programs and clean up leftovers.\n\nRestart as administrator?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return 0
        if run_as_admin():
            return 0
        QMessageBox.critical(None, "Error", "Windows could not restart the application as administrator.")
        return 1

    window = UninstallerTool()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
