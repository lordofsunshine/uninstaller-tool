import json
import re
import subprocess

# classic registry misses store apps, but raw package names are unreadable,
# so resolve friendly tile names and skip frameworks/system stubs

_TIMEOUT = 30

_GUID = re.compile(r"^[0-9a-fA-F-]{10,}$")
_ID_PREFIX = re.compile(r"^[A-Za-z0-9]{4,}\d|\d[A-Za-z0-9]{4,}$")


def _as_list(value):
    if not value:
        return []
    if isinstance(value, dict):
        return [value]
    return value if isinstance(value, list) else []


def _clean_publisher(raw):
    # publisher comes as cert dn like "CN=Foo, O=Bar, ...", keep it short
    text = str(raw or "").strip()
    if not text:
        return ""
    if not text.startswith("CN="):
        return text[:80]
    parts = {}
    for chunk in text.split(","):
        key, sep, val = chunk.partition("=")
        if sep:
            parts[key.strip().upper()] = val.strip()
    cn = parts.get("CN", "")
    if _GUID.match(cn.replace(" ", "")) or (cn and cn.upper() == cn and any(c.isdigit() for c in cn) and " " not in cn):
        # cn is a hash/guid, company name usually sits in O
        cn = parts.get("O", "") or ""
    return cn[:80]


def _prettify(name, family):
    # fallback when no start tile exists, strip publisher id prefix
    text = str(name or "").strip()
    if "." in text:
        first, _, rest = text.partition(".")
        if _ID_PREFIX.match(first):
            text = rest
    return text.replace(".", " ").strip() or str(name or "").strip()


def _tile_map(tiles):
    # AppID looks like "FamilyName!App", first tile wins
    mapping = {}
    for tile in tiles:
        app_id = str(tile.get("AppID") or tile.get("AppId") or "")
        friendly = str(tile.get("Name") or "").strip()
        if not app_id or not friendly or "!" not in app_id:
            continue
        family = app_id.split("!", 1)[0]
        mapping.setdefault(family.casefold(), friendly)
    return mapping


def _run_ps(script):
    # powershell writes redirected stdout in console encoding,
    # force utf-8 on both ends or cyrillic tile names turn into mojibake
    full_script = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + script
    cmd = ["powershell", "-NoProfile", "-Command", full_script]
    try:
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=_TIMEOUT, creationflags=0x08000000)
        except (TypeError, ValueError):
            # non-windows python, no creationflags
            proc = subprocess.run(cmd, capture_output=True, timeout=_TIMEOUT)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        text = proc.stdout.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = proc.stdout.decode("cp1251")
        except UnicodeDecodeError:
            return None
    return text.strip() or None


def get_store_apps():
    script = (
        "$pkgs = Get-AppxPackage | Where-Object { -not $_.IsFramework -and -not $_.IsResourcePackage "
        "-and $_.SignatureKind -ne 'System' } | Select-Object Name,PackageFullName,PackageFamilyName,"
        "Publisher,Version,InstallLocation; "
        "$tiles = Get-StartApps | Select-Object Name,AppID; "
        "@{packages=$pkgs; tiles=$tiles} | ConvertTo-Json -Compress -Depth 4"
    )
    raw = _run_ps(script)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(data, dict):
        return []
    tiles = _tile_map(_as_list(data.get("tiles")))
    programs = []
    for entry in _as_list(data.get("packages")):
        full = str(entry.get("PackageFullName") or "").strip()
        if not full:
            continue
        raw_name = str(entry.get("Name") or "").strip()
        family = str(entry.get("PackageFamilyName") or "").strip()
        friendly = tiles.get(family.casefold(), "")
        if friendly:
            name = friendly
        elif _GUID.match(raw_name):
            # background package without a tile, nothing readable to show
            continue
        else:
            name = _prettify(raw_name, family)
        if not name:
            continue
        programs.append({
            "name": name,
            "uninstall_string": f"remove-appx:{full}",
            "quiet_uninstall_string": f"remove-appx:{full}",
            "install_location": str(entry.get("InstallLocation") or ""),
            "publisher": _clean_publisher(entry.get("Publisher")),
            "install_date": "",
            "version": str(entry.get("Version") or ""),
            "size": 0,
            "url": "",
            "contact": "",
            "icon": "",
            "store_app": True,
            "package_full_name": full,
            "package_family": family,
        })
    programs.sort(key=lambda p: p["name"].casefold())
    return programs
