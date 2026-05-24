#!/usr/bin/env bash

set -Eeuo pipefail

TEST_DIRS=(tests)
SRC_DIRS=(src "${TEST_DIRS[@]}")

RUNNERS=(run_ruff run_pylint run_ty run_mypy run_pytest run_shellcheck)
[ "$#" -gt 0 ] && readarray -t RUNNERS < <(printf "%s" "$1" | xargs -d ',' -n1 | sed 's/^/run_/') && shift

FIRST_RC=0 && FAILURES=()
fail() {
    RC=$1 && shift
    [ "$FIRST_RC" -eq 0 ] && FIRST_RC=$RC
    FAILURES+=("$* returned error: $RC")
}

mapfile -d '' FILES < <(find "${SRC_DIRS[@]}" ! -name '*flycheck*' ! -name '.*' -name '*.py' -print0)
mapfile -d '' TEST_FILES < <(find "${TEST_DIRS[@]}" ! -name '*flycheck*' ! -name '.*' -name '*.py' -name '*.py' -print0)

FIND_NODOTDIR=(-mindepth 1 -type d -name '.*' -prune -o)
# shellcheck disable=SC2329
find_sh0() {
    find . "${FIND_NODOTDIR[@]}" -type f -print0 |
        xargs -0 grep -Z '^#!.*sh' -l | grep -zv '[.]sh$'
    find . "${FIND_NODOTDIR[@]}" -name '*.sh' -print0
}

# shellcheck disable=SC2329
{
    run_pylint() { uv run pylint "$@" "${FILES[@]}"; }
    run_ruff() { uv run ruff check "$@" "${FILES[@]}"; }
    run_ty() { uv run ty check "$@" "${FILES[@]}"; }
    run_mypy() { uv run mypy --strict "$@" "${FILES[@]}"; }
    run_pytest_base() { uv run pytest "$@" "${TEST_FILES[@]}"; }
    run_pytest_main() { run_pytest_base -p 'no:regtest' -m 'not characterization' "$@"; }
    run_pytest_char() { run_pytest_base -m 'characterization' "$@"; }
    run_pytest() {
        run_pytest_main "$@"
        run_pytest_char "$@"
    }
    run_pytest-cov() {
        run_pytest_main --cov --cov-report=html --cov-branch "$@"
        run_pytest_char --cov --cov-report=html:coverage_html_report/characterization --cov-branch "$@"
    }
    run_reset-char() {
        find tests -path '*/_regtest_outputs/*' -type f -name '*.out' -delete
        run_pytest_char --regtest-reset
    }
    run_shellcheck() { find_sh0 | xargs -0 shellcheck; }
}

for RUNNER in "${RUNNERS[@]}"; do
    "$RUNNER" "$@" || fail $? "$RUNNER"
done
[ "$FIRST_RC" -eq 0 ] && exit

echo "Error summary:"
(IFS=$'\n' && echo "${FAILURES[*]}")

exit "$FIRST_RC"
