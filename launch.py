"""Reproducible setup, local kernel and report runner for the research project."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV = ROOT / '.venv'
PYTHON = VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
REQUIREMENTS = ROOT / 'requirements.txt'


def run(command, *, env, capture=False):
    return subprocess.run([str(part) for part in command], cwd=ROOT, env=env,
                          check=True, text=True, encoding='utf-8', errors='replace',
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None)


def main():
    parser = argparse.ArgumentParser(description='Set up and open the portfolio-construction research notebook.')
    parser.add_argument('--check', action='store_true', help='Execute the research notebook and export HTML without opening a browser.')
    parser.add_argument('--mode', choices=['submission', 'synthetic', 'yahoo'], default='submission',
                        help='Data for --check/--report; defaults to the frozen submission.')
    parser.add_argument('--report', action='store_true', help='Execute validation and open the HTML report instead of Jupyter.')
    parser.add_argument('--repair', action='store_true', help='Recheck/install dependencies without removing the environment.')
    args = parser.parse_args()
    if not (3, 11) <= sys.version_info[:2] <= (3, 13):
        print('Please install 64-bit Python 3.11, 3.12 or 3.13 from https://www.python.org/downloads/ .')
        print('Then run run_project.bat on Windows or: python3 launch.py')
        return 2

    # Keep setup writes local, including on restricted or managed computers.
    temporary = ROOT / '.setup-tmp'
    temporary.mkdir(exist_ok=True)
    env = dict(os.environ, TEMP=str(temporary), TMP=str(temporary), TMPDIR=str(temporary),
               PYTHONIOENCODING='utf-8', PYTHONUTF8='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
    # Do not inherit another environment's Python package search path.
    env.pop('PYTHONHOME', None)
    env.pop('PYTHONPATH', None)
    print('1/4  Checking a private Python environment for this folder...', flush=True)
    if not PYTHON.exists():
        run([sys.executable, '-m', 'venv', VENV], env=env)
    version_result = run([PYTHON, '-c', 'import sys; print("%s.%s" % sys.version_info[:2])'], env=env, capture=True)
    actual = tuple(map(int, version_result.stdout.strip().splitlines()[-1].split('.')))
    if not (3, 11) <= actual <= (3, 13):
        raise RuntimeError('This folder has an older .venv. Rename that .venv folder, then launch again with Python 3.11-3.13.')
    pip_result = subprocess.run([str(PYTHON), '-m', 'pip', '--version'], cwd=ROOT, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if pip_result.returncode:
        run([PYTHON, '-m', 'ensurepip', '--upgrade'], env=env)

    fingerprint = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    marker = VENV / '.portfolio-requirements.sha256'
    ready = marker.exists() and marker.read_text().strip() == fingerprint
    print('2/4  Checking packages (first installation needs internet and may take several minutes)...', flush=True)
    if args.repair or not ready:
        run([PYTHON, '-m', 'pip', 'install', '--no-cache-dir', '-r', REQUIREMENTS], env=env)
    run([PYTHON, '-m', 'pip', 'check'], env=env)
    run([PYTHON, '-c', 'import numpy, pandas, scipy, matplotlib, yfinance, jupyterlab, ipykernel, nbclient, nbconvert, portfolio_tools, research_extensions; print("Imports OK")'], env=env)
    marker.write_text(fingerprint + '\n')

    print('3/4  Preparing the notebook kernel inside this environment...', flush=True)
    run([PYTHON, '-m', 'ipykernel', 'install', '--sys-prefix', '--name', 'portfolio-research',
         '--display-name', 'Portfolio construction (this folder)'], env=env, capture=True)
    env['JUPYTER_PATH'] = str(VENV / 'share' / 'jupyter')
    env['JUPYTER_CONFIG_DIR'] = str(VENV / 'jupyter-config')
    env['JUPYTER_DATA_DIR'] = str(VENV / 'jupyter-data')
    env['JUPYTER_RUNTIME_DIR'] = str(VENV / 'jupyter-runtime')
    env['IPYTHONDIR'] = str(VENV / 'ipython')
    env['MPLCONFIGDIR'] = str(VENV / 'matplotlib')
    for key in ['JUPYTER_CONFIG_DIR', 'JUPYTER_DATA_DIR', 'JUPYTER_RUNTIME_DIR', 'IPYTHONDIR', 'MPLCONFIGDIR']:
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    if args.check or args.report:
        print(f'4/4  Running {args.mode} analysis and writing a report...', flush=True)
        command = [PYTHON, ROOT / 'run_analysis.py', '--mode', args.mode]
        if args.report and not args.check:
            command.append('--open')
        run(command, env=env)
    else:
        print('4/4  Opening portfolio_construction.ipynb in your browser.', flush=True)
        print('In the notebook choose Run > Run All Cells. Keep this terminal open.', flush=True)
        print('To stop Jupyter later, press Ctrl+C in this terminal.', flush=True)
        run([PYTHON, '-m', 'jupyterlab', '--ServerApp.ip=127.0.0.1',
             '--ServerApp.port=8888', '--ServerApp.port_retries=20',
             f'--ServerApp.root_dir={ROOT}', '--LabApp.default_url=/lab/tree/portfolio_construction.ipynb'], env=env)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nStopped. Your notebook and data have been kept.')
        raise SystemExit(130)
    except Exception as exc:
        # Do not save process environments or credentials in a diagnostic log.
        print(f'\nSetup stopped: {exc}')
        print('Check your internet connection and that this extracted folder is writable.')
        print('Try: python launch.py --repair')
        print('See README.md > Troubleshooting. Nothing was deleted.')
        raise SystemExit(1)
