import pytest

from ukechords.config import UkeConfig, get_parser, get_args, error, InvalidCommandException


def test_no_args():
    parser = get_parser()
    args = get_args(parser=parser, args=[])
    with pytest.raises(InvalidCommandException):
        UkeConfig(args)


class FakeParser(): # pylint: disable=too-few-public-methods
    def __init__(self):
        self.help_shown_fds = []

    def print_help(self, file_descriptor):
        self.help_shown_fds.append(file_descriptor)


def test_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        error(5, "error!")
    assert excinfo.value.code == 5
    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'error!\n'
