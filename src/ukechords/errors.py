"""Our defined errors/exceptions"""


class UnknownKeyException(Exception):
    """Returned in the event of a request for an unrecognized musical key"""


class UnknownTuningException(Exception):
    """Returned in the event of a request for an unrecognized tuning"""


class ChordNotFoundException(ValueError):
    """Returned in the event of a request for an unrecognized musical chord"""


class InvalidCommandException(Exception):
    """Raised in case of an invalid command line invocation"""


class UnslidableEmptyShapeException(Exception):
    """Raised in the event of an attempt to slide an empty shape"""
