"""Standard-library web interface for the add-on catalog analyzer."""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from string import Template
from typing import Dict, Iterable
from urllib.parse import parse_qs, urlparse
from wsgiref.simple_server import make_server
from wsgiref.util import setup_testing_defaults

from .__main__ import DEFAULT_CACHE, DEFAULT_URL
from .analysis import CatalogSummary, summarize_addons
from .fetch import fetch_catalog
from .parser import parse_catalog

TEMPLATE_PATH = Path(__file__).with_name("templates").joinpath("index.html")
HTML_TEMPLATE = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))


def compute_summary(url: str, *, cache_path: Path | None = None) -> tuple[CatalogSummary, Path]:
    """Download, parse, and summarize the catalog for *url*."""

    destination = Path(cache_path or DEFAULT_CACHE)
    fetched_path = fetch_catalog(url, destination)
    xml_text = fetched_path.read_text(encoding="utf-8")
    addons = parse_catalog(xml_text)
    summary = summarize_addons(addons)
    return summary, fetched_path


def _render_error(message: str | None) -> str:
    if not message:
        return ""
    escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<div class=\"error-message\">{escaped}</div>"


def _render_summary(summary: CatalogSummary | None, destination: Path | None) -> str:
    if summary is None:
        return ""

    platforms_meta = ", ".join(summary.unique_platforms) or "None listed"
    os_meta = ", ".join(summary.unique_os_types) or "None listed"
    rows: Iterable[str]
    if summary.latest_versions:
        rows = (
            f"<tr><td>{desc}</td><td>{version}</td></tr>"
            for desc, version in summary.latest_versions.items()
        )
    else:
        rows = ("<tr><td colspan=\"2\">No version information available.</td></tr>",)

    latest_rows = "\n".join(rows)
    destination_text = destination if destination is not None else "Unknown"

    return f"""
<section class="status-card">
  <article>
    <h2>Total Add-ons</h2>
    <p class="value">{summary.total_addons}</p>
    <p class="meta">Catalog path: {destination_text}</p>
  </article>
  <article>
    <h2>Platforms</h2>
    <p class="value">{len(summary.unique_platforms)}</p>
    <p class="meta">{platforms_meta}</p>
  </article>
  <article>
    <h2>OS Types</h2>
    <p class="value">{len(summary.unique_os_types)}</p>
    <p class="meta">{os_meta}</p>
  </article>
</section>

<section class="latest">
  <header>
    <h3>Latest versions by description</h3>
    <p class="meta">
      Quickly compare the most recent releases for every add-on. Each row
      reflects the newest version discovered in the catalog.
    </p>
  </header>
  <table class="latest-table">
    <thead>
      <tr>
        <th scope="col">Description</th>
        <th scope="col">Latest version</th>
      </tr>
    </thead>
    <tbody>
      {latest_rows}
    </tbody>
  </table>
</section>
""".strip()


def render_dashboard(url: str, summary: CatalogSummary | None, destination: Path | None, error: str | None) -> str:
    """Render the dashboard HTML."""

    return HTML_TEMPLATE.substitute(
        CATALOG_URL=url,
        ERROR_SECTION=_render_error(error),
        SUMMARY_SECTION=_render_summary(summary, destination),
    )


def _app(environ: Dict[str, object], start_response):  # type: ignore[override]
    setup_testing_defaults(environ)
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    query_string = environ.get("QUERY_STRING", "")

    if method != "GET":
        start_response(f"{HTTPStatus.METHOD_NOT_ALLOWED.value} {HTTPStatus.METHOD_NOT_ALLOWED.phrase}", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Method not allowed"]

    parsed = urlparse(f"{path}?{query_string}" if query_string else str(path))
    params = parse_qs(parsed.query)
    url = params.get("url", [DEFAULT_URL])[0]

    if parsed.path == "/api/summary":
        try:
            summary, destination = compute_summary(url)
        except Exception as exc:  # pragma: no cover - integration behaviour
            payload = {"error": str(exc), "url": url}
            body = json.dumps(payload).encode("utf-8")
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
            ]
            start_response(f"{HTTPStatus.BAD_GATEWAY.value} {HTTPStatus.BAD_GATEWAY.phrase}", headers)
            return [body]

        payload = summary.to_dict()
        payload.update({"catalog_path": str(destination), "url": url})
        body = json.dumps(payload).encode("utf-8")
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ]
        start_response(f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}", headers)
        return [body]

    if parsed.path == "/":
        summary: CatalogSummary | None = None
        destination: Path | None = None
        error: str | None = None
        try:
            summary, destination = compute_summary(url)
        except Exception as exc:  # pragma: no cover - integration behaviour
            error = str(exc)

        html = render_dashboard(url, summary, destination, error)
        body = html.encode("utf-8")
        headers = [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ]
        start_response(f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}", headers)
        return [body]

    start_response(f"{HTTPStatus.NOT_FOUND.value} {HTTPStatus.NOT_FOUND.phrase}", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not found"]


def create_app():
    """Return the WSGI application."""

    return _app


def main() -> None:  # pragma: no cover - manual entry point
    server = make_server("0.0.0.0", 8000, create_app())
    print("Serving on http://0.0.0.0:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")


if __name__ == "__main__":  # pragma: no cover
    main()

