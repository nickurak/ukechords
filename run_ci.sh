#!/usr/bin/env bash

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

mapfile -d '' FILES < <(find "${SRC_DIRS[@]}" ! -name '*flycheck*' ! -name '.*' -name '*.py' -print0)
mapfile -d '' TEST_FILES < <(find "${TEST_DIRS[@]}" ! -name '*flycheck*' ! -name '.*' -name '*.py' -name '*.py' -print0)

xargs_uv() { xargs -d '\n' uv run "$@"; }

run_flake8() { uv run flake8 "$@" "${FILES[@]}" && echo 'flake8 passed'; }
run_pylint() { uv run pylint "$@" "${FILES[@]}"; }
run_mypy() { uv run mypy --strict "$@" "${FILES[@]}"; }
run_pytest() { uv run pytest "$@" "${TEST_FILES[@]}"; }
run_pytest-cov() { run_pytest --cov --cov-report=html --cov-branch "$@"; }

for RUNNER in "${RUNNERS[@]}"; do
    "$RUNNER" "$@" || fail $? "$RUNNER"
done
[ "$FIRST_RC" -eq 0 ] && exit

echo "Error summary:"
(IFS=$'\n' && echo "${FAILURES[*]}")

exit "$FIRST_RC"
