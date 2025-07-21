"""Our defined errors/exceptions and error handling logic"""

import sys
from typing import NoReturn, Any


class UnknownKeyException(Exception):
    """Returned in the event of a request for an unrecognized musical key"""


class UnknownTuningException(Exception):
    """Returned in the event of a request for an unrecognized tuning"""


class ChordNotFoundException(ValueError):
    """Returned in the event of a request for an unrecognized musical chord"""


class ShapeNotFoundException(ValueError):
    """Returned in the event of a request for a known chord with no known way to play it"""


class InvalidCommandException(Exception):
    """Raised in case of an invalid command line invocation"""


class UnslidableEmptyShapeException(Exception):
    """Raised in the event of an attempt to slide an empty shape"""


def error(return_code: int, message: Any) -> NoReturn:
    """Display an error and exit with the given status"""
    print(message, file=sys.stderr)
    sys.exit(return_code)
