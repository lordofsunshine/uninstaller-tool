from __future__ import annotations

__all__ = [
    "CleanupThread",
    "LeftoversThread",
    "LoaderThread",
    "SizesThread",
    "UninstallThread",
    "WorkerThread",
]


def __getattr__(name: str):
    if name == "WorkerThread":
        from app.workers.base import WorkerThread

        value = WorkerThread
    elif name == "CleanupThread":
        from app.workers.cleanup import CleanupThread

        value = CleanupThread
    elif name == "LeftoversThread":
        from app.workers.leftovers import LeftoversThread

        value = LeftoversThread
    elif name == "LoaderThread":
        from app.workers.loader import LoaderThread

        value = LoaderThread
    elif name == "SizesThread":
        from app.workers.sizes import SizesThread

        value = SizesThread
    elif name == "UninstallThread":
        from app.workers.uninstall import UninstallThread

        value = UninstallThread
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value
