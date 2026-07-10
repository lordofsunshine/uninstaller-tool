import os
import re
import shutil


MSI_SUCCESS_CODES = {0, 1641, 3010}


def split_windows_command(command):
    command = os.path.expandvars(str(command or "")).strip()
    if not command:
        return []

    if re.fullmatch(r"\{[0-9A-Fa-f-]+\}", command):
        return ["msiexec.exe", "/x", command]

    if command.startswith('"'):
        end = command.find('"', 1)
        if end == -1:
            return []
        executable = command[1:end]
        remainder = command[end + 1 :].strip()
    else:
        exe_match = re.match(r"(.+?\.(?:exe|com|bat|cmd))(?=\s|$)", command, re.IGNORECASE)
        if exe_match:
            executable = exe_match.group(1)
            remainder = command[exe_match.end() :].strip()
        else:
            parts = command.split(maxsplit=1)
            executable = parts[0]
            remainder = parts[1] if len(parts) == 2 else ""

    args = _split_arguments(remainder)
    return [executable, *args]


def _split_arguments(arguments):
    if not arguments:
        return []
    tokens = []
    current = []
    quoted = False
    for char in arguments:
        if char == '"':
            quoted = not quoted
        elif char.isspace() and not quoted:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        tokens.append("".join(current))
    return tokens


def is_msi_command(args):
    return bool(args) and os.path.basename(args[0]).casefold() in {"msiexec", "msiexec.exe"}


def build_uninstall_command(uninstall_string, silent=False):
    args = split_windows_command(uninstall_string)
    if not args:
        return []

    if is_msi_command(args):
        normalized = [args[0]]
        action_found = False
        for arg in args[1:]:
            match = re.fullmatch(r"/i(.+)", arg, re.IGNORECASE)
            if match:
                normalized.extend(["/x", match.group(1)])
                action_found = True
            elif arg.casefold() == "/i":
                normalized.append("/x")
                action_found = True
            else:
                normalized.append(arg)
                if arg.casefold() == "/x" or arg.casefold().startswith("/x{"):
                    action_found = True
        args = normalized
        if not action_found:
            args.insert(1, "/x")
        if silent:
            existing = {arg.casefold() for arg in args}
            if not existing.intersection({"/quiet", "/qn", "/passive"}):
                args.append("/quiet")
            if "/norestart" not in existing:
                args.append("/norestart")
        return args

    if silent:
        existing = {arg.casefold() for arg in args[1:]}
        executable = os.path.basename(args[0]).casefold()
        if "unins" in executable:
            for flag in ("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"):
                if flag.casefold() not in existing:
                    args.append(flag)
        elif not existing.intersection({"/s", "/silent", "/quiet", "-s", "--silent"}):
            args.append("/S")
    return args


def command_exists(args):
    if not args:
        return False
    executable = os.path.expandvars(args[0]).strip()
    if os.path.isfile(executable):
        return True
    return shutil.which(executable) is not None
