#!/usr/bin/env python3

import sys


from .theory import add_no5_quality, add_7sus2_quality, add_M13_quality
from .config import UkeConfig, get_args, get_parser


def main():
    add_no5_quality()
    add_7sus2_quality()
    add_M13_quality()
    config = UkeConfig(get_args(parser=get_parser(), args=sys.argv[1:]))
    config.run_command()
    return 0


if __name__ == "__main__":
    sys.exit(main())
