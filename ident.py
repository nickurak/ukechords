#!/usr/bin/env python3

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=missing-module-docstring,invalid-name

import sys

from theory import add_no5_quality, add_7sus2_quality
from config import UkeConfig, get_args, get_parser

def main():
    add_no5_quality()
    add_7sus2_quality()
    config = UkeConfig(get_args(get_parser()))
    config.command(config)
    return 0

if __name__ == "__main__":
    sys.exit(main())
