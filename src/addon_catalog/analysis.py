"""Analytics for add-on catalog entries."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List, Mapping, Optional

from collections import Counter

from .models import Addon


@dataclass(frozen=True)
class CatalogSummary:
    total_addons: int
    unique_platforms: List[str]
    unique_os_types: List[str]
    unique_architectures: List[str]
    latest_versions: Mapping[str, str]
    latest_addons: List["LatestAddonEntry"]
    platform_counts: Mapping[str, int]
    os_type_counts: Mapping[str, int]
    architecture_counts: Mapping[str, int]
    release_year_counts: Mapping[str, int]

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_addons": self.total_addons,
            "unique_platforms": list(self.unique_platforms),
            "unique_os_types": list(self.unique_os_types),
            "unique_architectures": list(self.unique_architectures),
            "latest_versions": dict(self.latest_versions),
            "latest_addons": [entry.to_dict() for entry in self.latest_addons],
            "platform_counts": dict(self.platform_counts),
            "os_type_counts": dict(self.os_type_counts),
            "architecture_counts": dict(self.architecture_counts),
            "release_year_counts": dict(self.release_year_counts),
        }


@dataclass(frozen=True)
class LatestAddonEntry:
    description: str
    version: str
    available_date: Optional[date]
    platforms: List[str]
    os_types: List[str]
    architecture: Optional[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "description": self.description,
            "version": self.version,
            "available_date": self.available_date.isoformat() if self.available_date else None,
            "platforms": list(self.platforms),
            "os_types": list(self.os_types),
            "architecture": self.architecture,
        }


def _select_latest(current: Addon, candidate: Addon) -> Addon:
    current_date, current_version = current.available_date, current.version
    candidate_date, candidate_version = candidate.available_date, candidate.version
    if candidate_date and (current_date is None or candidate_date > current_date):
        return candidate
    if candidate_date == current_date and candidate_version > current_version:
        return candidate
    return current


def summarize_addons(addons: Iterable[Addon]) -> CatalogSummary:
    addon_list = list(addons)
    platforms: set[str] = set()
    os_types: set[str] = set()
    architectures: set[str] = set()
    latest_by_description: Dict[str, Addon] = {}
    platform_counter: Counter[str] = Counter()
    os_counter: Counter[str] = Counter()
    architecture_counter: Counter[str] = Counter()
    release_counter: Counter[str] = Counter()

    for addon in addon_list:
        if addon.platforms:
            platforms.update(addon.platforms)
        else:
            platforms.add("未指定")

        if addon.os_types:
            os_types.update(addon.os_types)
        else:
            os_types.add("未指定")
        architecture_value = addon.architecture or "未指定"
        if addon.architecture:
            architectures.add(addon.architecture)
        else:
            architectures.add("未指定")

        key = addon.description or addon.id
        if key in latest_by_description:
            latest_by_description[key] = _select_latest(latest_by_description[key], addon)
        else:
            latest_by_description[key] = addon

        if addon.platforms:
            platform_counter.update(addon.platforms)
        else:
            platform_counter.update(["未指定"])

        if addon.os_types:
            os_counter.update(addon.os_types)
        else:
            os_counter.update(["未指定"])

        architecture_counter.update([architecture_value])

        if addon.available_date:
            release_counter.update([str(addon.available_date.year)])
        else:
            release_counter.update(["未知"])

    latest_versions = {
        desc: version
        for desc, version in sorted(
            ((key, addon.version) for key, addon in latest_by_description.items()),
            key=lambda item: item[0],
        )
    }

    latest_addons = [
        LatestAddonEntry(
            description=key,
            version=addon.version,
            available_date=addon.available_date,
            platforms=sorted(addon.platforms) if addon.platforms else ["未指定"],
            os_types=sorted(addon.os_types) if addon.os_types else ["未指定"],
            architecture=addon.architecture or "未指定",
        )
        for key, addon in sorted(latest_by_description.items(), key=lambda item: item[0])
    ]

    sorted_platform_counts = dict(sorted(platform_counter.items(), key=lambda item: (-item[1], item[0])))
    sorted_os_counts = dict(sorted(os_counter.items(), key=lambda item: (-item[1], item[0])))
    sorted_architecture_counts = dict(
        sorted(architecture_counter.items(), key=lambda item: (-item[1], item[0]))
    )
    sorted_release_counts = dict(sorted(release_counter.items(), key=lambda item: item[0]))

    return CatalogSummary(
        total_addons=len(addon_list),
        unique_platforms=sorted(platforms),
        unique_os_types=sorted(os_types),
        unique_architectures=sorted(architectures),
        latest_versions=latest_versions,
        latest_addons=latest_addons,
        platform_counts=sorted_platform_counts,
        os_type_counts=sorted_os_counts,
        architecture_counts=sorted_architecture_counts,
        release_year_counts=sorted_release_counts,
    )


__all__ = ["CatalogSummary", "LatestAddonEntry", "summarize_addons"]
