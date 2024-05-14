#!/bin/bash

# This script assumes that the pyvenv installed in PYDIR exists, and
# has ukechords and all its dependencies.

PYDIR="${HOME}/.local/pyvenv/ukechords/"
. "$PYDIR/bin/activate"

set -e

flake8 . && echo 'flake8 passed'
find . -name '*.py' | grep -v flycheck | xargs -d '\n' pylint

mypy .

export COVERAGE_CORE=sysmon
pytest . "$@"
