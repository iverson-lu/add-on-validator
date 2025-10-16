"""Command-line interface for the add-on catalog analyzer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from .analysis import summarize_addons
from .fetch import fetch_catalog
from .parser import parse_catalog

DEFAULT_URL = "https://ftp.hp.com/pub/tcimages/EasyUpdate/Images/addoncatalog.xml"
DEFAULT_CACHE = Path(".cache/addon_catalog.xml")


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download and analyze HP add-on catalog")
    parser.add_argument("--url", default=DEFAULT_URL, help="Catalog XML URL")
    parser.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_CACHE,
        help="Destination path for downloaded XML",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    args = parser.parse_args(argv)

    destination = fetch_catalog(args.url, args.cache)
    xml_text = _load_text(destination)
    addons = parse_catalog(xml_text)
    summary = summarize_addons(addons)

    if args.format == "json":
        data: Dict[str, Any] = summary.to_dict()
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(f"Catalog path: {destination}")
        print(f"Total add-ons: {summary.total_addons}")
        print(f"Unique platforms: {', '.join(summary.unique_platforms) or 'None'}")
        print(f"Unique OS types: {', '.join(summary.unique_os_types) or 'None'}")
        print("Latest versions by description:")
        for desc, version in sorted(summary.latest_versions.items()):
            print(f"  - {desc}: {version}")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
