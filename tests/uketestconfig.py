# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

from typing import Generator

import tempfile
import pytest

from ukechords.config import UkeConfig


@pytest.fixture
def uke_config() -> Generator[UkeConfig, None, None]:
    with tempfile.TemporaryDirectory() as tmpdirname:
        config_obj = UkeConfig(cache_dir=tmpdirname, tuning=("C", "E", "G"), max_difficulty=20.0)
        yield config_obj
