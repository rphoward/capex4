import math

from .errors import RentalCapexError, VALIDATION_ERROR


def _assert_finite_number(value: object, name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise RentalCapexError(
            VALIDATION_ERROR,
            f"{name} must be a finite number.",
            {"field": name, "value": value},
        )


def pmt(
    rate: float,
    nper: float,
    pv: float,
    fv: float = 0,
    payment_type: int = 0,
) -> float:
    _assert_finite_number(rate, "rate")
    _assert_finite_number(nper, "nper")
    _assert_finite_number(pv, "pv")
    _assert_finite_number(fv, "fv")

    if (
        isinstance(payment_type, bool)
        or not isinstance(payment_type, int)
        or payment_type not in (0, 1)
    ):
        raise RentalCapexError(
            VALIDATION_ERROR,
            "PMT type must be 0 or 1.",
            {"type": payment_type},
        )

    if nper == 0:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "PMT nper must not be zero.",
            {"nper": nper},
        )

    if rate == 0:
        return -(pv + fv) / nper

    factor = (1 + rate) ** nper
    return -((pv * factor + fv) * rate) / (
        (1 + rate * payment_type) * (factor - 1)
    )


def cumulative_principal(
    rate: float,
    nper: float,
    pv: float,
    start_period: int,
    end_period: int,
    payment_type: int = 0,
) -> float:
    _assert_finite_number(rate, "rate")
    _assert_finite_number(nper, "nper")
    _assert_finite_number(pv, "pv")
    _assert_finite_number(start_period, "startPeriod")
    _assert_finite_number(end_period, "endPeriod")

    if (
        isinstance(payment_type, bool)
        or not isinstance(payment_type, int)
        or payment_type != 0
    ):
        raise RentalCapexError(
            VALIDATION_ERROR,
            "Only end-of-period CUMPRINC calculations are supported.",
            {"type": payment_type},
        )

    if not isinstance(start_period, int) or not isinstance(end_period, int):
        raise RentalCapexError(
            VALIDATION_ERROR,
            "CUMPRINC periods must be integers.",
            {"startPeriod": start_period, "endPeriod": end_period},
        )

    if start_period < 1 or end_period < start_period or end_period > nper:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "CUMPRINC periods are outside the loan term.",
            {"startPeriod": start_period, "endPeriod": end_period, "nper": nper},
        )

    payment = pmt(rate, nper, pv, 0, payment_type)
    balance = pv
    cumulative = 0

    for period in range(1, end_period + 1):
        interest_payment = -balance * rate
        principal_payment = payment - interest_payment
        balance += principal_payment

        if period >= start_period:
            cumulative += principal_payment

    return cumulative
