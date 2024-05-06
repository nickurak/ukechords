#!/usr/bin/env python3

# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import sys


from ukechords.theory import add_no5_quality, add_7sus2_quality
from ukechords.theory import UnknownKeyException, ChordNotFoundException, ShapeNotFoundException
from ukechords.config import UkeConfig, InvalidCommandException


def error(return_code, message):
    print(message, file=sys.stderr)
    sys.exit(return_code)


def main():
    add_no5_quality()
    add_7sus2_quality()
    try:
        config = UkeConfig(sys.argv[1:])
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
