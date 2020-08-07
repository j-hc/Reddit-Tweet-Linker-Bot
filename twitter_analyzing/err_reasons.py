from enum import Enum


class Reasons(Enum):
    NO_TEXT = -1
    DEFAULT = -2
    NO_AT = -3
    NO_IMG = -4
    TOO_SHORT_NO_AT = -8
    ACCOUNT_SUSPENDED = -5
    ACCOUNT_DNE = -6
    ACCOUNT_PROTECTED = -7
