"""Analytics for add-on catalog entries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List, Mapping, Optional

from .models import Addon


@dataclass(frozen=True)
class CatalogSummary:
    total_addons: int
    unique_platforms: List[str]
    unique_os_types: List[str]
    latest_versions: Mapping[str, str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_addons": self.total_addons,
            "unique_platforms": list(self.unique_platforms),
            "unique_os_types": list(self.unique_os_types),
            "latest_versions": dict(self.latest_versions),
        }


def _select_latest(current: tuple[Optional[date], str], candidate: tuple[Optional[date], str]) -> tuple[Optional[date], str]:
    current_date, current_version = current
    candidate_date, candidate_version = candidate
    if candidate_date and (current_date is None or candidate_date > current_date):
        return candidate
    if candidate_date == current_date and candidate_version > current_version:
        return candidate
    return current


def summarize_addons(addons: Iterable[Addon]) -> CatalogSummary:
    addon_list = list(addons)
    platforms: set[str] = set()
    os_types: set[str] = set()
    latest_by_description: Dict[str, tuple[Optional[date], str]] = {}

    for addon in addon_list:
        platforms.update(addon.platforms)
        os_types.update(addon.os_types)
        key = addon.description or addon.id
        candidate = (addon.available_date, addon.version)
        if key in latest_by_description:
            latest_by_description[key] = _select_latest(latest_by_description[key], candidate)
        else:
            latest_by_description[key] = candidate

    latest_versions = {
        desc: version
        for desc, (_, version) in sorted(latest_by_description.items(), key=lambda item: item[0])
    }

    return CatalogSummary(
        total_addons=len(addon_list),
        unique_platforms=sorted(platforms),
        unique_os_types=sorted(os_types),
        latest_versions=latest_versions,
    )


__all__ = ["CatalogSummary", "summarize_addons"]
