import subprocess

import psutil
from PyQt6.QtCore import QThread, pyqtSignal

from core.uninstall_commands import (
    MSI_SUCCESS_CODES,
    build_uninstall_command,
    command_exists,
    is_msi_command,
)


class UninstallThread(QThread):
    progress = pyqtSignal(int, str, str, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, programs, silent):
        super().__init__()
        self.programs = programs
        self.silent = silent
        self.current_process = None
        self.uninstalled_programs = []

    def run(self):
        for index, program in enumerate(self.programs):
            name = program.get("name", "Unknown program")
            self.progress.emit(index, f"Uninstalling {name}...", "running", name)
            try:
                command = program.get("quiet_uninstall_string") if self.silent else ""
                args = build_uninstall_command(command or program.get("uninstall_string"), self.silent)
                if not command_exists(args):
                    self.progress.emit(index + 1, f"Invalid uninstall command for {name}", "error", name)
                    continue

                success = self._run(args, timeout=300 if self.silent else None)
                if not success and self.silent:
                    self.progress.emit(index, f"Silent mode failed for {name}; opening the uninstaller...", "running", name)
                    args = build_uninstall_command(program.get("uninstall_string"), False)
                    success = self._run(args)

                if success:
                    self.uninstalled_programs.append(program)
                    self.progress.emit(index + 1, f"{name} was uninstalled", "success", name)
                else:
                    self.progress.emit(index + 1, f"Could not uninstall {name}", "error", name)
            except subprocess.TimeoutExpired:
                self._terminate_process_tree()
                self.progress.emit(index + 1, f"Uninstall timed out for {name}", "error", name)
            except (OSError, ValueError) as exc:
                self.error.emit(f"Could not start the uninstaller for {name}: {exc}")
                self.progress.emit(index + 1, f"Could not uninstall {name}", "error", name)
        self.finished.emit()

    def _run(self, args, timeout=None):
        self.current_process = subprocess.Popen(args, shell=False)
        return_code = self.current_process.wait(timeout=timeout)
        return return_code in (MSI_SUCCESS_CODES if is_msi_command(args) else {0})

    def _terminate_process_tree(self):
        if not self.current_process:
            return
        try:
            process = psutil.Process(self.current_process.pid)
            for child in process.children(recursive=True):
                child.kill()
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
