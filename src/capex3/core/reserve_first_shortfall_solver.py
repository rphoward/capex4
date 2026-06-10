"""Bisect monthly reserve increase to clear the first y>=2 emergency gap only."""

from __future__ import annotations

import math
from typing import Callable, Mapping

from .errors import (
    MAX_ITERATIONS_EXCEEDED,
    NO_BRACKET,
    RentalCapexError,
    VALIDATION_ERROR,
)

YEAR_ONE_MAKE_READY_REASON = (
    "First repair shortfall is in year 1 — use make-ready / rehab budget, not reserve increase."
)
NO_EMERGENCY_GAP_REASON = "No emergency repair gap at year 2 or later."
ALREADY_CLEARED_REASON = (
    "Current monthly reserve increase already clears the first emergency gap."
)


def find_first_raw_shortfall_year(ledger: Mapping[str, object]) -> int | None:
    for row in ledger.get("years", []):
        if not isinstance(row, Mapping):
            continue
        if float(row.get("rawShortfall") or 0.0) > 0.0:
            return int(row["year"])
    return None


def find_first_emergency_gap_year(ledger: Mapping[str, object]) -> int | None:
    for row in ledger.get("years", []):
        if not isinstance(row, Mapping):
            continue
        year = int(row["year"])
        if year >= 2 and float(row.get("emergencyGap") or 0.0) > 0.0:
            return year
    return None


def emergency_gap_at_year(ledger: Mapping[str, object], year: int) -> float:
    for row in ledger.get("years", []):
        if not isinstance(row, Mapping):
            continue
        if int(row["year"]) == year:
            return float(row.get("emergencyGap") or 0.0)
    raise RentalCapexError(
        VALIDATION_ERROR,
        f"Ledger missing year {year}.",
        {"year": year},
    )


def bisect_monthly_reserve_increase(
    *,
    evaluate_gap: Callable[[float], float],
    lower_bound: float,
    upper_bound: float,
    tolerance: float,
    max_iterations: int,
) -> dict[str, object]:
    if lower_bound < 0 or upper_bound <= lower_bound:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "Reserve solver bounds require 0 <= lowerBound < upperBound.",
            {"lowerBound": lower_bound, "upperBound": upper_bound},
        )
    if tolerance <= 0 or max_iterations < 1:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "Reserve solver tolerance must be positive and maxIterations >= 1.",
            {"tolerance": tolerance, "maxIterations": max_iterations},
        )

    lower_gap = evaluate_gap(lower_bound)
    upper_gap = evaluate_gap(upper_bound)

    if lower_gap <= tolerance:
        return {
            "ok": True,
            "solvedValue": lower_bound,
            "residual": lower_gap,
            "iterations": 0,
            "alreadyCleared": True,
        }

    if upper_gap > tolerance:
        return {
            "ok": False,
            "code": NO_BRACKET,
            "message": "Reserve solver bounds do not bracket zero gap at first shortfall year.",
            "lowerBound": lower_bound,
            "upperBound": upper_bound,
            "lowerGap": lower_gap,
            "upperGap": upper_gap,
        }

    low_value = lower_bound
    high_value = upper_bound
    iterations = 0

    for iteration in range(1, max_iterations + 1):
        midpoint = (low_value + high_value) / 2
        mid_gap = evaluate_gap(midpoint)
        iterations = iteration

        if abs(mid_gap) <= tolerance:
            return {
                "ok": True,
                "solvedValue": midpoint,
                "residual": mid_gap,
                "iterations": iterations,
                "alreadyCleared": False,
            }

        if mid_gap > 0:
            low_value = midpoint
        else:
            high_value = midpoint

    midpoint = (low_value + high_value) / 2
    mid_gap = evaluate_gap(midpoint)
    if abs(mid_gap) <= tolerance:
        return {
            "ok": True,
            "solvedValue": midpoint,
            "residual": mid_gap,
            "iterations": iterations,
            "alreadyCleared": False,
        }

    return {
        "ok": False,
        "code": MAX_ITERATIONS_EXCEEDED,
        "message": "Reserve solver reached max iterations before meeting tolerance.",
        "solvedValue": midpoint,
        "residual": mid_gap,
        "iterations": iterations,
    }


def estimate_upper_bound_for_reserve_increase(
    *,
    first_shortfall_year: int,
    gap_amount: float,
    current_monthly_increase: float,
) -> float:
    if gap_amount <= 0:
        return max(current_monthly_increase + 1.0, 1.0)
    months_before_shortfall = max(12, (first_shortfall_year - 1) * 12 + 1)
    per_month_estimate = gap_amount / months_before_shortfall
    headroom = max(per_month_estimate * 4, gap_amount / 12, 25.0)
    return current_monthly_increase + headroom


def reserve_solver_decline_reason(ledger: Mapping[str, object]) -> str | None:
    if find_first_raw_shortfall_year(ledger) == 1:
        return YEAR_ONE_MAKE_READY_REASON
    if find_first_emergency_gap_year(ledger) is None:
        return NO_EMERGENCY_GAP_REASON
    return None


def round_reserve_increase(value: float) -> float:
    if not math.isfinite(value):
        return value
    rounded = round(value, 2)
    return 0.0 if abs(rounded) < 0.005 else rounded
