# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import tempfile
import pytest


def shape_ranker(shape):
    return sum(shape)


class UkeTestConfig:
    # pylint: disable=too-few-public-methods,too-many-instance-attributes
    def __init__(self):
        self.slide = False
        self.tuning = ["C", "E", "G"]
        self.show_notes = False
        self.visualize = False
        self.force_flat = False
        self.qualities = False
        self.no_cache = True
        self.base = 0
        self.max_difficulty = 20
        self.shape_ranker = shape_ranker
        self.num = 10
        self.cache_dir = None


@pytest.fixture
def uke_config():
    with tempfile.TemporaryDirectory() as tmpdirname:
        config_obj = UkeTestConfig()
        config_obj.cache_dir = tmpdirname
        yield config_obj
