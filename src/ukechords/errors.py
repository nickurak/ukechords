"""Our defined errors/exceptions and error handling logic"""

import sys


class UnknownKeyException(Exception):
    """Returned in the event of a request for an unrecognized musical key"""


class ChordNotFoundException(ValueError):
    """Returned in the event of a request for an unrecognized musical chord"""


class ShapeNotFoundException(ValueError):
    """Returned in the event of a request for a known chord with no known way to play it"""


class InvalidCommandException(Exception):
    "Raised in case of an invalid command line invocation"


def error(return_code, message):
    """ "Display an error and exit with the given status"""
    print(message, file=sys.stderr)
    sys.exit(return_code)
