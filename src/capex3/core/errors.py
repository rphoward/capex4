from dataclasses import dataclass, field
from typing import Mapping


VALIDATION_ERROR = "VALIDATION_ERROR"
LOOKUP_ERROR = "LOOKUP_ERROR"
NO_BRACKET = "NO_BRACKET"
NON_FINITE_RESULT = "NON_FINITE_RESULT"
UNDEFINED_METRIC = "UNDEFINED_METRIC"
MAX_ITERATIONS_EXCEEDED = "MAX_ITERATIONS_EXCEEDED"


def json_safe_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): json_safe_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [json_safe_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


@dataclass(frozen=True)
class RentalCapexError(ValueError):
    code: str
    message: str
    details: Mapping[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


ERROR_CODES = {
    "VALIDATION_ERROR": VALIDATION_ERROR,
    "LOOKUP_ERROR": LOOKUP_ERROR,
    "NO_BRACKET": NO_BRACKET,
    "NON_FINITE_RESULT": NON_FINITE_RESULT,
    "UNDEFINED_METRIC": UNDEFINED_METRIC,
    "MAX_ITERATIONS_EXCEEDED": MAX_ITERATIONS_EXCEEDED,
}

CapexValidationError = RentalCapexError
