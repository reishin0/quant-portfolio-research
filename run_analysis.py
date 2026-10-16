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
    parser.add_argument('--mode', choices=['snapshot', 'submission', 'synthetic', 'yahoo'], default='snapshot',
                        help='Default: offline frozen prices; Yahoo explicitly refreshes prices.')
    args = parser.parse_args()
    print('Loading the portfolio-construction notebook...', flush=True)
    nb = nbformat.read(ROOT / 'portfolio_construction.ipynb', as_version=4)
    # This describes the checked-in display snapshot, not the run about to start.
    nb.metadata.pop('executed_snapshot', None)
    # Override only the data-mode assignment; retain all source research settings.
    config = next(cell for cell in nb.cells if cell.id == 'configuration')
    import re
    config.source, replacements = re.subn(r'^DATA_MODE\s*=.*$',
                                           f'DATA_MODE = "{args.mode}"',
                                           config.source, flags=re.MULTILINE)
    if replacements != 1:
        raise ValueError('Notebook must contain exactly one DATA_MODE assignment.')
    nbformat.validate(nb)
    print('Starting its local Python kernel and executing all cells...', flush=True)
    NotebookClient(nb, timeout=900, startup_timeout=60, kernel_name='portfolio-research',
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
    packages = ['numpy', 'pandas', 'scipy', 'matplotlib', 'yfinance', 'jupyterlab', 'ipykernel', 'nbclient', 'nbconvert', 'openpyxl', 'pandas_market_calendars', 'exchange_calendars', 'scikit-learn', 'statsmodels']
    import hashlib
    from importlib.metadata import distributions
    versions = {'code_sha256': hashlib.sha256('\n'.join(c.source for c in nb.cells if c.cell_type == 'code').encode()).hexdigest(),
                'installed_packages': {d.metadata['Name']: d.version for d in distributions()},
                'python': sys.version.split()[0], 'packages': {name: version(name) for name in packages},
                'mode': args.mode, 'notebook_execution': 'all cells passed'}
    (output / 'environment.json').write_text(json.dumps(versions, indent=2), encoding='utf-8')
    print('SUCCESS: every portfolio-construction notebook cell completed.')
    print(f'Report: {report}')
    if args.open:
        webbrowser.open(report.as_uri())


if __name__ == '__main__':
    main()
