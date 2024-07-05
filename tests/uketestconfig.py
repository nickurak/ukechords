# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

from typing import Callable, List, Optional
from dataclasses import dataclass, field

import tempfile
import pytest


def shape_ranker(shape):
    return sum(shape)


@dataclass
class UkeTestConfig:
    # pylint: disable=too-many-instance-attributes
    slide: bool = False
    tuning: List[str] = field(default_factory=lambda: ["C", "E", "G"])
    show_notes: bool = False
    visualize: bool = False
    force_flat: bool = False
    qualities: bool = False
    no_cache: bool = True
    mute: bool = False
    max_difficulty: float = 20
    shape_ranker: Callable = shape_ranker
    num: int = 10
    cache_dir: Optional[str] = None


@pytest.fixture
def uke_config():
    with tempfile.TemporaryDirectory() as tmpdirname:
        config_obj = UkeTestConfig()
        config_obj.cache_dir = tmpdirname
        yield config_obj
