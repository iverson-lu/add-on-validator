"""Parsing helpers for the add-on catalog XML."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from xml.etree import ElementTree as ET

from .models import Addon, FileEntry

DATE_FORMATS = ["%m/%d/%Y", "%m/%d/%y"]


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value!r}")


def _parse_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _collect_platform_ids(addon_elem: ET.Element) -> List[str]:
    platforms = []
    for platform_elem in addon_elem.findall("SupportedPlatforms/platform"):
        platform_id = platform_elem.get("ID") or platform_elem.text or ""
        platform_id = platform_id.strip()
        if platform_id:
            platforms.append(platform_id)
    return platforms


def _collect_os_fields(addon_elem: ET.Element) -> tuple[List[str], List[str]]:
    versions: List[str] = []
    types: List[str] = []
    for os_elem in addon_elem.findall("OSes/OS"):
        version = (os_elem.get("Version") or os_elem.text or "").strip()
        os_type = (os_elem.get("Type") or "").strip()
        if version:
            versions.append(version)
        if os_type:
            types.append(os_type)
    return versions, types


def _collect_files(addon_elem: ET.Element) -> List[FileEntry]:
    files: List[FileEntry] = []
    files_elem = addon_elem.find("files")
    if files_elem is None:
        return files
    for child in files_elem:
        kind = child.tag
        path = (child.text or "").strip() or None
        size_attr = child.get("size")
        files.append(FileEntry(kind=kind, path=path, size=_parse_int(size_attr)))
    return files


def parse_catalog(xml_text: str) -> List[Addon]:
    """Parse catalog XML text into a list of :class:`Addon` objects."""

    root = ET.fromstring(xml_text)
    addons: List[Addon] = []
    for addon_elem in root.findall("addon"):
        os_versions, os_types = _collect_os_fields(addon_elem)
        addon = Addon(
            id=addon_elem.get("ID", "").strip(),
            description=addon_elem.get("Description", "").strip(),
            version=addon_elem.get("Version", "").strip(),
            available_date=_parse_date(addon_elem.get("AvailableDate")),
            expiration_date=_parse_date(addon_elem.get("ExpirationDate")),
            platforms=_collect_platform_ids(addon_elem),
            os_versions=os_versions,
            os_types=os_types,
            architecture=(addon_elem.findtext("architecture") or "").strip() or None,
            install_command=(addon_elem.findtext("install_command") or "").strip() or None,
            files=_collect_files(addon_elem),
        )
        addons.append(addon)
    return addons


__all__ = ["parse_catalog"]
