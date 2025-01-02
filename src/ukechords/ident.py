#!/usr/bin/env python3

"""Simple command-line client to invoke ukechords functionality"""

import sys


from ukechords.theory import add_no5_quality, add_7sus2_quality
from ukechords.errors import UnknownKeyException, ChordNotFoundException, ShapeNotFoundException
from ukechords.errors import error, InvalidCommandException
from ukechords.config import UkeConfig


def main() -> int:
    # pylint: disable=missing-function-docstring
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
    except KeyboardInterrupt:
        error(128, "(aborted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
