#!/usr/bin/env python3

import sys


from .theory import add_no5_quality, add_7sus2_quality
from .theory import UnknownKeyException, ChordNotFoundException, ShapeNotFoundException
from .config import UkeConfig, get_args, get_parser, error, InvalidCommandException


def main():
    add_no5_quality()
    add_7sus2_quality()
    try:
        config = UkeConfig(get_args(parser=get_parser(), args=sys.argv[1:]))
        config.run_command()
    except UnknownKeyException as exc:
        error(10, exc)
    except ChordNotFoundException as exc:
        error(2, exc)
    except ShapeNotFoundException as exc:
        error(1, exc)
    except InvalidCommandException as exc:
        error(5, exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
