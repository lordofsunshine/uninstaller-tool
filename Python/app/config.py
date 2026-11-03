from app.version import APP_ID, APP_NAME, APP_VERSION

APP_AUTHOR = "Uninstaller Tool"

UNINSTALL_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
    <line x1="10" y1="11" x2="10" y2="17"/>
    <line x1="14" y1="11" x2="14" y2="17"/>
</svg>
"""

ARROW_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%23{color}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
    <path d="M6 9l6 6 6-6"/>
</svg>
"""

CHECK_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
    <path d="M5 12l4 4L19 6"/>
</svg>
"""

__all__ = [
    "APP_AUTHOR",
    "APP_ID",
    "APP_NAME",
    "APP_VERSION",
    "ARROW_ICON",
    "CHECK_ICON",
    "UNINSTALL_ICON",
]
