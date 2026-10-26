from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.utils import format_size


class ProgramSource(str, Enum):
    REGISTRY = "registry"
    STORE = "store"


class ProgramStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(slots=True)
class Program:
    name: str
    uninstall_string: str = ""
    quiet_uninstall_string: str = ""
    install_location: str = ""
    publisher: str = ""
    install_date: str = ""
    version: str = ""
    size_kb: int = 0
    icon: str = ""
    source: ProgramSource = ProgramSource.REGISTRY
    package_full_name: str = ""
    package_family: str = ""
    registry_hive: str = ""
    registry_subkey: str = ""
    status: ProgramStatus = ProgramStatus.IDLE
    checked: bool = False

    @property
    def is_store_app(self) -> bool:
        return self.source is ProgramSource.STORE

    @property
    def key(self) -> str:
        if self.is_store_app:
            return f"store::{self.package_full_name or self.name.casefold()}"
        if self.registry_subkey:
            return f"registry::{self.registry_hive}\\{self.registry_subkey}"
        return (
            f"registry::{self.name.casefold()}|"
            f"{self.version.casefold()}|{self.uninstall_string.casefold()}"
        )

    @property
    def size_bytes(self) -> int:
        return max(0, int(self.size_kb)) * 1024

    def meta_text(self) -> str:
        parts: list[str] = []
        if self.is_store_app:
            parts.append("Store")
        if self.publisher:
            parts.append(self.publisher)
        if self.version:
            parts.append(f"v{self.version}")
        size = self.size_bytes
        if size > 0:
            parts.append(format_size(size))
        return "   ·   ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "uninstall_string": self.uninstall_string,
            "quiet_uninstall_string": self.quiet_uninstall_string,
            "install_location": self.install_location,
            "publisher": self.publisher,
            "install_date": self.install_date,
            "version": self.version,
            "size_kb": self.size_kb,
            "icon": self.icon,
            "source": self.source.value,
            "package_full_name": self.package_full_name,
            "package_family": self.package_family,
            "registry_hive": self.registry_hive,
            "registry_subkey": self.registry_subkey,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Program:
        try:
            size_kb = max(0, int(float(data.get("size_kb") or 0)))
        except (TypeError, ValueError, OverflowError):
            size_kb = 0
        try:
            source = ProgramSource(data.get("source") or ProgramSource.REGISTRY.value)
        except ValueError:
            source = ProgramSource.REGISTRY
        return cls(
            name=str(data.get("name") or ""),
            uninstall_string=str(data.get("uninstall_string") or ""),
            quiet_uninstall_string=str(data.get("quiet_uninstall_string") or ""),
            install_location=str(data.get("install_location") or ""),
            publisher=str(data.get("publisher") or ""),
            install_date=str(data.get("install_date") or ""),
            version=str(data.get("version") or ""),
            size_kb=size_kb,
            icon=str(data.get("icon") or ""),
            source=source,
            package_full_name=str(data.get("package_full_name") or ""),
            package_family=str(data.get("package_family") or ""),
            registry_hive=str(data.get("registry_hive") or ""),
            registry_subkey=str(data.get("registry_subkey") or ""),
        )


class RegistryEntryKind(str, Enum):
    UNINSTALL = "uninstall"
    VENDOR = "vendor"


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    hive: str
    subkey: str
    display_name: str = ""
    key_name: str = ""
    kind: RegistryEntryKind = RegistryEntryKind.UNINSTALL

    @property
    def path(self) -> str:
        return f"{self.hive}\\{self.subkey}"


@dataclass(slots=True)
class Leftovers:
    program_key: str = ""
    program_name: str = ""
    files: list[str] = field(default_factory=list)
    registry: list[RegistryEntry] = field(default_factory=list)
    timed_out: bool = False

    @property
    def has_items(self) -> bool:
        return bool(self.files or self.registry)


@dataclass(slots=True)
class RemovalResult:
    removed_files: int = 0
    removed_registry: int = 0
    scheduled_files: int = 0
    errors: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UninstallResult:
    program_key: str
    name: str
    success: bool
    exit_code: int | None = None
    reboot_required: bool = False
    still_running: bool = False
    message: str = ""


@dataclass(slots=True)
class ProcessEntry:
    pid: int
    name: str
    exe: str
