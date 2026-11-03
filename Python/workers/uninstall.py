from __future__ import annotations

import subprocess
import time

import psutil
from PySide6.QtCore import Signal

from app.core.commands import (
    build_uninstall_command,
    command_exists,
    exit_code_succeeded,
    power_shell_command,
    prepare_process_arguments,
)
from app.core.processes import tree_memory_mb
from app.logging_setup import get_logger
from app.models.program import Program, ProgramStatus, UninstallResult
from app.workers.base import WorkerThread

LOGGER = get_logger("uninstall-worker")

POLL_SECONDS = 0.5
STATS_SECONDS = 1.5
SILENT_TIMEOUT = 300.0
SETTLE_SECONDS = 4.0
REBOOT_CODES = {1641, 3010}
NO_WINDOW = 0x08000000


class UninstallThread(WorkerThread):
    progress = Signal(int, int, str, str, str)
    stats = Signal(str)

    def __init__(self, programs: list[Program], silent: bool, parent=None):
        super().__init__(parent)
        self.programs = list(programs)
        self.silent = silent
        self.results: list[UninstallResult] = []
        self.uninstalled: list[Program] = []
        self.reboot_required: list[str] = []
        self._process: subprocess.Popen | None = None
        self._children: set[int] = set()

    def work(self) -> None:
        total = len(self.programs)
        for index, program in enumerate(self.programs):
            if self.isInterruptionRequested():
                break

            self.progress.emit(
                index,
                total,
                program.key,
                ProgramStatus.RUNNING.value,
                f"Uninstalling {program.name}…",
            )
            success = False
            exit_code: int | None = None
            still_running = False
            message = ""
            try:
                if program.is_store_app:
                    success, exit_code, still_running, message = self._run_store(program)
                else:
                    success, exit_code, still_running, message = self._run_classic(
                        program, index, total
                    )
            except subprocess.TimeoutExpired:
                self._kill_tree()
                message = f"Uninstall timed out for {program.name}"
            except (OSError, ValueError) as exc:
                LOGGER.warning("Could not uninstall %s: %s", program.name, exc)
                message = str(exc)
            except Exception as exc:
                LOGGER.exception("Unexpected uninstall error for %s", program.name)
                message = str(exc) or type(exc).__name__
            finally:
                self._process = None
                self._children.clear()
                self.stats.emit("")

            if self.isInterruptionRequested():
                message = f"Uninstall cancelled for {program.name}"
                success = False

            if success:
                if exit_code in REBOOT_CODES:
                    self.reboot_required.append(program.name)
                if still_running:
                    message = message or "The uninstaller is still finishing in the background"
                else:
                    self.uninstalled.append(program)
                    message = message or f"{program.name} was uninstalled"
            elif not message:
                if exit_code is None:
                    message = f"Could not uninstall {program.name}"
                else:
                    message = f"Uninstaller for {program.name} exited with code {exit_code}"

            status = ProgramStatus.SUCCESS if success else ProgramStatus.ERROR
            result = UninstallResult(
                program_key=program.key,
                name=program.name,
                success=success,
                exit_code=exit_code,
                reboot_required=exit_code in REBOOT_CODES,
                still_running=still_running,
                message=message,
            )
            self.results.append(result)
            LOGGER.info("%s: success=%s code=%s message=%s", program.name, success, exit_code, message)
            self.progress.emit(index + 1, total, program.key, status.value, message)

    def _run_classic(
        self,
        program: Program,
        index: int,
        total: int,
    ) -> tuple[bool, int | None, bool, str]:
        quiet = program.quiet_uninstall_string if self.silent else ""
        args = build_uninstall_command(quiet or program.uninstall_string, self.silent)
        if not args or not command_exists(args):
            raise FileNotFoundError(
                f"The uninstall command was not found for {program.name}"
            )

        timeout = SILENT_TIMEOUT if self.silent else None
        code, still_running, message = self._execute(args, timeout)
        if code is None:
            return False, None, still_running, message
        success = exit_code_succeeded(args, code) or code in REBOOT_CODES

        if not success and self.silent and not self.isInterruptionRequested():
            self.progress.emit(
                index,
                total,
                program.key,
                ProgramStatus.RUNNING.value,
                f"Silent mode failed for {program.name}; opening the uninstaller…",
            )
            fallback = build_uninstall_command(program.uninstall_string, False)
            if fallback and command_exists(fallback):
                code, still_running, message = self._execute(fallback, None)
                success = code is not None and (
                    exit_code_succeeded(fallback, code) or code in REBOOT_CODES
                )

        if success:
            return True, code, still_running, message
        if code is None:
            return False, None, still_running, message
        return False, code, still_running, message

    def _run_store(self, program: Program) -> tuple[bool, int | None, bool, str]:
        full_name = program.package_full_name
        if not full_name:
            raise ValueError("The Store package identifier is missing")
        escaped = full_name.replace("'", "''")
        script = (
            "$ErrorActionPreference = 'Stop'; "
            f"try {{ Remove-AppxPackage -Package '{escaped}' }} "
            "catch { Write-Error $_; exit 1 }"
        )
        code, still_running, message = self._execute(
            power_shell_command(script),
            SILENT_TIMEOUT,
        )
        success = code == 0
        return success, code, still_running, message

    def _execute(
        self,
        args: list[str],
        timeout: float | None,
    ) -> tuple[int | None, bool, str]:
        prepared = prepare_process_arguments(args)
        LOGGER.info("Starting uninstaller: %s", subprocess.list2cmdline(prepared))
        started = time.monotonic()
        last_stats = 0.0
        self._children.clear()

        try:
            self._process = subprocess.Popen(
                prepared,
                shell=False,
                creationflags=NO_WINDOW,
            )
        except (TypeError, ValueError):
            self._process = subprocess.Popen(prepared, shell=False)

        while True:
            if self.isInterruptionRequested():
                self._kill_tree()
                return None, False, "Cancelled"
            try:
                code = self._process.wait(timeout=POLL_SECONDS)
                break
            except subprocess.TimeoutExpired:
                self._collect_children()
                elapsed = time.monotonic() - started
                if timeout is not None and elapsed >= timeout:
                    self._kill_tree()
                    raise subprocess.TimeoutExpired(prepared, timeout) from None
                if elapsed - last_stats >= STATS_SECONDS:
                    last_stats = elapsed
                    memory = tree_memory_mb(self._process.pid)
                    self.stats.emit(
                        f"Elapsed: {elapsed:.0f} s   |   Memory usage: {memory:.1f} MB"
                    )

        still_running = self._settle()
        if still_running:
            LOGGER.warning(
                "Uninstaller process %s finished, but child processes are still running",
                self._process.pid,
            )
        return code, still_running, ""

    def _collect_children(self) -> None:
        if self._process is None:
            return
        try:
            process = psutil.Process(self._process.pid)
            for child in process.children(recursive=True):
                self._children.add(child.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return

    def _settle(self) -> bool:
        if not self._children:
            return False
        approved = set(self._children)
        deadline = time.monotonic() + SETTLE_SECONDS
        while time.monotonic() < deadline:
            alive = set()
            for pid in approved:
                try:
                    if psutil.Process(pid).is_running():
                        alive.add(pid)
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    continue
                except psutil.AccessDenied:
                    alive.add(pid)
            if not alive:
                return False
            alive.update(self._collect_new_children(approved))
            approved.update(alive)
            time.sleep(0.2)
        return bool(approved)

    def _collect_new_children(self, approved: set[int]) -> set[int]:
        discovered: set[int] = set()
        for pid in list(approved):
            try:
                process = psutil.Process(pid)
                for child in process.children(recursive=True):
                    if child.pid not in approved:
                        discovered.add(child.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return discovered

    def _kill_tree(self) -> None:
        if self._process is None:
            return
        try:
            process = psutil.Process(self._process.pid)
            for child in process.children(recursive=True):
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        for pid in self._children:
            try:
                psutil.Process(pid).kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
