import sys
import ctypes
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import UninstallerTool

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return True
    except:
        return False

if __name__ == "__main__":
    if not is_admin():
        app = QApplication(sys.argv)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Administrator Required")
        msg.setText("This application requires administrator privileges to uninstall programs.")
        msg.setInformativeText("Do you want to restart as administrator?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            if run_as_admin():
                sys.exit(0)
            else:
                QMessageBox.critical(None, "Error", "Failed to restart as administrator.")
                sys.exit(1)
        else:
            sys.exit(0)
    
    app = QApplication(sys.argv)
    window = UninstallerTool()
    window.show()
    sys.exit(app.exec())
