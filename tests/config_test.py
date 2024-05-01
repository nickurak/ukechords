import pytest

from ukechords.config import UkeConfig, get_parser, get_args, InvalidCommandException


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
