#!/bin/bash

# This script assumes that the pyvenv installed in UKECHORDS_PYDIR
# exists, and has ukechords and all its dependencies.

# With coverage: ./run_tests.sh  --cov --cov-report=html --cov-branch

if [ -z "$UKECHORDS_PYDIR" ]; then
    UKECHORDS_PYDIR="${HOME}/.local/pyvenv/ukechords/"
fi

. "$UKECHORDS_PYDIR/bin/activate"

export COVERAGE_CORE=sysmon
pytest . "$@"
