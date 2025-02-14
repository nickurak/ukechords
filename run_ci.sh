#!/bin/bash

# This script assumes that the pyvenv installed in UKECHORDS_PYDIR
# exists, and has ukechords and all its dependencies.

if [ -z "$UKECHORDS_PYDIR" ]; then
    UKECHORDS_PYDIR="${HOME}/.local/pyvenv/ukechords/"
fi

. "$UKECHORDS_PYDIR/bin/activate"

set -e

flake8 . && echo 'flake8 passed' || exit $?

find . -name '*.py' | grep -v flycheck | xargs -d '\n' pylint

mypy --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs .

export COVERAGE_CORE=sysmon
pytest . "$@"
