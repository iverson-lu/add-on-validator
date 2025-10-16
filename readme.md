# Add-on Catalog Analyzer

This project downloads the HP Thin Client add-on catalog XML and provides a
command-line tool to analyze its contents.

## Usage

```bash
python -m addon_catalog --url https://ftp.hp.com/pub/tcimages/EasyUpdate/Images/addoncatalog.xml
```

The command stores the XML in `.cache/addon_catalog.xml` and prints summary
statistics. Add `--format json` to emit a machine-readable report.

## Development

Install optional dependencies and run the tests:

```bash
pip install .[dev]
pytest
```
