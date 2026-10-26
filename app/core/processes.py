from __future__ import annotations

import os
import time

import psutil

from app.core.commands import split_windows_command
from app.core.safety import is_safe_program_directory, normalize_path
from app.logging_setup import get_logger
from app.models.program import ProcessEntry
from app.utils import split_icon_reference

LOGGER = get_logger("processes")


def _uninstaller_directory(program) -> str:
    for field_name in ("uninstall_string", "quiet_uninstall_string"):
        parts = split_windows_command(str(getattr(program, field_name, "") or ""))
        if not parts:
            continue
        executable = parts[0]
        if os.path.isfile(executable):
            return os.path.dirname(executable)
    return ""


def program_paths(program) -> set[str]:
    paths: set[str] = set()

    location = str(getattr(program, "install_location", "") or "")
    if is_safe_program_directory(location):
        paths.add(normalize_path(location))

    icon_path, _ = split_icon_reference(str(getattr(program, "icon", "") or ""))
    if icon_path and os.path.isfile(icon_path):
        directory = os.path.dirname(icon_path)
        if is_safe_program_directory(directory):
            paths.add(normalize_path(directory))

    uninstaller = _uninstaller_directory(program)
    if uninstaller and is_safe_program_directory(uninstaller):
        paths.add(normalize_path(uninstaller))

    return {path for path in paths if path}


def scan_processes() -> list[ProcessEntry]:
    entries: list[ProcessEntry] = []
    for process in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = process.info
            entries.append(
                ProcessEntry(
                    pid=int(info["pid"]),
                    name=str(info.get("name") or "?"),
                    exe=normalize_path(info.get("exe")),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return entries


def find_running_processes(
    program,
    snapshot: list[ProcessEntry] | None = None,
) -> list[ProcessEntry]:
    roots = sorted(program_paths(program))
    if not roots:
        return []
    entries = snapshot if snapshot is not None else scan_processes()
    matches: list[ProcessEntry] = []
    for entry in entries:
        if not entry.exe:
            continue
        for root in roots:
            if entry.exe == root or entry.exe.startswith(root + os.sep):
                matches.append(entry)
                break
    return matches


def batch_find_running(programs) -> dict[str, list[ProcessEntry]]:
    snapshot = scan_processes()
    return {program.key: find_running_processes(program, snapshot) for program in programs}


def kill_processes(entries, timeout: float = 5.0) -> dict[str, list]:
    killed: list[int] = []
    errors: list[str] = []
    targets = []

    for entry in entries:
        try:
            targets.append(psutil.Process(entry.pid))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    for process in targets:
        try:
            for child in process.children(recursive=True):
                try:
                    child.kill()
                    killed.append(child.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                    errors.append(str(exc))
            process.kill()
            killed.append(process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            errors.append(str(exc))

    psutil.wait_procs(targets, timeout=timeout)
    return {"killed": killed, "errors": errors}


def tree_memory_mb(pid: int) -> float:
    try:
        process = psutil.Process(pid)
        processes = [process, *process.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return 0.0
    total = 0
    for item in processes:
        try:
            total += item.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total / (1024 * 1024)


def wait_for_process_tree(pid: int, timeout: float) -> bool:
    try:
        process = psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return True
    except psutil.AccessDenied:
        return False

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if not process.is_running():
                return True
            children = process.children(recursive=True)
            alive = [child for child in children if child.is_running()]
            if alive:
                time.sleep(0.1)
                continue
            process.wait(timeout=0.2)
            return True
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return True
        except (psutil.AccessDenied, psutil.TimeoutExpired):
            time.sleep(0.1)
    return False
