from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from unittest import mock

import pytest

from addon_catalog.analysis import summarize_addons
from addon_catalog.fetch import fetch_catalog
from addon_catalog.models import Addon, FileEntry
from addon_catalog.parser import parse_catalog


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
    assert summary.unique_architectures == ["x64"]
    assert summary.latest_versions == {"Example": "1.1.0"}
    assert summary.platform_counts == {"mt440": 1, "t655": 1}
    assert summary.os_type_counts == {"Windows": 2}
    assert summary.architecture_counts == {"x64": 2}
    assert summary.monthly_release_counts == {"2025-01": 1, "2025-02": 1}
    assert len(summary.latest_version_details) == 1
    assert summary.latest_version_details[0].version == "1.1.0"


def test_fetch_catalog_writes_response(tmp_path: Path) -> None:
    destination = tmp_path / "catalog.xml"
    fake_response = io.BytesIO(b"<AddOns></AddOns>")

    with mock.patch("addon_catalog.fetch.urlopen", return_value=fake_response):
        fetch_catalog("http://example.com/catalog.xml", destination)

    assert destination.read_text() == "<AddOns></AddOns>"
