from __future__ import annotations

import contextlib
import ctypes
import sys
import traceback

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.config import APP_ID, APP_NAME, APP_VERSION
from app.logging_setup import get_logger, setup_logging
from app.paths import log_dir
from app.ui.main_window import UninstallerTool
from app.utils import resource_path, set_dark_title_bar

LOGGER = get_logger("app")


class TitleBarTheme(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Show and isinstance(obj, QWidget):
            with contextlib.suppress(AttributeError, RuntimeError, OSError):
                if obj.isWindow():
                    set_dark_title_bar(obj, getattr(self.window, "is_dark", False))
        return False


def _install_exception_hook() -> None:
    def handle(exc_type, exc_value, exc_traceback):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        LOGGER.critical("Unhandled exception\n%s", text)
        if QApplication.instance() is not None:
            with contextlib.suppress(RuntimeError, OSError):
                QMessageBox.critical(
                    None,
                    "Unexpected error",
                    "The application hit an unexpected error.\n"
                    f"Details were written to the log file:\n{log_dir() / 'app.log'}",
                )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle


def main() -> int:
    logger = setup_logging()
    _install_exception_hook()
    logger.info("Starting %s %s", APP_NAME, APP_VERSION)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)
    app.setWindowIcon(QIcon(resource_path("assets/app_icon.ico")))
    with contextlib.suppress(AttributeError, OSError):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"{APP_ID}.{APP_VERSION}"
        )

    window = UninstallerTool()
    app.installEventFilter(TitleBarTheme(window))
    window.show()
    with contextlib.suppress(AttributeError, RuntimeError):
        app.styleHints().colorSchemeChanged.connect(
            lambda *_: window.on_system_theme_changed()
        )
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
