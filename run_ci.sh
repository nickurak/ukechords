#!/bin/bash

set -Eeuo pipefail

SRC_DIRS=(src tests)

uv run flake8 "${SRC_DIRS[@]}" && echo 'flake8 passed'

find "${SRC_DIRS[@]}" -name '*.py' | grep -v flycheck | xargs -d '\n' uv run pylint

uv run mypy --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs "${SRC_DIRS[@]}"

export COVERAGE_CORE=sysmon
uv run pytest "$@" "${SRC_DIRS[@]}"
