"""Fixture to mark characterization tests and automatically pull in regtest_all
Disables pytest_regtest's binary checker to ensure all unicode output doesn't trigger a failure.
"""

from collections.abc import Iterator
from unittest import mock

import pytest


@pytest.fixture(params=[pytest.param(None, marks=pytest.mark.characterization)])
def characterization(regtest_all: None) -> Iterator[None]:
    """Fixture to mark characterization tests and automatically pull in regtest_all
    Disables pytest_regtest's binary checker to ensure all unicode output doesn't trigger a failure.
    """
    with mock.patch("pytest_regtest.pytest_regtest.contains_binary", return_value=False):
        yield
