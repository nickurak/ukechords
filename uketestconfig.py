import pytest

class UkeTestConfig():
    # pylint: disable=too-few-public-methods,too-many-instance-attributes
    def __init__(self):
        self.slide = False
        self.tuning = ['C', 'E', 'G']
        self.show_notes = False
        self.visualize = False
        self.force_flat = False
        self.qualities = False
        self.no_cache = True
        self.base = 0
        self.max_difficulty = 20


@pytest.fixture
def uke_config():
    config_obj = UkeTestConfig()
    yield config_obj
