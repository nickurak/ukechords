"""Fixture to mark characterization tests and automatically pull in regtest_all"""
# mypy: ignore-errors

from collections.abc import Iterator

import pytest


@pytest.fixture(params=[pytest.param(None, marks=pytest.mark.characterization)])
def characterization(regtest_all: None) -> Iterator[None]:
    """Fixture to mark characterization tests and automatically pull in regtest_all"""
    yield
