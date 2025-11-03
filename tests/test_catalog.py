from __future__ import annotations

import io
import json
from datetime import date
from pathlib import Path
from unittest import mock

import pytest

from addon_catalog.analysis import summarize_addons
from addon_catalog.fetch import fetch_catalog
from addon_catalog.models import Addon, FileEntry
from addon_catalog.parser import parse_catalog
from addon_catalog.webapp import PageModel, _build_chart_payload, _render_versions, render_page


@pytest.fixture()
def sample_xml() -> str:
    return """
    <AddOns DateStamp="09/18/2025">
      <addon ExpirationDate="" AvailableDate="5/19/2025" Version="5.27.1" Description="Amazon WorkSpaces Client" ID="AmazonWorkSpacesClient-5.27.1">
        <SupportedPlatforms>
          <platform Description="mt440" ID="mt440"/>
          <platform Description="t655" ID="t655"/>
        </SupportedPlatforms>
        <OSes>
          <OS Description="Win11-64" Version="Win11-64" Type="Windows"/>
        </OSes>
        <architecture>x64</architecture>
        <install_command>msiexec /i AmazonWorkSpacesClient-5.27.1.msi ALLUSERS=1</install_command>
        <files>
          <package size="437948416">../AddOns/Win64/AmazonWorkSpacesClient-5.27.1.msi</package>
          <md5 size="74">../AddOns/Win64/AmazonWorkSpacesClient-5.27.1.md5</md5>
        </files>
      </addon>
      <addon ExpirationDate="" AvailableDate="8/20/2025" Version="1.2.6353" Description="Remote Desktop Connection" ID="AVDWindows365Client-1.2.6353">
        <SupportedPlatforms>
          <platform Description="mt440" ID="mt440"/>
        </SupportedPlatforms>
        <OSes>
          <OS Description="Win11-64" Version="Win11-64" Type="Windows"/>
        </OSes>
        <architecture>x64</architecture>
        <install_command>msiexec.exe /i AVDWindows365Client-1.2.6353.msi ALLUSERS=1</install_command>
        <files>
          <package size="33603584">../AddOns/Win64/AVDWindows365Client-1.2.6353.msi</package>
          <md5 size="65">../AddOns/Win64/AVDWindows365Client-1.2.6353.md5</md5>
        </files>
      </addon>
    </AddOns>
    """.strip()


def test_parse_catalog_creates_addons(sample_xml: str) -> None:
    addons = parse_catalog(sample_xml)
    assert len(addons) == 2

    first = addons[0]
    assert first.id == "AmazonWorkSpacesClient-5.27.1"
    assert first.available_date == date(2025, 5, 19)
    assert first.platforms == ["mt440", "t655"]
    assert first.files == [
        FileEntry(kind="package", path="../AddOns/Win64/AmazonWorkSpacesClient-5.27.1.msi", size=437948416),
        FileEntry(kind="md5", path="../AddOns/Win64/AmazonWorkSpacesClient-5.27.1.md5", size=74),
    ]


def test_summarize_addons_identifies_latest_versions() -> None:
    addons = [
        Addon(
            id="A-1",
            description="Example",
            version="1.0.0",
            available_date=date(2025, 1, 1),
            expiration_date=None,
            platforms=["mt440"],
            os_versions=["Win11-64"],
            os_types=["Windows"],
            architecture="x64",
            install_command=None,
            files=[],
        ),
        Addon(
            id="A-2",
            description="Example",
            version="1.1.0",
            available_date=date(2025, 2, 1),
            expiration_date=None,
            platforms=["t655"],
            os_versions=["Win11-64"],
            os_types=["Windows"],
            architecture="x64",
            install_command=None,
            files=[],
        ),
    ]

    summary = summarize_addons(addons)
    assert summary.total_addons == 2
    assert summary.unique_platforms == ["mt440", "t655"]
    assert summary.latest_versions == {"Example": "1.1.0"}
    assert summary.unique_architectures == ["x64"]
    assert summary.platform_counts == {"mt440": 1, "t655": 1}
    assert summary.os_type_counts == {"Windows": 2}
    assert summary.architecture_counts == {"x64": 2}
    assert summary.release_year_counts == {"2025": 2}
    assert len(summary.latest_addons) == 1
    latest_entry = summary.latest_addons[0]
    assert latest_entry.version == "1.1.0"
    assert latest_entry.platforms == ["t655"]
    assert latest_entry.os_types == ["Windows"]
    assert latest_entry.architecture == "x64"


def test_fetch_catalog_writes_response(tmp_path: Path) -> None:
    destination = tmp_path / "catalog.xml"
    fake_response = io.BytesIO(b"<AddOns></AddOns>")

    with mock.patch("addon_catalog.fetch.urlopen", return_value=fake_response):
        fetch_catalog("http://example.com/catalog.xml", destination)

    assert destination.read_text() == "<AddOns></AddOns>"


def test_build_chart_payload_produces_valid_json() -> None:
    payload = _build_chart_payload({"x64": 2, "x86": "3", "invalid": "skip"})
    parsed = json.loads(payload)
    assert parsed == {"labels": ["x64", "x86"], "values": [2, 3]}


def test_render_versions_matches_column_expectations(sample_xml: str) -> None:
    addons = parse_catalog(sample_xml)
    summary = summarize_addons(addons)
    table_html = _render_versions(summary.latest_addons)

    assert "<th scope=\"col\">平台</th>" not in table_html
    # Header should expose exactly five columns.
    assert table_html.count("<th scope=\"col\">") == 5
    # Architecture data should render alongside release dates per row.
    assert "<td>x64</td>" in table_html


def test_render_page_embeds_valid_chart_json(sample_xml: str) -> None:
    addons = parse_catalog(sample_xml)
    summary = summarize_addons(addons)
    page = render_page(PageModel(summary, "http://example.com"))

    def extract(identifier: str) -> dict[str, object]:
        marker = f'<script type="application/json" id="{identifier}">'  # nosec: B608
        start = page.index(marker) + len(marker)
        end = page.index("</script>", start)
        raw = page[start:end].strip()
        return json.loads(raw)

    ordered_labels = list(summary.platform_counts.keys())
    assert extract("platform-chart-data") == {
        "labels": ordered_labels,
        "values": [summary.platform_counts[key] for key in ordered_labels],
    }
