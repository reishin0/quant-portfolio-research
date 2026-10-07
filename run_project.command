#!/bin/sh
set -eu
cd "$(dirname "$0")"
for portfolio_python in python3.13 python3.12 python3.11 python3; do
    if command -v "$portfolio_python" >/dev/null 2>&1 && "$portfolio_python" -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,13) else 1)' >/dev/null 2>&1; then
        exec "$portfolio_python" launch.py "$@"
    fi
done
printf '%s\n' 'Install Python 3.11, 3.12 or 3.13 from https://www.python.org/downloads/ then try again.'
exit 2
