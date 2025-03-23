#!/bin/bash

[ "${#ARGS[@]}" -lt 1 ] && ARGS=(".")

uv run mypy --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs "${ARGS[*]}"
