import os

import psutil


def _normalize_path(path):
    try:
        return os.path.normcase(os.path.abspath(os.path.expandvars(str(path or "").strip().strip('"'))))
    except (OSError, ValueError):
        return ""


def _program_paths(program):
    paths = set()
    location = _normalize_path(program.get("install_location"))
    if location and os.path.isdir(location):
        paths.add(location)
    for key in ("uninstall_string", "quiet_uninstall_string"):
        raw = str(program.get(key) or "")
        if raw.startswith('"'):
            candidate = raw[1:].split('"', 1)[0]
        else:
            candidate = raw.split(" ", 1)[0]
        candidate = _normalize_path(candidate)
        if candidate and os.path.isfile(candidate):
            paths.add(os.path.dirname(candidate))
    return paths


def find_running_processes(program):
    roots = _program_paths(program)
    if not roots:
        return []
    matches = []
    seen = set()
    for process in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = process.info
            exe = _normalize_path(info.get("exe"))
            if not exe or exe in seen:
                continue
            for root in roots:
                if exe.startswith(root + os.sep) or exe == root:
                    seen.add(exe)
                    matches.append({"pid": info["pid"], "name": info.get("name") or "?", "exe": info.get("exe")})
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return matches


def kill_processes(entries, timeout=5.0):
    killed = []
    errors = []
    targets = []
    for entry in entries:
        try:
            process = psutil.Process(entry["pid"])
            targets.append(process)
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


def tree_memory_mb(pid):
    total = 0
    try:
        process = psutil.Process(pid)
        processes = [process, *process.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return 0.0
    for item in processes:
        try:
            total += item.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total / (1024 * 1024)
