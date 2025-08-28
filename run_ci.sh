#!/bin/bash

set -Eeuo pipefail

TEST_DIRS=(tests)
SRC_DIRS=(src "${TEST_DIRS[@]}")

RUNNERS=(run_flake8 run_pylint run_mypy run_pytest)
[ "$#" -gt 0 ] && RUNNERS=("run_$1") && shift

FIRST_RC=0 && FAILURES=()
fail() {
    RC=$1 && shift
    [ "$FIRST_RC" -eq 0 ] && FIRST_RC=$RC
    FAILURES+=("$* returned error: $RC")
}

get_files() { find "${SRC_DIRS[@]}" -name '*.py' | grep -vE 'flycheck|/[.]'; }
get_test_files() { find "${TEST_DIRS[@]}" -name '*.py' | grep -vE 'flycheck|/[.]'; }
xargs_uv() { xargs -d '\n' uv run "$@"; }

run_flake8() { get_files | (xargs_uv flake8 "$@" && echo 'flake8 passed'); }
run_pylint() { get_files | xargs_uv pylint "$@"; }
run_mypy() { get_files | xargs_uv mypy --strict "$@"; }
run_pytest() { get_test_files | xargs_uv pytest "$@"; }
run_pytest-cov() { run_pytest --cov --cov-report=html --cov-branch "$@"; }

for RUNNER in "${RUNNERS[@]}"; do
    "$RUNNER" "$@" || fail $? "$RUNNER"
done
[ "$FIRST_RC" -eq 0 ] && exit

echo "Error summary:"
(IFS=$'\n' && echo "${FAILURES[*]}")

exit "$FIRST_RC"
