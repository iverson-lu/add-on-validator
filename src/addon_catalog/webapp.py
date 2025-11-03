"""面向命令行分析工具的轻量级 Web 展示界面。"""

from __future__ import annotations

import html
import json
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Mapping, Optional

from .analysis import CatalogSummary, LatestAddonEntry, summarize_addons
from .fetch import fetch_catalog
from .parser import parse_catalog

DEFAULT_URL = "https://ftp.hp.com/pub/tcimages/EasyUpdate/Images/addoncatalog.xml"
CACHE_PATH = Path(".cache/web_addon_catalog.xml")
TEMPLATE_PATH = Path(__file__).with_name("templates").joinpath("index.html")


@dataclass(frozen=True)
class PageModel:
    summary: CatalogSummary
    current_url: str
    selected_platform: str = ""
    selected_os: str = ""
    selected_architecture: str = ""
    error: Optional[str] = None


def _load_summary(url: str) -> CatalogSummary:
    destination = fetch_catalog(url, CACHE_PATH)
    xml_text = Path(destination).read_text(encoding="utf-8")
    addons = parse_catalog(xml_text)
    return summarize_addons(addons)


def _render_versions(latest_addons: list[LatestAddonEntry]) -> str:
    if not latest_addons:
        return '<div class="empty-state">当前数据源未提供任何版本信息。</div>'

    rows = []
    for entry in latest_addons:
        os_types = "<br />".join(html.escape(os_type) for os_type in entry.os_types)
        architecture = html.escape(entry.architecture or "未指定")
        available = entry.available_date.isoformat() if entry.available_date else "未知"
        rows.append(
            "<tr>"
            f"<td>{html.escape(entry.description)}</td>"
            f"<td>{html.escape(entry.version)}</td>"
            f"<td>{os_types}</td>"
            f"<td>{architecture}</td>"
            f"<td>{available}</td>"
            "</tr>"
        )
    table = "".join(rows)
    return (
        "<table><thead><tr>"
        "<th scope=\"col\">描述</th>"
        "<th scope=\"col\">最新版本</th>"
        "<th scope=\"col\">操作系统</th>"
        "<th scope=\"col\">架构</th>"
        "<th scope=\"col\">发布日期</th>"
        "</tr></thead><tbody>{}</tbody></table>".format(table)
    )


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
    labels: list[str] = []
    values: list[int] = []
    for label, raw_value in counts.items():
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            continue
        labels.append(str(label))
        values.append(value)
    payload = {"labels": labels, "values": values}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def render_page(model: PageModel) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    summary = model.summary
    filtered_addons = _filter_addons(
        summary.latest_addons,
        model.selected_platform,
        model.selected_os,
        model.selected_architecture,
    )
    query_for_clear = urllib.parse.urlencode({"url": model.current_url})
    replacements = {
        "{{CURRENT_URL}}": html.escape(model.current_url),
        "{{ERROR_SECTION}}": _render_error(model.error),
        "{{TOTAL_ADDONS}}": str(summary.total_addons),
        "{{PLATFORM_COUNT}}": str(len(summary.unique_platforms)),
        "{{OS_COUNT}}": str(len(summary.unique_os_types)),
        "{{ARCH_COUNT}}": str(len(summary.unique_architectures)),
        "{{PLATFORM_OPTIONS}}": _render_select_options(
            list(summary.platform_counts.keys()),
            model.selected_platform,
            "全部平台",
        ),
        "{{OS_OPTIONS}}": _render_select_options(
            list(summary.os_type_counts.keys()),
            model.selected_os,
            "全部操作系统",
        ),
        "{{ARCH_OPTIONS}}": _render_select_options(
            list(summary.architecture_counts.keys()),
            model.selected_architecture,
            "全部架构",
        ),
        "{{FILTERED_COUNT}}": str(len(filtered_addons)),
        "{{VERSION_TABLE}}": _render_versions(filtered_addons),
        "{{CLEAR_FILTER_URL}}": f"/?{query_for_clear}",
        "{{PLATFORM_CHART_DATA}}": _build_chart_payload(summary.platform_counts),
        "{{OS_CHART_DATA}}": _build_chart_payload(summary.os_type_counts),
        "{{ARCH_CHART_DATA}}": _build_chart_payload(summary.architecture_counts),
        "{{RELEASE_CHART_DATA}}": _build_chart_payload(summary.release_year_counts),
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
        selected_platform = params.get("platform", [""])[0].strip()
        selected_os = params.get("os", [""])[0].strip()
        selected_architecture = params.get("arch", [""])[0].strip()

        try:
            summary = _load_summary(current_url)
            error = None
        except Exception as exc:  # pragma: no cover - 用户界面中的错误展示
            summary = CatalogRequestHandler.model_cache.summary
            error = f"无法加载目录：{exc}"

        model = PageModel(
            summary=summary,
            current_url=current_url,
            selected_platform=selected_platform,
            selected_os=selected_os,
            selected_architecture=selected_architecture,
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
