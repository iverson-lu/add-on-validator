"""面向命令行分析工具的轻量级 Web 展示界面。"""

from __future__ import annotations

import html
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from .analysis import CatalogSummary, summarize_addons
from .fetch import fetch_catalog
from .parser import parse_catalog

DEFAULT_URL = "https://ftp.hp.com/pub/tcimages/EasyUpdate/Images/addoncatalog.xml"
CACHE_PATH = Path(".cache/web_addon_catalog.xml")
TEMPLATE_PATH = Path(__file__).with_name("templates").joinpath("index.html")


@dataclass(frozen=True)
class PageModel:
    summary: CatalogSummary
    current_url: str
    error: Optional[str] = None


def _load_summary(url: str) -> CatalogSummary:
    destination = fetch_catalog(url, CACHE_PATH)
    xml_text = Path(destination).read_text(encoding="utf-8")
    addons = parse_catalog(xml_text)
    return summarize_addons(addons)


def _render_chips(items: list[str]) -> str:
    if not items:
        return "<span class=\"chip\">暂无数据</span>"
    return "".join(f"<span class=\"chip\">{html.escape(item)}</span>" for item in items)


def _render_versions(latest_versions: dict[str, str]) -> str:
    if not latest_versions:
        return '<div class="empty-state">当前数据源未提供任何版本信息。</div>'

    rows = []
    for desc, version in latest_versions.items():
        rows.append(
            "<tr><td>{}</td><td>{}</td></tr>".format(
                html.escape(desc), html.escape(version)
            )
        )
    table = "".join(rows)
    return (
        "<table><thead><tr><th scope=\"col\">描述</th><th scope=\"col\">最新版本</th>"
        "</tr></thead><tbody>{}</tbody></table>".format(table)
    )


def _render_error(error: Optional[str]) -> str:
    if not error:
        return ""
    return f'<div class="error-banner">{html.escape(error)}</div>'


def render_page(model: PageModel) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    summary = model.summary
    replacements = {
        "{{CURRENT_URL}}": html.escape(model.current_url),
        "{{ERROR_SECTION}}": _render_error(model.error),
        "{{TOTAL_ADDONS}}": str(summary.total_addons),
        "{{PLATFORM_COUNT}}": str(len(summary.unique_platforms)),
        "{{PLATFORM_CHIPS}}": _render_chips(summary.unique_platforms),
        "{{OS_COUNT}}": str(len(summary.unique_os_types)),
        "{{OS_CHIPS}}": _render_chips(summary.unique_os_types),
        "{{VERSION_TABLE}}": _render_versions(dict(summary.latest_versions)),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


class CatalogRequestHandler(BaseHTTPRequestHandler):
    model_cache = PageModel(summarize_addons([]), DEFAULT_URL)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler uses camelCase
        parsed = urllib.parse.urlsplit(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        raw_url = params.get("url", [DEFAULT_URL])[0]
        current_url = raw_url.strip() or DEFAULT_URL

        try:
            summary = _load_summary(current_url)
            error = None
        except Exception as exc:  # pragma: no cover - 用户界面中的错误展示
            summary = CatalogRequestHandler.model_cache.summary
            error = f"无法加载目录：{exc}"

        model = PageModel(summary=summary, current_url=current_url, error=error)
        CatalogRequestHandler.model_cache = model

        body = render_page(model).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - keep signature
        return  # 静默日志，保持控制台整洁


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), CatalogRequestHandler)
    print(f"Serving dashboard on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - 手动终止
        pass
    finally:
        server.server_close()


if __name__ == "__main__":  # pragma: no cover - 模块直接执行
    run()
