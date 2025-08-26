#!/bin/bash

set -Eeuo pipefail

TEST_DIRS=(tests)
SRC_DIRS=(src "${TEST_DIRS[@]}")

RUNNERS=()
if [ "$#" -eq 0 ]; then
    RUNNERS=(run_flake8 run_pylint run_mypy run_pytest)
fi
[ "$#" -gt 0 ] && [ "$1" == flake8 ] && RUNNERS+=(run_flake8) && shift
[ "$#" -gt 0 ] && [ "$1" == pylint ] && RUNNERS+=(run_pylint) && shift
[ "$#" -gt 0 ] && [ "$1" == mypy ] && RUNNERS+=(run_mypy) && shift
[ "$#" -gt 0 ] && [ "$1" == pytest ] && RUNNERS+=(run_pytest) && shift
[ "$#" -gt 0 ] && [ "$1" == pytest-cov ] && RUNNERS+=(run_pytest_cov) && shift

FIRST_RC=0
FAILURES=()
fail() {
    RC=$1 && shift
    [ "$FIRST_RC" -eq 0 ] && FIRST_RC=$RC
    FAILURES+=("$* returned error: $RC")
}

get_files() { find "${SRC_DIRS[@]}" -name '*.py' | grep -vE 'flycheck|/[.]'; }
get_test_files() { find "${TEST_DIRS[@]}" -name '*.py' | grep -vE 'flycheck|/[.]'; }
xargs_uv() { xargs -d '\n' uv run "$@"; }

export COVERAGE_CORE=sysmon

run_flake8() { get_files | (xargs_uv flake8 "$@" && echo 'flake8 passed') || fail $? flake8; }
run_pylint() { get_files | xargs_uv pylint "$@" || fail $? pylint; }
run_mypy() { get_files | xargs_uv mypy --strict "$@" || fail $? mypy; }
run_pytest() { get_test_files | xargs_uv pytest "$@" || fail $? pytest; }
run_pytest-cov() { run_pytest --cov --cov-report=html --cov-branch "$@"; }

for RUNNER in "${RUNNERS[@]}"; do
    "$RUNNER" "$@"
done
[ "$FIRST_RC" -eq 0 ] && exit

echo "Error summary:"
for FAILURE in "${FAILURES[@]}"; do
    echo "$FAILURE"
done

exit "$FIRST_RC"
