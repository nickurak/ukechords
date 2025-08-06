#!/bin/bash

set -Eeuo pipefail

TEST_DIRS=(tests)
SRC_DIRS=(src "${TEST_DIRS[@]}")

FIRST_RC=0
FAILURES=()
fail() {
    RC=$1 && shift
    [ "$FIRST_RC" -eq 0 ] && FIRST_RC=$RC
    FAILURES+=("$* returned error: $RC")
}

get_files() { find "${SRC_DIRS[@]}" -name '*.py' | grep -v flycheck; }
get_test_files() { find "${TEST_DIRS[@]}" -name '*.py' | grep -v flycheck; }
xargs_uv() { xargs -d '\n' uv run "$@"; }

export COVERAGE_CORE=sysmon
get_files | (xargs_uv flake8 && echo 'flake8 passed') || fail $? flake8
get_files | xargs_uv pylint || fail $? pylint
get_files | xargs_uv mypy --strict || fail $? mypy
get_test_files | xargs_uv pytest "$@" || fail $? pytest

[ "$FIRST_RC" -eq 0 ] && exit

echo "Error summary:"
for FAILURE in "${FAILURES[@]}"; do
    echo "$FAILURE"
done

exit "$FIRST_RC"
