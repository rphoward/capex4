"""Offer-ready screen copy — mechanical survival and warning strings."""

from __future__ import annotations

from typing import Mapping

SURVIVAL_PASS_HEADLINE = "Deal survives repairs"
SURVIVAL_FAIL_HEADLINE = "Deal does not survive repairs"

SURVIVAL_PASS_DETAIL = (
    "Worst-month shock-adjusted cash flow and your cash-flow floor both clear."
)
SURVIVAL_FAIL_DETAIL = (
    "Shock-adjusted cash flow or true monthly cash flow falls below your floor."
)

SHOCK_ADJUSTED_LABEL = "Shock-adjusted cash flow (worst month)"
TRUE_MONTHLY_LABEL = "True monthly cash flow (B40)"
FLOOR_LABEL = "Your cash-flow floor"

OVERLAP_WARNING_SHORT = (
    "Stacked emergency refi: a new repair gap landed while prior emergency debt "
    "was still due."
)

MAKE_READY_INTRO = "Make-ready shortfall flagged"

RESERVE_SOLVER_TITLE = "Reserve bump for first shortfall"
RESERVE_SOLVER_PROMPT = (
    "Minimum monthly reserve increase that clears the first unfunded emergency repair "
    "(year 2 or later only)."
)
RESERVE_SOLVER_OVERLAP_NOTE = (
    "Higher reserves do not clear a stacked emergency refi warning by themselves."
)
RESERVE_SOLVER_DISCLAIMER = (
    "App-side resilience solver — not workbook Goal Seek or spreadsheet parity."
)
RESERVE_SOLVER_YEAR_ONE_DECLINED = (
    "First repair shortfall is in year 1 — use make-ready / rehab budget instead."
)
RESERVE_SOLVER_APPLY_NOTE = (
    "Apply writes monthlyReserveIncrease only. Re-apply with the same walkthrough ages "
    "sets the same bump (idempotent — does not stack duplicate increases)."
)


def build_offer_ready_copy(result: Mapping[str, object] | None) -> dict[str, str]:
    survives = bool(result.get("dealSurvives")) if isinstance(result, Mapping) else False
    return {
        "survivalHeadline": SURVIVAL_PASS_HEADLINE if survives else SURVIVAL_FAIL_HEADLINE,
        "survivalDetail": SURVIVAL_PASS_DETAIL if survives else SURVIVAL_FAIL_DETAIL,
        "shockAdjustedLabel": SHOCK_ADJUSTED_LABEL,
        "trueMonthlyLabel": TRUE_MONTHLY_LABEL,
        "floorLabel": FLOOR_LABEL,
        "overlapWarning": OVERLAP_WARNING_SHORT,
        "makeReadyIntro": MAKE_READY_INTRO,
        "reserveSolverTitle": RESERVE_SOLVER_TITLE,
        "reserveSolverPrompt": RESERVE_SOLVER_PROMPT,
        "reserveSolverOverlapNote": RESERVE_SOLVER_OVERLAP_NOTE,
        "reserveSolverDisclaimer": RESERVE_SOLVER_DISCLAIMER,
        "reserveSolverYearOneDeclined": RESERVE_SOLVER_YEAR_ONE_DECLINED,
        "reserveSolverApplyNote": RESERVE_SOLVER_APPLY_NOTE,
    }
