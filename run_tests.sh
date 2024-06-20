#!/bin/bash

# This script assumes that the pyvenv installed in PYDIR exists, and
# has ukechords and all its dependencies.

if [ -z "$UKECHORDS_PYDIR" ]; then
    UKECHORDS_PYDIR="${HOME}/.local/pyvenv/ukechords/"
fi

. "$UKECHORDS_PYDIR/bin/activate"

export COVERAGE_CORE=sysmon
pytest . "$@"
