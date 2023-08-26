#!/usr/bin/env python3

import sys


from theory import add_no5_quality, add_7sus2_quality
from config import UkeConfig, get_args, get_parser


def main(args):
    add_no5_quality()
    add_7sus2_quality()
    config = UkeConfig(get_args(parser=get_parser(), args=args))
    config.command(config)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
