import ctypes
import os
import subprocess
import sys


def is_admin() -> bool:
    if sys.platform != "win32":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _command_line() -> tuple[str, str]:
    if getattr(sys, "frozen", False):
        executable = sys.executable
        arguments = sys.argv[1:]
    else:
        executable = sys.executable
        arguments = [os.path.abspath(sys.argv[0]), *sys.argv[1:]]
    return executable, subprocess.list2cmdline(arguments)


def relaunch_as_admin() -> bool:
    if sys.platform != "win32":
        return False
    executable, arguments = _command_line()
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            arguments,
            None,
            1,
        )
    except (AttributeError, OSError):
        return False
    return int(result) > 32
