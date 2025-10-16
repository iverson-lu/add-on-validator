"""Utilities for downloading the add-on catalog XML."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import BinaryIO
from urllib.request import urlopen


def _write_stream_to_file(stream: BinaryIO, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as fh:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            fh.write(chunk)


def fetch_catalog(url: str, destination: Path, *, timeout: float = 10.0) -> Path:
    """Download the catalog XML from *url* and store it at *destination*.

    Parameters
    ----------
    url:
        The HTTP(S) URL pointing to the XML document.
    destination:
        Local file path where the XML should be written. Parent directories are
        created automatically.
    timeout:
        Network timeout in seconds when opening the URL. Defaults to 10 seconds.

    Returns
    -------
    Path
        The destination path supplied by the caller.
    """

    with contextlib.closing(urlopen(url, timeout=timeout)) as response:
        _write_stream_to_file(response, destination)
    return destination


__all__ = ["fetch_catalog"]
