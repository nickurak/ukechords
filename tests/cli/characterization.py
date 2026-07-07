"""Fixture to mark characterization tests and automatically pull in regtest_all
Disables pytest_regtest's binary checker to ensure all unicode output doesn't trigger a failure.
"""
# mypy: ignore-errors

from collections.abc import Iterator

import pytest
from pytest_regtest import pytest_regtest


@pytest.fixture(params=[pytest.param(None, marks=pytest.mark.characterization)])
def characterization(regtest_all: None) -> Iterator[None]:
    """Fixture to mark characterization tests and automatically pull in regtest_all
    Disables pytest_regtest's binary checker to ensure all unicode output doesn't trigger a failure.
    """
    pytest_regtest.contains_binary = lambda x: False  # type: ignore
    yield
