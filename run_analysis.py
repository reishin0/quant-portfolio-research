"""Execute a deterministic copy of the research notebook and export a report."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import webbrowser

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--open', action='store_true', help='Open the finished report in a browser.')
    args = parser.parse_args()
    print('Loading the portfolio-construction notebook...', flush=True)
    nb = nbformat.read(ROOT / 'portfolio_construction.ipynb', as_version=4)
    # Use deterministic data for automated validation; the source defaults to Yahoo.
    # The editable source notebook is not changed.
    config = next(cell for cell in nb.cells if cell.id == 'configuration')
    config.source = ('DATA_MODE = "synthetic"\nSTART_DATE = "2020-01-01"\n'
                     'END_DATE = "2024-08-23"\nANNUAL_RISK_FREE_RATE = 0.03\n'
                     'MAX_WEIGHT = 0.35\nTRAINING_DAYS = 504\n'
                     'TRANSACTION_COST_BPS = 10\nANNUAL_SHORT_BORROW_BPS = 100\n'
                     'KELLY_FRACTION = 0.50\nBAB_GROSS_LIMIT = 2.0\n'
                     'FACTOR_FILE = "data/F-F_Research_Data_5_Factors_2x3_monthly.csv"\n'
                     'FACTOR_UNIT = "percent"\nRANDOM_SEED = 42\n')
    nbformat.validate(nb)
    print('Starting its local Python kernel and executing all cells...', flush=True)
    NotebookClient(nb, timeout=300, startup_timeout=60, kernel_name='portfolio-research',
                   resources={'metadata': {'path': str(ROOT)}}, allow_errors=False).execute()
    output = ROOT / 'outputs' / datetime.now(timezone.utc).strftime('validation_report_%Y%m%dT%H%M%S_%fZ')
    output.mkdir(parents=True, exist_ok=False)
    nbformat.write(nb, output / 'executed_portfolio_construction.ipynb')
    print('Notebook finished. Creating the HTML report...', flush=True)
    exporter = HTMLExporter(template_name='lab')
    exporter.exclude_input = True
    body, _ = exporter.from_notebook_node(nb)
    report = output / 'portfolio_construction_report.html'
    report.write_text(body, encoding='utf-8')
    # Record direct package versions, without local paths or environment values.
    from importlib.metadata import version
    packages = ['numpy', 'pandas', 'scipy', 'matplotlib', 'yfinance', 'jupyterlab', 'ipykernel', 'nbclient', 'nbconvert']
    versions = {'python': sys.version.split()[0], 'packages': {name: version(name) for name in packages},
                'mode': 'synthetic validation', 'notebook_execution': 'all cells passed'}
    (output / 'environment.json').write_text(json.dumps(versions, indent=2), encoding='utf-8')
    print('SUCCESS: every portfolio-construction notebook cell completed.')
    print(f'Report: {report}')
    if args.open:
        webbrowser.open(report.as_uri())


if __name__ == '__main__':
    main()
