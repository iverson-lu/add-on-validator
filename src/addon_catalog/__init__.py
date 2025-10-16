"""Addon catalog analyzer package."""

from .analysis import CatalogSummary, summarize_addons
from .fetch import fetch_catalog
from .parser import parse_catalog

__all__ = [
    "CatalogSummary",
    "fetch_catalog",
    "parse_catalog",
    "summarize_addons",
]
