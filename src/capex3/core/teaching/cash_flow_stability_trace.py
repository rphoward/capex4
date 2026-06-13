"""Cash-flow stability dossier trace assembly for calculate result payloads."""

from __future__ import annotations

from typing import Mapping, Sequence

from capex3.core.errors import RentalCapexError, VALIDATION_ERROR

from .cash_flow_stability_evidence import (
    CASH_FLOW_STABILITY_LAYER_ID,
    CASH_FLOW_STABILITY_SOURCE_NOTE,
    TRACE_DEBT_SHOCK_ROW_ROLES,
    TRACE_PLANNED_ROW_ROLES,
    build_trace_path_rows,
    cash_flow_stability_evidence_to_contract,
    peak_emergency_payment_from_result,
)


def cash_flow_stability_trace(result: Mapping[str, object]) -> dict[str, object]:
    teaching = cash_flow_stability_evidence_to_contract(result)
    dashboard = result["dashboard"]
    ledger = result["emergencyDebtLedger"]
    if not isinstance(ledger, Mapping):
        raise RentalCapexError(
            VALIDATION_ERROR,
            "Calculator result emergencyDebtLedger must be an object.",
            {"emergencyDebtLedger": ledger},
        )

    planned_monthly = dashboard["totalMonthlyCapexReserve"]
    refinance_events = [
        dict(event)
        for event in ledger.get("refinanceEvents", [])
        if isinstance(event, Mapping)
    ]
    payment_months = [
        dict(row)
        for row in ledger.get("paymentMonths", [])
        if isinstance(row, Mapping)
    ]
    peak_debt_payment = peak_emergency_payment_from_result(result)

    overlap_detected = bool(ledger.get("overlapDetected"))
    overlap_years = list(ledger.get("overlapRefinanceYears", []))
    months_with_debt_service = sum(
        1 for row in payment_months if float(row.get("debtService") or 0.0) > 0.0
    )

    planned_rows = build_trace_path_rows(result, TRACE_PLANNED_ROW_ROLES)
    debt_shock_rows = build_trace_path_rows(result, TRACE_DEBT_SHOCK_ROW_ROLES)
    if peak_debt_payment > 0.0:
        debt_shock_rows.append(
            {
                "role": "monthlyBurdenAvoided",
                "label": "Monthly burden avoided vs peak debt",
                "value": peak_debt_payment - float(planned_monthly or 0.0),
                "kind": "moneyCents",
            }
        )

    return {
        "id": CASH_FLOW_STABILITY_LAYER_ID,
        "title": teaching["title"],
        "primaryFramingCopy": teaching["primaryFramingCopy"],
        "summary": _summary_cards(
            planned_monthly=planned_monthly,
            peak_debt_payment=peak_debt_payment,
            shock_adjusted_cash_flow=result["shockAdjustedCashFlow"],
            overlap_detected=overlap_detected,
            overlap_years=overlap_years,
        ),
        "twoPathComparison": {
            "plannedReservePath": {
                "title": teaching["plannedPathTitle"],
                "rows": planned_rows,
            },
            "debtShockPath": {
                "title": teaching["debtShockPathTitle"],
                "rows": debt_shock_rows,
            },
        },
        "debtLedgerTimeline": {
            "refinanceEvents": refinance_events,
            "paymentMonths": payment_months,
            "overlapDetected": overlap_detected,
            "overlapRefinanceYears": overlap_years,
            "monthsWithDebtService": months_with_debt_service,
        },
        "teaching": teaching,
        "contractSource": teaching["contractSource"],
        "sourceNote": CASH_FLOW_STABILITY_SOURCE_NOTE,
        "workbookCanonical": False,
        "appOnlyResilience": True,
    }


def _summary_cards(
    *,
    planned_monthly: object,
    peak_debt_payment: float,
    shock_adjusted_cash_flow: object,
    overlap_detected: bool,
    overlap_years: Sequence[object],
) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = [
        _card(
            "Planned monthly reserve",
            planned_monthly,
            "moneyCents",
            note="Snapshot monthly rate before repairs are pre-funded.",
        ),
        _card(
            "Peak emergency debt payment",
            peak_debt_payment,
            "moneyCents",
            note=(
                "Highest consolidated payment after unfunded repair shortfalls (y≥2)."
                if peak_debt_payment
                else "No emergency refi in the modeled window."
            ),
        ),
        _card(
            "Shock-adjusted cash flow",
            shock_adjusted_cash_flow,
            "moneyCents",
            note="Worst month: Snapshot cash flow minus emergency debt service.",
        ),
    ]
    if overlap_detected:
        summary.append(
            {
                "label": "Stacked refinance overlap",
                "value": True,
                "kind": "boolean",
                "note": f"Overlap years: {', '.join(str(year) for year in overlap_years)}",
            }
        )
    return summary


def _card(label: str, value: object, kind: str, *, note: str = "") -> dict[str, object]:
    card: dict[str, object] = {"label": label, "value": value, "kind": kind}
    if note:
        card["note"] = note
    return card
