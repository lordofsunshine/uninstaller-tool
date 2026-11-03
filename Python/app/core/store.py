from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import time

from app.core.commands import power_shell_command
from app.logging_setup import get_logger
from app.models.program import Program, ProgramSource
from app.paths import cache_dir

LOGGER = get_logger("store")

CACHE_TTL_SECONDS = 12 * 60 * 60
CACHE_FILE = cache_dir() / "store_apps.json"
TIMEOUT_SECONDS = 45
NO_WINDOW = 0x08000000

_GUID = re.compile(r"^[0-9a-fA-F-]{10,}$")

SCRIPT = (
    "$ErrorActionPreference = 'Stop'; "
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    "$OutputEncoding = [System.Text.Encoding]::UTF8; "
    "$pkgs = Get-AppxPackage | Where-Object { -not $_.IsFramework -and -not $_.IsResourcePackage "
    "-and $_.SignatureKind -ne 'System' } | Select-Object Name,PackageFullName,PackageFamilyName,"
    "Publisher,Version,InstallLocation; "
    "$tiles = Get-StartApps | Select-Object Name,AppID; "
    "@{packages=$pkgs; tiles=$tiles} | ConvertTo-Json -Compress -Depth 6"
)


def _as_list(value) -> list:
    if not value:
        return []
    if isinstance(value, dict):
        return [value]
    return value if isinstance(value, list) else []


def _clean_publisher(raw) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    if not text.startswith("CN="):
        return text[:80]
    parts: dict[str, str] = {}
    for chunk in text.split(","):
        key, separator, value = chunk.partition("=")
        if separator:
            parts[key.strip().upper()] = value.strip()
    common_name = parts.get("CN", "")
    looks_like_hash = (
        _GUID.match(common_name.replace(" ", ""))
        or (
            common_name
            and common_name.upper() == common_name
            and any(character.isdigit() for character in common_name)
            and " " not in common_name
        )
    )
    if looks_like_hash:
        common_name = parts.get("O", "") or ""
    return common_name[:80]


def _prettify(name: str) -> str:
    text = str(name or "").strip()
    if not text:
        return ""
    base = text.split("_", 1)[0]
    if "." in base:
        base = base.split(".", 1)[1]
    readable = base.replace(".", " ").strip()
    return readable or text


def _tile_map(tiles) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for tile in _as_list(tiles):
        app_id = str(tile.get("AppID") or tile.get("AppId") or "")
        friendly = str(tile.get("Name") or "").strip()
        if not app_id or not friendly or "!" not in app_id:
            continue
        family = app_id.split("!", 1)[0]
        mapping.setdefault(family.casefold(), friendly)
    return mapping


def _decode(output: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1251", "mbcs"):
        try:
            return output.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return output.decode("utf-8", errors="replace")


def fetch_store_apps() -> list[Program]:
    arguments = power_shell_command(SCRIPT)
    try:
        completed = subprocess.run(
            arguments,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            creationflags=NO_WINDOW,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("Store app scan timed out") from exc
    except OSError as exc:
        raise OSError(f"Could not start PowerShell: {exc}") from exc

    if completed.returncode != 0:
        message = _decode(completed.stderr).strip()
        raise OSError(message or "PowerShell returned an error")

    text = _decode(completed.stdout).strip()
    if not text:
        return []

    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError("Could not parse the Store app list") from exc
    if not isinstance(data, dict):
        return []

    tiles = _tile_map(data.get("tiles"))
    programs: list[Program] = []
    for entry in _as_list(data.get("packages")):
        full_name = str(entry.get("PackageFullName") or "").strip()
        if not full_name:
            continue
        raw_name = str(entry.get("Name") or "").strip()
        family = str(entry.get("PackageFamilyName") or "").strip()
        friendly = tiles.get(family.casefold(), "")
        if friendly:
            name = friendly
        elif _GUID.match(raw_name):
            continue
        else:
            name = _prettify(raw_name)
        if not name:
            continue
        programs.append(
            Program(
                name=name,
                uninstall_string=f"remove-appx:{full_name}",
                quiet_uninstall_string=f"remove-appx:{full_name}",
                install_location=str(entry.get("InstallLocation") or ""),
                publisher=_clean_publisher(entry.get("Publisher")),
                version=str(entry.get("Version") or ""),
                source=ProgramSource.STORE,
                package_full_name=full_name,
                package_family=family,
            )
        )

    programs.sort(key=lambda item: item.name.casefold())
    return programs


def save_store_cache(programs: list[Program]) -> None:
    payload = {
        "saved_at": int(time.time()),
        "programs": [program.to_dict() for program in programs],
    }
    temporary = CACHE_FILE.with_suffix(".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporary, CACHE_FILE)
    except OSError as exc:
        LOGGER.warning("Could not save the Store cache: %s", exc)
        with contextlib.suppress(OSError):
            temporary.unlink(missing_ok=True)


def load_store_cache() -> tuple[list[Program], bool]:
    try:
        payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], False

    if not isinstance(payload, dict):
        return [], False
    try:
        saved_at = max(0, int(payload.get("saved_at") or 0))
    except (TypeError, ValueError, OverflowError):
        saved_at = 0
    fresh = saved_at > 0 and (time.time() - saved_at) < CACHE_TTL_SECONDS
    programs: list[Program] = []
    for item in _as_list(payload.get("programs")):
        if not isinstance(item, dict):
            continue
        try:
            program = Program.from_dict(item)
        except (TypeError, ValueError):
            continue
        if program.name and program.package_full_name:
            programs.append(program)
    programs.sort(key=lambda item: item.name.casefold())
    return programs, fresh
