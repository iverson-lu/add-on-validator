"""Dataclasses representing add-on catalog objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass(frozen=True)
class FileEntry:
    """Represents a file listed inside an add-on element."""

    kind: str
    path: Optional[str]
    size: Optional[int]


@dataclass(frozen=True)
class Addon:
    """Represents a single `<addon>` entry in the catalog."""

    id: str
    description: str
    version: str
    available_date: Optional[date]
    expiration_date: Optional[date]
    platforms: List[str] = field(default_factory=list)
    os_versions: List[str] = field(default_factory=list)
    os_types: List[str] = field(default_factory=list)
    architecture: Optional[str] = None
    install_command: Optional[str] = None
    files: List[FileEntry] = field(default_factory=list)


__all__ = ["Addon", "FileEntry"]
