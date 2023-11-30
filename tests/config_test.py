from ukechords.config import UkeConfig, get_parser, get_args


def test_no_args(mocker):
    mock_error = mocker.patch('ukechords.config.error')

    parser = get_parser()
    args = get_args(parser=parser, args=[])
    UkeConfig(args)

    args, _ = mock_error.call_args

    assert args[0] == 5
