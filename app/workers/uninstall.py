import subprocess
import time

import psutil
from PySide6.QtCore import QThread, Signal

from app.core.processes import tree_memory_mb
from app.core.commands import MSI_SUCCESS_CODES, build_uninstall_command, command_exists, is_msi_command

POLL_SEC = 0.5
SILENT_TIMEOUT = 300


class UninstallThread(QThread):
    progress = Signal(int, str, str, str)
    stats = Signal(str)
    completed = Signal()
    failed = Signal(str)

    def __init__(self, programs, silent, parent=None):
        super().__init__(parent)
        self.programs = programs
        self.silent = silent
        self.current_process = None
        self.uninstalled = []

    def run(self):
        for index, program in enumerate(self.programs):
            name = program.get("name", "Unknown program")
            self.progress.emit(index, f"Uninstalling {name}...", "running", name)
            try:
                quiet = program.get("quiet_uninstall_string") if self.silent else ""
                args = build_uninstall_command(quiet or program.get("uninstall_string"), self.silent)
                if not command_exists(args):
                    self.progress.emit(index + 1, f"Invalid uninstall command for {name}", "error", name)
                    continue

                timeout = SILENT_TIMEOUT if self.silent else None
                success = self._run(args, timeout=timeout)

                # some installers just ignore silent flags, retry with gui
                if not success and self.silent:
                    self.progress.emit(index, f"Silent mode failed for {name}; opening the uninstaller...", "running", name)
                    args = build_uninstall_command(program.get("uninstall_string"), False)
                    success = self._run(args)

                if success:
                    self.uninstalled.append(program)
                    self.progress.emit(index + 1, f"{name} was uninstalled", "success", name)
                else:
                    self.progress.emit(index + 1, f"Could not uninstall {name}", "error", name)
            except subprocess.TimeoutExpired:
                self._kill_tree()
                self.progress.emit(index + 1, f"Uninstall timed out for {name}", "error", name)
            except (OSError, ValueError) as exc:
                self.failed.emit(f"Could not start the uninstaller for {name}: {exc}")
                self.progress.emit(index + 1, f"Could not uninstall {name}", "error", name)
            finally:
                self.stats.emit("")
        self.completed.emit()

    def _run(self, args, timeout=None):
        self.current_process = subprocess.Popen(args, shell=False)
        started = time.monotonic()
        while True:
            try:
                code = self.current_process.wait(timeout=POLL_SEC)
                break
            except subprocess.TimeoutExpired:
                pass
            elapsed = time.monotonic() - started
            if timeout is not None and elapsed >= timeout:
                raise subprocess.TimeoutExpired(args, timeout)
            # live feedback while the uninstaller is doing its thing
            mem = tree_memory_mb(self.current_process.pid)
            self.stats.emit(f"Elapsed: {elapsed:.0f} s   |   Memory usage: {mem:.1f} MB")
        ok_codes = MSI_SUCCESS_CODES if is_msi_command(args) else {0}
        return code in ok_codes

    def _kill_tree(self):
        if not self.current_process:
            return
        try:
            proc = psutil.Process(self.current_process.pid)
            for child in proc.children(recursive=True):
                child.kill()
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
