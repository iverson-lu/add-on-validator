"""面向命令行分析工具的轻量级 Web 展示界面。"""

from __future__ import annotations

import html
import json
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .analysis import CatalogSummary, LatestAddonEntry, summarize_addons
from .fetch import fetch_catalog
from .models import Addon
from .parser import parse_catalog

DEFAULT_URL = "https://ftp.hp.com/pub/tcimages/EasyUpdate/Images/addoncatalog.xml"
CACHE_PATH = Path(".cache/web_addon_catalog.xml")
TEMPLATE_PATH = Path(__file__).with_name("templates").joinpath("index.html")


@dataclass(frozen=True)
class PageModel:
    summary: CatalogSummary
    current_url: str
    selected_platforms: Sequence[str] = ()
    selected_os_types: Sequence[str] = ()
    selected_architectures: Sequence[str] = ()
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


def _render_versions(latest_details: Sequence[Addon]) -> str:
    if not latest_details:
        return '<div class="empty-state">当前数据源未提供任何版本信息。</div>'

    rows = []
    for addon in latest_details:
        description = addon.description or addon.id
        platforms = ", ".join(addon.platforms) or "—"
        os_types = ", ".join(addon.os_types) or "—"
        os_versions = ", ".join(addon.os_versions) or "—"
        architecture = addon.architecture or "—"
        available = addon.available_date.isoformat() if addon.available_date else "—"
        rows.append(
            (
                "<tr>"
                f"<td>{html.escape(description)}</td>"
                f"<td>{html.escape(addon.version)}</td>"
                f"<td>{html.escape(platforms)}</td>"
                f"<td>{html.escape(os_types)}</td>"
                f"<td>{html.escape(os_versions)}</td>"
                f"<td>{html.escape(architecture)}</td>"
                f"<td>{html.escape(available)}</td>"
                "</tr>"
            )
        )
    table = "".join(rows)
    return (
        "<table><thead><tr>"
        "<th scope=\"col\">描述</th>"
        "<th scope=\"col\">最新版本</th>"
        "<th scope=\"col\">平台</th>"
        "<th scope=\"col\">操作系统类型</th>"
        "<th scope=\"col\">操作系统版本</th>"
        "<th scope=\"col\">架构</th>"
        "<th scope=\"col\">发布日期</th>"
        "</tr></thead><tbody>{}</tbody></table>".format(table)
    )


def _render_filter_options(items: Iterable[str], selected: Sequence[str]) -> str:
    options: list[str] = []
    selected_set = set(selected)
    for item in items:
        is_selected = " selected" if item in selected_set else ""
        options.append(
            f'<option value="{html.escape(item)}"{is_selected}>{html.escape(item)}</option>'
        )
    if not options:
        return '<option value="" disabled>暂无可选项</option>'
    return "".join(options)


def _matches_filters(addon: Addon, model: PageModel) -> bool:
    if model.selected_platforms:
        if not set(addon.platforms).intersection(model.selected_platforms):
            return False
    if model.selected_os_types:
        if not set(addon.os_types).intersection(model.selected_os_types):
            return False
    if model.selected_architectures:
        architecture = addon.architecture or ""
        if architecture not in model.selected_architectures:
            return False
    return True


def _build_chart_payload(labels: Sequence[str], values: Sequence[int]) -> str:
    return json.dumps({"labels": list(labels), "values": list(values)}, ensure_ascii=False)


def _render_error(error: Optional[str]) -> str:
    if not error:
        return ""
    return f'<div class="error-banner">{html.escape(error)}</div>'


def _render_select_options(
    values: list[str], selected: str, placeholder: str
) -> str:
    options = []
    selected_attr = " selected" if not selected else ""
    options.append(
        f'<option value=""{selected_attr}>{html.escape(placeholder)}</option>'
    )
    for value in values:
        attr = " selected" if value == selected else ""
        options.append(
            f'<option value="{html.escape(value)}"{attr}>{html.escape(value)}</option>'
        )
    return "".join(options)


def _filter_addons(
    entries: list[LatestAddonEntry],
    platform: str,
    os_type: str,
    architecture: str,
) -> list[LatestAddonEntry]:
    def matches(entry: LatestAddonEntry) -> bool:
        if platform and platform not in entry.platforms:
            return False
        if os_type and os_type not in entry.os_types:
            return False
        if architecture and architecture != (entry.architecture or ""):
            return False
        return True

    return [entry for entry in entries if matches(entry)]


def _build_chart_payload(counts: Mapping[str, int]) -> str:
    labels = list(counts.keys())
    values = list(counts.values())
    payload = {"labels": labels, "values": values}
    return json.dumps(payload, ensure_ascii=False)


def render_page(model: PageModel) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    summary = model.summary
    filtered_details = [
        addon for addon in summary.latest_version_details if _matches_filters(addon, model)
    ]

    replacements = {
        "{{CURRENT_URL}}": html.escape(model.current_url),
        "{{ERROR_SECTION}}": _render_error(model.error),
        "{{TOTAL_ADDONS}}": str(summary.total_addons),
        "{{PLATFORM_COUNT}}": str(len(summary.unique_platforms)),
        "{{PLATFORM_CHIPS}}": _render_chips(summary.unique_platforms),
        "{{OS_COUNT}}": str(len(summary.unique_os_types)),
        "{{OS_CHIPS}}": _render_chips(summary.unique_os_types),
        "{{PLATFORM_FILTER_OPTIONS}}": _render_filter_options(
            summary.unique_platforms, model.selected_platforms
        ),
        "{{OS_FILTER_OPTIONS}}": _render_filter_options(
            summary.unique_os_types, model.selected_os_types
        ),
        "{{ARCH_FILTER_OPTIONS}}": _render_filter_options(
            summary.unique_architectures, model.selected_architectures
        ),
        "{{VERSION_TABLE}}": _render_versions(filtered_details),
        "{{FILTERED_COUNT}}": str(len(filtered_details)),
        "{{PLATFORM_CHART_JSON}}": _build_chart_payload(
            summary.platform_counts.keys(), summary.platform_counts.values()
        ),
        "{{OS_CHART_JSON}}": _build_chart_payload(
            summary.os_type_counts.keys(), summary.os_type_counts.values()
        ),
        "{{ARCH_CHART_JSON}}": _build_chart_payload(
            summary.architecture_counts.keys(), summary.architecture_counts.values()
        ),
        "{{MONTHLY_CHART_JSON}}": _build_chart_payload(
            summary.monthly_release_counts.keys(), summary.monthly_release_counts.values()
        ),
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
        selected_platforms = tuple(filter(None, params.get("platform", [])))
        selected_os_types = tuple(filter(None, params.get("os_type", [])))
        selected_architectures = tuple(filter(None, params.get("architecture", [])))

        try:
            summary = _load_summary(current_url)
            error = None
        except Exception as exc:  # pragma: no cover - 用户界面中的错误展示
            summary = CatalogRequestHandler.model_cache.summary
            error = f"无法加载目录：{exc}"

        model = PageModel(
            summary=summary,
            current_url=current_url,
            selected_platforms=selected_platforms,
            selected_os_types=selected_os_types,
            selected_architectures=selected_architectures,
            error=error,
        )
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
