#!/bin/bash

# This script assumes that the pyvenv installed in PYDIR exists, and
# has ukechords and all its dependencies.

PYDIR="${HOME}/.local/pyvenv/ukechords/"
. "$PYDIR/bin/activate"

ARGS="$@"

[ "${#ARGS[@]}" -lt 1 ] && ARGS=(".")

mypy --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs "${ARGS[*]}"
