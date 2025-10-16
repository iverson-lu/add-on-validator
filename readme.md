# Add-on Catalog Analyzer

This project downloads the HP Thin Client add-on catalog XML and provides a
command-line tool to analyze its contents. A lightweight web dashboard is also
available for a more visual overview.

## Usage

```bash
python -m addon_catalog --url https://ftp.hp.com/pub/tcimages/EasyUpdate/Images/addoncatalog.xml
```

The command stores the XML in `.cache/addon_catalog.xml` and prints summary
statistics. Add `--format json` to emit a machine-readable report.

## Web Dashboard

Launch the interactive dashboard with the built-in HTTP server:

```bash
PYTHONPATH=src python -m addon_catalog.webapp
```

Then open `http://127.0.0.1:8000/` in your browser. The interface uses the
same catalog analysis pipeline and presents key metrics with a modern visual
style. Use the form at the top of the page to analyze a different catalog URL.

## Development

Install optional dependencies and run the tests:

```bash
pip install .[dev]
pytest
```
