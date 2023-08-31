from utils import cached_filename


def test_cached_filename(mocker):
    mock_abspath  = mocker.patch('os.path.abspath')
    mock_abspath.return_value = '/test/null.py'
    fn_str = cached_filename(-1, 4, ['A'], 50)
    assert fn_str == "/test/cached_shapes/cache_-1_4_A_50.pcl"