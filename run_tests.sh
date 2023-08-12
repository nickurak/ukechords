#!/bin/bash

PYDIR="${HOME}/.local/pyvenv/ukechords/"
. "$PYDIR/bin/activate"

pytest . "$@"
