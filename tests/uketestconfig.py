"""Pytest fixture to provide a UkeConfig object"""

from typing import Generator
import pathlib

import pytest

from ukechords.config import UkeConfig


@pytest.fixture
def uke_config(tmp_path: pathlib.Path) -> Generator[UkeConfig, None, None]:
    """Pytest fixture to provide a UkeConfig object"""
    config_obj = UkeConfig(cache_dir=str(tmp_path), tuning=("C", "E", "G"), max_difficulty=20.0)
    yield config_obj
