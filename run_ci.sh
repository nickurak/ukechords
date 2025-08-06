#!/bin/bash

set -Eeuo pipefail

SRC_DIRS=(src tests)

FIRST_RC=0
FAILURES=()
fail() {
    RC=$1 && shift
    [ "$FIRST_RC" -eq 0 ] && FIRST_RC=$RC
    FAILURES+=("$* returned error: $RC")
}

(uv run flake8 "${SRC_DIRS[@]}" && echo 'flake8 passed') || fail $? flake8

find "${SRC_DIRS[@]}" -name '*.py' | grep -v flycheck | xargs -d '\n' uv run pylint || fail $? pylint

uv run mypy --strict "${SRC_DIRS[@]}" || fail $? mypy

export COVERAGE_CORE=sysmon
uv run pytest --no-header "$@" "${SRC_DIRS[@]}" || fail $? pytest

[ "$FIRST_RC" -eq 0 ] && exit

echo "Error summary:"
for FAILURE in "${FAILURES[@]}"; do
    echo "$FAILURE"
done

exit "$FIRST_RC"
