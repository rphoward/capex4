"""Emergency debt ledger evaluator — app-only resilience metric (Phase 5).

Consumes repairReservePathTrace year rows only. See debt-ledger-design.md §3–7.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .errors import RentalCapexError, VALIDATION_ERROR
from .financial import pmt

MAKE_READY_SHORTFALL_REASON = (
    "Near-term repairs from walkthrough exceed make-ready; not emergency-rate debt."
)


def trace_years_from_trace(trace: Mapping[str, object]) -> list[Mapping[str, object]]:
    """Normalize trace payload to per-year rows (years[] or teaching view rows[])."""
    years = trace.get("years")
    if isinstance(years, list):
        return years
    rows = trace.get("rows")
    if isinstance(rows, list):
        return rows
    raise RentalCapexError(
        VALIDATION_ERROR,
        "trace must include years[] or rows[].",
        {"traceKeys": list(trace.keys())},
    )


def repair_year_first_month(trace_year: int) -> int:
    """1-based month index from deal start for the first month of trace year y."""
    return trace_year * 12 + 1


def evaluate_emergency_debt_ledger(
    trace_years: Sequence[Mapping[str, object]],
    *,
    emergency_loan_apr: float,
    emergency_loan_term_years: float,
    immediate_rehab_make_ready: float = 0.0,
    evaluation_horizon_months: int = 120,
) -> dict[str, object]:
    """Evaluate chronological emergency gaps, refi stack, and month debt service."""
    if emergency_loan_term_years <= 0:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "emergencyLoanTermYears must be greater than zero.",
            {
                "field": "emergencyLoanTermYears",
                "value": emergency_loan_term_years,
            },
        )

    term_months = int(emergency_loan_term_years * 12)
    if term_months <= 0:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "emergencyLoanTermYears is too small to produce a payment term.",
            {
                "field": "emergencyLoanTermYears",
                "value": emergency_loan_term_years,
                "termMonths": term_months,
            },
        )
    monthly_rate = emergency_loan_apr / 12
    rows_by_year = {int(row["year"]): row for row in trace_years}

    outstanding_principal = 0.0
    ledger_years: list[dict[str, object]] = []
    refinance_events: list[dict[str, object]] = []
    make_ready_attribution = 0.0

    for year in range(1, 11):
        trace_row = rows_by_year.get(year)
        if trace_row is None:
            raise RentalCapexError(
                VALIDATION_ERROR,
                f"trace missing year {year}.",
                {"year": year, "presentYears": sorted(rows_by_year)},
            )

        repair_cost = float(trace_row["repairCost"])
        balance_before_repairs = float(trace_row["balanceBeforeRepairs"])

        if repair_cost <= 0:
            raw_shortfall = 0.0
        else:
            raw_shortfall = max(0.0, repair_cost - balance_before_repairs)

        year_make_ready = 0.0
        if year == 1 and raw_shortfall > 0:
            emergency_gap = 0.0
            year_make_ready = raw_shortfall
            make_ready_attribution = raw_shortfall
        elif year >= 2:
            emergency_gap = raw_shortfall
        else:
            emergency_gap = 0.0

        ledger_years.append(
            {
                "year": year,
                "repairCost": repair_cost,
                "balanceBeforeRepairs": balance_before_repairs,
                "rawShortfall": raw_shortfall,
                "emergencyGap": emergency_gap,
                "makeReadyAttribution": year_make_ready,
                "routedToMakeReady": year == 1 and raw_shortfall > 0,
            }
        )

        if emergency_gap <= 0:
            continue

        prior_schedule_active = _prior_schedule_active(
            refinance_events,
            repair_year_first_month(year),
            term_months,
        )

        outstanding_principal += emergency_gap
        monthly_payment = pmt(
            monthly_rate,
            term_months,
            0.0,
            -outstanding_principal,
            0,
        )
        payment_start_month = repair_year_first_month(year)

        refinance_events.append(
            {
                "year": year,
                "emergencyGap": emergency_gap,
                "outstandingPrincipal": outstanding_principal,
                "monthlyPayment": monthly_payment,
                "apr": emergency_loan_apr,
                "termMonths": term_months,
                "paymentStartMonth": payment_start_month,
                "priorScheduleActive": prior_schedule_active,
            }
        )

    payment_months = _build_payment_months(
        refinance_events,
        evaluation_horizon_months,
    )

    make_ready_flag = make_ready_attribution > 0
    overlap_refinance_years = overlap_refinance_years_from_events(refinance_events)
    overlap_detected = bool(overlap_refinance_years)

    return {
        "id": "emergencyDebtLedger",
        "years": ledger_years,
        "refinanceEvents": refinance_events,
        "paymentMonths": payment_months,
        "overlapDetected": overlap_detected,
        "overlapRefinanceYears": overlap_refinance_years,
        "makeReadyShortfallFlag": make_ready_flag,
        "makeReadyAttribution": make_ready_attribution,
        "suggestedImmediateRehabMakeReady": (
            immediate_rehab_make_ready + make_ready_attribution
        ),
        "reason": MAKE_READY_SHORTFALL_REASON if make_ready_flag else None,
        "outstandingPrincipal": outstanding_principal,
        "emergencyLoanApr": emergency_loan_apr,
        "emergencyLoanTermYears": emergency_loan_term_years,
        "termMonths": term_months,
        "evaluationHorizonMonths": evaluation_horizon_months,
    }


def debt_service_for_month(
    ledger: Mapping[str, object],
    month: int,
) -> float:
    """Return emergency debt service for a 1-based month index in the ledger horizon."""
    if month < 1:
        return 0.0
    payment_months = ledger.get("paymentMonths", [])
    if not isinstance(payment_months, list) or month > len(payment_months):
        return 0.0
    row = payment_months[month - 1]
    if not isinstance(row, Mapping) or int(row["month"]) != month:
        return 0.0
    return float(row["debtService"])


def evaluate_shock_adjusted_cash_flow(
    true_monthly_cash_flow: float,
    ledger: Mapping[str, object],
) -> dict[str, object]:
    """Worst-month shock-adjusted cash flow from static B40 minus emergency debt service."""
    horizon = int(ledger.get("evaluationHorizonMonths", 120))
    shock_adjusted_months: list[dict[str, object]] = []
    worst_adjusted = true_monthly_cash_flow
    worst_month = 1

    for month in range(1, horizon + 1):
        debt_service = debt_service_for_month(ledger, month)
        adjusted_cash_flow = true_monthly_cash_flow - debt_service
        shock_adjusted_months.append(
            {
                "month": month,
                "adjustedCashFlow": adjusted_cash_flow,
                "debtService": debt_service,
            }
        )
        if adjusted_cash_flow < worst_adjusted:
            worst_adjusted = adjusted_cash_flow
            worst_month = month

    return {
        "trueMonthlyCashFlow": true_monthly_cash_flow,
        "shockAdjustedCashFlow": worst_adjusted,
        "worstShockMonth": worst_month,
        "shockAdjustedMonths": shock_adjusted_months,
        "evaluationHorizonMonths": horizon,
    }


def evaluate_deal_survival(
    shock_adjusted_cash_flow: float,
    true_monthly_cash_flow: float,
    minimum_true_monthly_cash_flow: float,
) -> bool:
    """Survival rule: worst-month shock >= 0 and B40 >= user floor."""
    return (
        shock_adjusted_cash_flow >= 0
        and true_monthly_cash_flow >= minimum_true_monthly_cash_flow
    )


def overlap_refinance_years_from_events(
    refinance_events: Sequence[Mapping[str, object]],
) -> list[int]:
    """Years where a new y>=2 refi started while a prior payment window was still active."""
    return [
        int(event["year"])
        for event in refinance_events
        if bool(event.get("priorScheduleActive"))
    ]


def evaluate_overlap_detected(ledger: Mapping[str, object]) -> bool:
    """True when any emergency refi stacked on a prior schedule (§9.2)."""
    events = ledger.get("refinanceEvents", [])
    if not isinstance(events, list):
        return False
    return bool(overlap_refinance_years_from_events(events))


def _prior_schedule_active(
    refinance_events: Sequence[Mapping[str, object]],
    new_payment_start_month: int,
    term_months: int,
) -> bool:
    if not refinance_events:
        return False
    prior = refinance_events[-1]
    prior_start = int(prior["paymentStartMonth"])
    prior_end = prior_start + term_months - 1
    return new_payment_start_month <= prior_end


def _build_payment_months(
    refinance_events: Sequence[Mapping[str, object]],
    horizon_months: int,
) -> list[dict[str, object]]:
    if not refinance_events:
        return [
            {"month": month, "debtService": 0.0, "activeRefiYear": None}
            for month in range(1, horizon_months + 1)
        ]

    segments: list[tuple[int, int, float, int | None]] = []
    for index, event in enumerate(refinance_events):
        start = int(event["paymentStartMonth"])
        nominal_end = start + int(event["termMonths"]) - 1
        if index + 1 < len(refinance_events):
            next_start = int(refinance_events[index + 1]["paymentStartMonth"])
            end = min(nominal_end, next_start - 1)
        else:
            end = nominal_end
        if start <= end:
            segments.append(
                (
                    start,
                    end,
                    float(event["monthlyPayment"]),
                    int(event["year"]),
                )
            )

    payment_months: list[dict[str, object]] = []
    for month in range(1, horizon_months + 1):
        debt_service = 0.0
        active_refi_year: int | None = None
        for start, end, payment, refi_year in segments:
            if start <= month <= end:
                debt_service = payment
                active_refi_year = refi_year
                break
        payment_months.append(
            {
                "month": month,
                "debtService": debt_service,
                "activeRefiYear": active_refi_year,
            }
        )
    return payment_months
