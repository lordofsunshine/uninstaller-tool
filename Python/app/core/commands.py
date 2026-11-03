from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess

MSI_SUCCESS_CODES = {0, 1641, 3010}
MSI_REBOOT_CODES = {1641, 3010}
SILENT_FALLBACK_FLAGS = ("/S", "/s", "/silent", "/quiet", "-s", "--silent")
NSIS_FLAGS = ("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART")
BATCH_EXTENSIONS = {".bat", ".cmd"}


def system_root() -> str:
    return os.environ.get("SYSTEMROOT") or os.environ.get("WINDIR") or r"C:\Windows"


def system32_dir() -> str:
    return os.path.join(system_root(), "System32")


def powershell_path() -> str:
    candidate = os.path.join(
        system32_dir(), "WindowsPowerShell", "v1.0", "powershell.exe"
    )
    return candidate if os.path.isfile(candidate) else "powershell.exe"


def cmd_path() -> str:
    candidate = os.path.join(system32_dir(), "cmd.exe")
    return candidate if os.path.isfile(candidate) else "cmd.exe"


def reg_path() -> str:
    candidate = os.path.join(system32_dir(), "reg.exe")
    return candidate if os.path.isfile(candidate) else "reg.exe"


def power_shell_command(script: str) -> list[str]:
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return [
        powershell_path(),
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        encoded,
    ]


def split_windows_command(command: str | None) -> list[str]:
    text = os.path.expandvars(str(command or "")).strip()
    if not text:
        return []

    if re.fullmatch(r"\{[0-9A-Fa-f-]+\}", text):
        return [os.path.join(system32_dir(), "msiexec.exe"), "/x", text]

    if text.startswith('"'):
        end = text.find('"', 1)
        if end == -1:
            return []
        executable = text[1:end]
        remainder = text[end + 1 :].strip()
    else:
        match = re.match(r"(.+?\.(?:exe|com|bat|cmd))(?=\s|$)", text, re.IGNORECASE)
        if match:
            executable = match.group(1)
            remainder = text[match.end() :].strip()
        else:
            parts = text.split(maxsplit=1)
            executable = parts[0]
            remainder = parts[1] if len(parts) == 2 else ""

    return [executable, *_split_arguments(remainder)]


def _split_arguments(arguments: str) -> list[str]:
    if not arguments:
        return []
    tokens: list[str] = []
    current: list[str] = []
    quoted = False
    for character in arguments:
        if character == '"':
            quoted = not quoted
        elif character.isspace() and not quoted:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(character)
    if current:
        tokens.append("".join(current))
    return tokens


def is_msi_command(args: list[str]) -> bool:
    if not args:
        return False
    return os.path.basename(args[0]).casefold() in {"msiexec", "msiexec.exe"}


def build_uninstall_command(uninstall_string: str | None, silent: bool = False) -> list[str]:
    args = split_windows_command(uninstall_string)
    if not args:
        return []

    if is_msi_command(args):
        normalized = [args[0]]
        action_found = False
        for argument in args[1:]:
            match = re.fullmatch(r"/i(.+)", argument, re.IGNORECASE)
            if match:
                normalized.extend(["/x", match.group(1)])
                action_found = True
            elif argument.casefold() == "/i":
                normalized.append("/x")
                action_found = True
            else:
                normalized.append(argument)
                if argument.casefold() == "/x" or argument.casefold().startswith("/x{"):
                    action_found = True
        args = normalized
        if not action_found:
            args.insert(1, "/x")
        if silent:
            existing = {argument.casefold() for argument in args}
            if not existing.intersection({"/quiet", "/qn", "/passive"}):
                args.append("/quiet")
            if "/norestart" not in existing:
                args.append("/norestart")
        return args

    extension = os.path.splitext(args[0])[1].casefold()
    if silent and extension not in BATCH_EXTENSIONS:
        existing = {argument.casefold() for argument in args[1:]}
        executable = os.path.basename(args[0]).casefold()
        if "unins" in executable:
            for flag in NSIS_FLAGS:
                if flag.casefold() not in existing:
                    args.append(flag)
        elif not existing.intersection(SILENT_FALLBACK_FLAGS):
            args.append("/S")
    return args


def _search_directories() -> list[str]:
    values = [
        system32_dir(),
        os.path.join(system_root(), "SysWOW64"),
        system_root(),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    return [value for value in values if value]


def resolve_executable(name: str) -> str:
    text = os.path.expandvars(str(name or "")).strip().strip('"')
    if not text:
        return ""
    if os.path.isfile(text):
        return os.path.abspath(text)

    base = os.path.basename(text)
    if base.casefold() in {"powershell", "powershell.exe"}:
        candidate = powershell_path()
        if os.path.isfile(candidate):
            return candidate
    if base.casefold() in {"cmd", "cmd.exe"}:
        candidate = cmd_path()
        if os.path.isfile(candidate):
            return candidate
    if base.casefold() in {"reg", "reg.exe"}:
        candidate = reg_path()
        if os.path.isfile(candidate):
            return candidate
    if base.casefold() in {"msiexec", "msiexec.exe"}:
        candidate = os.path.join(system32_dir(), "msiexec.exe")
        if os.path.isfile(candidate):
            return candidate

    for directory in _search_directories():
        candidate = os.path.join(directory, base)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    found = shutil.which(text)
    return os.path.abspath(found) if found else ""


def command_exists(args: list[str]) -> bool:
    if not args:
        return False
    return bool(resolve_executable(args[0]))


def _batch_command_line(args: list[str]) -> list[str]:
    line = subprocess.list2cmdline(args)
    return [cmd_path(), "/d", "/s", "/c", line]


def prepare_process_arguments(args: list[str]) -> list[str]:
    if not args:
        raise ValueError("Empty command")
    executable = resolve_executable(args[0])
    if not executable:
        raise FileNotFoundError(args[0])
    prepared = [executable, *args[1:]]
    if os.path.splitext(executable)[1].casefold() in BATCH_EXTENSIONS:
        return _batch_command_line(prepared)
    return prepared


def success_exit_codes(args: list[str]) -> set[int]:
    if is_msi_command(args):
        return MSI_SUCCESS_CODES
    return {0}


def reboot_exit_codes(args: list[str]) -> set[int]:
    if is_msi_command(args):
        return MSI_REBOOT_CODES
    return set()


def exit_code_succeeded(args: list[str], code: int) -> bool:
    return code in success_exit_codes(args)
