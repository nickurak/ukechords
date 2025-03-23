#!/bin/bash

# With coverage: ./run_tests.sh  --cov --cov-report=html --cov-branch

export COVERAGE_CORE=sysmon
uv run pytest . "$@"
