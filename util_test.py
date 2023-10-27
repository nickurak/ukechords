import pytest

from utils import cached_filename

@pytest.fixture(autouse=True)
def abspath_mock(mocker):
    mock_abspath  = mocker.patch('os.path.abspath')
    mock_abspath.return_value = '/test/null.py'


def test_cached_filename():
    fn_str = cached_filename(-1, 4, ['A'], 50)
    assert fn_str == "/test/cached_shapes/cache_-1_4_A_50.pcl"
