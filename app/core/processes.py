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
    icon = _normalize_path(str(program.get("icon") or "").split(",")[0])
    if icon and os.path.isfile(icon):
        paths.add(os.path.dirname(icon))
    for key in ("uninstall_string", "quiet_uninstall_string"):
        raw = str(program.get(key) or "")
        if raw.startswith('"'):
            candidate = raw[1:].split('"', 1)[0]
        else:
            candidate = raw.split(" ", 1)[0]
        candidate = _normalize_path(candidate)
        if candidate and os.path.isfile(candidate):
            paths.add(os.path.dirname(candidate))
    if not paths:
        # install location often empty, guess from standard dirs
        try:
            from app.core.files import _find_program_directories
            for guess in _find_program_directories(program.get("name", ""), program.get("publisher", "")):
                norm = _normalize_path(guess)
                if norm:
                    paths.add(norm)
        except (OSError, ValueError):
            pass
    return paths


def _exe_tokens(program):
    # fallback tokens for name-based matching when paths are unknown
    import re
    tokens = set()
    for value in (program.get("name", ""), program.get("publisher", "")):
        for part in re.split(r"\W+", str(value or "").casefold()):
            if len(part) >= 4 and part not in {"soft", "labs", "inc", "llc", "corp", "gmbh", "team"}:
                tokens.add(part)
    return tokens


def find_running_processes(program):
    roots = _program_paths(program)
    tokens = _exe_tokens(program) if not roots else set()
    if not roots and not tokens:
        return []
    matches = []
    seen = set()
    for process in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = process.info
            exe = _normalize_path(info.get("exe"))
            proc_name = str(info.get("name") or "").casefold()
            matched = False
            if exe:
                for root in roots:
                    if exe.startswith(root + os.sep) or exe == root:
                        matched = True
                        break
            if not matched and tokens and proc_name:
                # last resort: exe name contains program token
                stem = proc_name[:-4] if proc_name.endswith(".exe") else proc_name
                if stem and stem in tokens:
                    matched = True
            if not matched or (exe and exe in seen):
                continue
            if exe:
                seen.add(exe)
            matches.append({"pid": info["pid"], "name": info.get("name") or "?", "exe": info.get("exe")})
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
