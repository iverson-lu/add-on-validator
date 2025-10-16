from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable
from wsgiref.util import setup_testing_defaults

from addon_catalog.analysis import CatalogSummary
from addon_catalog.web import create_app


def _fake_summary() -> CatalogSummary:
    return CatalogSummary(
        total_addons=2,
        unique_platforms=["mt440", "t655"],
        unique_os_types=["Windows"],
        latest_versions={"Example": "1.1.0"},
    )


def _make_request(app, path: str, query: str = "") -> tuple[str, Dict[str, str], bytes]:
    environ: Dict[str, object] = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = "GET"
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = query

    captured: Dict[str, object] = {}

    def start_response(status: str, headers: Iterable[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = dict(headers)

    body = b"".join(app(environ, start_response))
    return captured["status"], captured["headers"], body


def test_index_renders_dashboard(monkeypatch) -> None:
    app = create_app()

    def fake_compute(url: str, *, cache_path: Path | None = None):  # type: ignore[override]
        return _fake_summary(), Path("/tmp/catalog.xml")

    monkeypatch.setattr("addon_catalog.web.compute_summary", fake_compute)

    status, headers, body = _make_request(app, "/")

    assert status.startswith("200")
    assert headers["Content-Type"].startswith("text/html")
    payload = body.decode("utf-8")
    assert "HP Add-on Catalog Dashboard" in payload
    assert "2" in payload
    assert "Example" in payload


def test_api_summary_returns_json(monkeypatch) -> None:
    app = create_app()

    def fake_compute(url: str, *, cache_path: Path | None = None):  # type: ignore[override]
        return _fake_summary(), Path("/tmp/catalog.xml")

    monkeypatch.setattr("addon_catalog.web.compute_summary", fake_compute)

    status, headers, body = _make_request(app, "/api/summary")

    assert status.startswith("200")
    assert headers["Content-Type"] == "application/json"
    assert b"\"total_addons\": 2" in body
    assert b"Example" in body
