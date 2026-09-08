import subprocess
import time

import psutil
from PySide6.QtCore import QThread, Signal

from app.core.processes import tree_memory_mb
from app.core.commands import MSI_SUCCESS_CODES, build_uninstall_command, command_exists, is_msi_command

POLL_SEC = 0.5
SILENT_TIMEOUT = 300
REBOOT_CODES = {1641, 3010}

# hide console flash for gui-launched uninstallers
_NO_WINDOW = 0x08000000


class UninstallThread(QThread):
    progress = Signal(int, str, str, str)
    stats = Signal(str)
    completed = Signal()
    failed = Signal(str)

    def __init__(self, programs, silent, parent=None):
        super().__init__(parent)
        self.programs = list(programs)
        self.silent = silent
        self.current_process = None
        self.uninstalled = []
        self.reboot_required = []

    def run(self):
        for index, program in enumerate(self.programs):
            if self.isInterruptionRequested():
                break
            name = program.get("name", "Unknown program")
            self.progress.emit(index, f"Uninstalling {name}...", "running", name)
            try:
                if program.get("store_app"):
                    success, _ = self._run_store(program)
                else:
                    success, needs_reboot = self._run_classic(program, index)
                    if needs_reboot and name not in self.reboot_required:
                        self.reboot_required.append(name)

                if self.isInterruptionRequested():
                    self._kill_tree()
                    self.progress.emit(index + 1, f"Uninstall cancelled for {name}", "error", name)
                elif success:
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
                self.current_process = None
                self.stats.emit("")
        self.completed.emit()

    def _run_classic(self, program, index):
        name = program.get("name", "Unknown program")
        quiet = program.get("quiet_uninstall_string") if self.silent else ""
        args = build_uninstall_command(quiet or program.get("uninstall_string"), self.silent)
        if not command_exists(args):
            return False, False
        timeout = SILENT_TIMEOUT if self.silent else None
        success, needs_reboot = self._run(args, timeout=timeout)
        # some installers just ignore silent flags, retry with gui
        if not success and self.silent and not self.isInterruptionRequested():
            self.progress.emit(index, f"Silent mode failed for {name}; opening the uninstaller...", "running", name)
            args = build_uninstall_command(program.get("uninstall_string"), False)
            success, needs_reboot = self._run(args)
        return success, needs_reboot

    def _run_store(self, program):
        # uwps have no exe uninstaller, remove via powershell
        full = program.get("package_full_name", "")
        if not full:
            return False, False
        args = ["powershell", "-NoProfile", "-Command", f"Remove-AppxPackage -Package '{full}'"]
        return self._run(args, timeout=SILENT_TIMEOUT)

    def _run(self, args, timeout=None):
        try:
            self.current_process = subprocess.Popen(args, shell=False, creationflags=_NO_WINDOW)
        except (TypeError, ValueError):
            # non-windows python, no creationflags
            self.current_process = subprocess.Popen(args, shell=False)
        started = time.monotonic()
        while True:
            if self.isInterruptionRequested():
                self._kill_tree()
                return False, False
            try:
                code = self.current_process.wait(timeout=POLL_SEC)
                break
            except subprocess.TimeoutExpired:
                pass
            elapsed = time.monotonic() - started
            if timeout is not None and elapsed >= timeout:
                raise subprocess.TimeoutExpired(args, timeout)
            # live feedback while the uninstaller is doing its thing
            try:
                mem = tree_memory_mb(self.current_process.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                mem = 0.0
            self.stats.emit(f"Elapsed: {elapsed:.0f} s   |   Memory usage: {mem:.1f} MB")
        ok_codes = MSI_SUCCESS_CODES if is_msi_command(args) else {0}
        return code in ok_codes, code in REBOOT_CODES

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
