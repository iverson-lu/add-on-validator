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
    latest_version_details: List[Addon]
    platform_counts: Mapping[str, int]
    os_type_counts: Mapping[str, int]
    architecture_counts: Mapping[str, int]
    monthly_release_counts: Mapping[str, int]

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_addons": self.total_addons,
            "unique_platforms": list(self.unique_platforms),
            "unique_os_types": list(self.unique_os_types),
            "unique_architectures": list(self.unique_architectures),
            "latest_versions": dict(self.latest_versions),
            "latest_version_details": [
                {
                    "id": addon.id,
                    "description": addon.description,
                    "version": addon.version,
                    "available_date": addon.available_date.isoformat()
                    if addon.available_date
                    else None,
                    "expiration_date": addon.expiration_date.isoformat()
                    if addon.expiration_date
                    else None,
                    "platforms": list(addon.platforms),
                    "os_versions": list(addon.os_versions),
                    "os_types": list(addon.os_types),
                    "architecture": addon.architecture,
                    "install_command": addon.install_command,
                }
                for addon in self.latest_version_details
            ],
            "platform_counts": dict(self.platform_counts),
            "os_type_counts": dict(self.os_type_counts),
            "architecture_counts": dict(self.architecture_counts),
            "monthly_release_counts": dict(self.monthly_release_counts),
        }


def _select_latest(
    current: tuple[Optional[date], str, Addon],
    candidate: tuple[Optional[date], str, Addon],
) -> tuple[Optional[date], str, Addon]:
    current_date, current_version, _ = current
    candidate_date, candidate_version, _ = candidate
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
    platform_counts: Dict[str, int] = {}
    os_type_counts: Dict[str, int] = {}
    architecture_counts: Dict[str, int] = {}
    monthly_counts: Dict[str, int] = {}
    latest_by_description: Dict[str, tuple[Optional[date], str, Addon]] = {}

    for addon in addon_list:
        platforms.update(addon.platforms)
        for platform in addon.platforms:
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

        os_types.update(addon.os_types)
        for os_type in addon.os_types:
            os_type_counts[os_type] = os_type_counts.get(os_type, 0) + 1

        if addon.architecture:
            architectures.add(addon.architecture)
            architecture_counts[addon.architecture] = (
                architecture_counts.get(addon.architecture, 0) + 1
            )

        if addon.available_date:
            month_key = addon.available_date.strftime("%Y-%m")
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1

        key = addon.description or addon.id
        candidate = (addon.available_date, addon.version, addon)
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

    latest_details_sorted = [
        (desc, available_date, version, addon)
        for desc, (available_date, version, addon) in sorted(
            latest_by_description.items(), key=lambda item: item[0]
        )
    ]
    latest_versions = {desc: version for desc, _, version, _ in latest_details_sorted}
    latest_version_details = [addon for _, _, _, addon in latest_details_sorted]

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
        latest_version_details=latest_version_details,
        platform_counts=dict(sorted(platform_counts.items(), key=lambda item: (-item[1], item[0]))),
        os_type_counts=dict(sorted(os_type_counts.items(), key=lambda item: (-item[1], item[0]))),
        architecture_counts=dict(
            sorted(architecture_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        monthly_release_counts=dict(sorted(monthly_counts.items())),
    )


__all__ = ["CatalogSummary", "LatestAddonEntry", "summarize_addons"]
