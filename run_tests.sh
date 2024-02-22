#!/bin/bash

PYDIR="${HOME}/.local/pyvenv/ukechords/"
. "$PYDIR/bin/activate"

export COVERAGE_CORE=sysmon
pytest . "$@"
