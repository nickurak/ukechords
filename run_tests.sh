#!/bin/bash

# This script assumes that the pyvenv installed in PYDIR exists, and
# has ukechords and all its dependencies.

PYDIR="${HOME}/.local/pyvenv/ukechords/"
. "$PYDIR/bin/activate"

export COVERAGE_CORE=sysmon
pytest . "$@"
