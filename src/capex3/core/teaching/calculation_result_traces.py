"""Calculation-result trace view-model builders for calculate payloads."""

from __future__ import annotations

from copy import deepcopy
from typing import Mapping, Sequence

from capex3.core.solve_rental_capex import (
    RentalCapexSolverRequest,
    solve_rental_capex,
)
from capex3.core.workbook_assumptions import model_spec_record

from .cash_flow_stability_trace import cash_flow_stability_trace
from .evidence_presentation import presentation_for_layer
from .solver_question_display import (
    threshold_questions_to_contract,
    threshold_solver_tolerance,
)

SOLVER_CASE_POLICY = (
    "solver.* cases are app-side regression cases, not workbook-canonical solver behavior."
)

SOLVER_DISCLAIMER: dict[str, object] = {
    "workbookCanonical": False,
    "appRegressionOnly": True,
    "solverCasePolicy": SOLVER_CASE_POLICY,
    "sourceNote": (
        "Manual solver and threshold questions call solve_rental_capex bisection under "
        "fixtureContract.solverCasePolicy — app-side regression only, not spreadsheet "
        "Goal Seek or workbook-canonical solver truth."
    ),
    "layerCopy": (
        "Thresholds under current assumptions — not recommendations. Each question uses "
        "the Python app regression solver with all other inputs held constant."
    ),
    "solverNote": (
        "App-side regression only (fixtureContract.solverCasePolicy). Previews are "
        "exploratory under current inputs — not workbook-canonical solver output."
    ),
    "previewFootnote": (
        "App-side regression preview — not workbook-canonical solver output."
    ),
}

REPAIR_RESERVE_PATH_TRACE_DECISION_ID = (
    "repair_reserve_path_trace_workbook_vs_teaching"
)

CANONICAL_RESERVE_FIELD_PATHS = [
    "proForma[].annualCapexContribution",
    "proForma[].accumulatedCapexReserve",
    "dashboard.totalMonthlyCapexReserve",
    "dashboard.targetCapExReserve",
]


def build_calculation_result_traces(
    contract: Mapping[str, object],
    *,
    solver_variables: Sequence[Mapping[str, object]],
    model_spec: Mapping[str, object],
) -> dict[str, object]:
    traces = {
        "cashFlow": _cash_flow_trace(contract),
        "repairDrivers": _repair_driver_trace(contract),
        "repairFund": _repair_fund_trace(contract),
        "tenYear": _ten_year_trace(contract),
        "whatWorks": _what_works_trace(
            contract,
            solver_variables=solver_variables,
            model_spec=model_spec,
        ),
        "cashFlowStability": cash_flow_stability_trace(contract),
    }
    for layer_id, trace in traces.items():
        trace["presentation"] = presentation_for_layer(layer_id)
    return traces


def _cash_flow_trace(result: Mapping[str, object]) -> dict[str, object]:
    dashboard = result["dashboard"]
    input_data = result["input"]
    vacancy_loss = (
        dashboard["effectiveGrossIncomeMonthly"] - input_data["actualGrossMonthlyRent"]
    )
    return {
        "id": "cashFlow",
        "title": "Monthly Cash Flow Breakdown",
        "summary": [
            _card("Usable income", dashboard["effectiveGrossIncomeMonthly"], "moneyCents"),
            _card("Operating costs", dashboard["totalMonthlyFixedExpenses"], "moneyCents"),
            _card(
                "Repair fund",
                dashboard["totalMonthlyCapexReserve"],
                "moneyCents",
                note="Snapshot monthly rate from sinking fund.",
            ),
            _card(
                "True monthly cash flow (B40)",
                dashboard["trueMonthlyCashFlow"],
                "moneyCents",
                note=(
                    "Static underwriting snapshot; full monthly reserve deducted "
                    "every month (not post-cap annual contribution)."
                ),
            ),
        ],
        "rows": [
            _receipt_row(
                "Expected monthly rent",
                "actualGrossMonthlyRent",
                input_data["actualGrossMonthlyRent"],
                "income",
            ),
            _receipt_row(
                f"Vacancy rate ({dashboard['vacancyRate']:.0%})",
                "vacancyRate",
                vacancy_loss,
                "deduction",
            ),
            _receipt_row(
                "Usable income",
                "effectiveGrossIncomeMonthly",
                dashboard["effectiveGrossIncomeMonthly"],
                "subtotal",
            ),
            _receipt_row(
                "Operating costs",
                "totalMonthlyFixedExpenses",
                -dashboard["totalMonthlyFixedExpenses"],
                "deduction",
            ),
            _receipt_row(
                "Monthly repair fund (snapshot)",
                "totalMonthlyCapexReserve",
                -dashboard["totalMonthlyCapexReserve"],
                "deduction",
            ),
            _receipt_row(
                "Income before debt",
                "netOperatingIncomeMonthly",
                dashboard["netOperatingIncomeMonthly"],
                "subtotal",
            ),
            _receipt_row(
                "Loan payment",
                "monthlyMortgagePI",
                -dashboard["monthlyMortgagePI"],
                "deduction",
            ),
            _receipt_row(
                "True monthly cash flow (B40)",
                "trueMonthlyCashFlow",
                dashboard["trueMonthlyCashFlow"],
                "total",
            ),
        ],
        "graph": {
            "bars": [
                _bar("Usable income", dashboard["effectiveGrossIncomeMonthly"], "moneyCents"),
                _bar("Operating costs", dashboard["totalMonthlyFixedExpenses"], "moneyCents"),
                _bar("Repair fund (snapshot)", dashboard["totalMonthlyCapexReserve"], "moneyCents"),
                _bar("Loan payment", dashboard["monthlyMortgagePI"], "moneyCents"),
                _bar("True monthly cash flow (B40)", dashboard["trueMonthlyCashFlow"], "moneyCents"),
            ]
        },
    }


def _repair_driver_trace(result: Mapping[str, object]) -> dict[str, object]:
    total = result["dashboard"]["totalMonthlyCapexReserve"] or 1
    rows = [
        {
            **dict(row),
            "label": row["component"],
            "value": row["monthlyReserve"],
            "kind": "moneyCents",
            "shareOfReserve": row["monthlyReserve"] / total,
            "source": (
                "Walkthrough override"
                if row.get("overrideStatus")
                else "Workbook default"
            ),
        }
        for row in result["sinkingFundRows"]
    ]
    display_rows = _repair_driver_display_rows(rows, total)
    override_count = sum(1 for row in rows if row.get("overrideStatus"))
    return {
        "id": "repairDrivers",
        "title": "Repair Drivers",
        "summary": [
            _card("Total monthly reserve", result["dashboard"]["totalMonthlyCapexReserve"], "moneyCents"),
            _card("Components tracked", len(rows), "number"),
            _card("Walkthrough overrides", override_count, "number"),
        ],
        "rows": rows,
        "displayRows": display_rows,
        "graph": {"bars": display_rows[:6]},
    }


def _ten_year_trace(result: Mapping[str, object]) -> dict[str, object]:
    rows = [dict(row) for row in result["proForma"]]
    dashboard = result["dashboard"]
    year10 = rows[-1]
    initial_investment = dashboard["totalInitialInvestment"]
    return {
        "id": "tenYear",
        "title": "10-Year Story",
        "summary": [
            _card(
                "Year-10 ROI (B28)",
                dashboard["year10Roi"],
                "percent",
                note="Excludes reserve returned at sale (L15).",
            ),
            _card(
                "Liquidation wealth (L17)",
                year10["realEstateLiquidationWealth"],
                "money",
                note="Includes accumulated reserve (L15) returned at sale.",
            ),
            _card("Annualized ROI", dashboard["year10AnnualizedRoi"], "percent"),
            _card("Cash needed up front", dashboard["totalInitialInvestment"], "money"),
        ],
        "receipts": _ten_year_sale_bridge_receipts(dashboard, year10),
        "rows": rows,
        "graph": {
            "series": [
                {
                    "id": "rental",
                    "label": "Liquidation wealth (L17)",
                    "values": [row["realEstateLiquidationWealth"] for row in rows],
                },
                {
                    "id": "cashFlow",
                    "label": "Cash position (L16 + initial)",
                    "sourceNote": (
                        "Running cash after expenses and reserves; year 10 excludes "
                        "sale proceeds and reserve addback (those are in L17)."
                    ),
                    "values": [
                        initial_investment + row["accumulatedTrueCashFlow"]
                        for row in rows
                    ],
                },
                {
                    "id": "moneyMarket",
                    "label": "Money market",
                    "values": [row["moneyMarketComparison"] for row in rows],
                },
                {
                    "id": "conservativeIra",
                    "label": "IRA",
                    "values": [row["conservativeIraComparison"] for row in rows],
                },
            ]
        },
        "note": (
            "Liquidation wealth (L17) grows through leverage, appreciation, and sale; "
            "cash position (L16 + initial) is operating cash only—year 10 does not include "
            "sale proceeds or reserve addback. Alternative paths use the workbook's money "
            "market and IRA assumptions."
        ),
        "initialInvestment": initial_investment,
    }


def _ten_year_sale_bridge_receipts(
    dashboard: Mapping[str, object],
    year10: Mapping[str, object],
) -> list[dict[str, object]]:
    return [
        _workbook_receipt(
            "Future property value (B23)",
            "dashboard.futurePropertyValueYear10",
            dashboard["futurePropertyValueYear10"],
            "10-Year Pro Forma B23",
            formula="purchase price × (1 + appreciation)^10",
        ),
        _workbook_receipt(
            "Remaining loan balance (B24)",
            "dashboard.remainingLoanBalanceYear10",
            dashboard["remainingLoanBalanceYear10"],
            "10-Year Pro Forma B24",
            formula="CUMPRINC through year 10",
            source_note="Subtracted from future value at sale.",
        ),
        _workbook_receipt(
            "Cost of sale (B25)",
            "dashboard.costOfSaleYear10",
            dashboard["costOfSaleYear10"],
            "10-Year Pro Forma B25",
            formula="B23 × cost-of-sale rate",
            source_note="Subtracted from future value at sale.",
        ),
        _workbook_receipt(
            "Net proceeds (B26)",
            "dashboard.netProceedsYear10",
            dashboard["netProceedsYear10"],
            "10-Year Pro Forma B26",
            formula="B23 − B24 − B25",
        ),
        _workbook_receipt(
            "Accumulated operating cash (L16)",
            "proForma[10].accumulatedTrueCashFlow",
            year10["accumulatedTrueCashFlow"],
            "10-Year Pro Forma L16",
            source_note="Running true cash flow through year 10; feeds B28 ROI numerator.",
        ),
        _workbook_receipt(
            "Reserve returned at sale (L15)",
            "proForma[10].accumulatedCapexReserve",
            year10["accumulatedCapexReserve"],
            "10-Year Pro Forma L15",
            source_note="Capped reserve balance addback at sale; included in L17, excluded from B28.",
        ),
    ]


def _workbook_receipt(
    label: str,
    engine_field: str,
    value: object,
    workbook_source: str,
    *,
    formula: str = "",
    source_note: str = "",
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "label": label,
        "engineField": engine_field,
        "value": value,
        "kind": "money",
        "workbookSource": workbook_source,
    }
    if formula:
        receipt["formula"] = formula
    if source_note:
        receipt["sourceNote"] = source_note
    return receipt


def _repair_fund_contribution_pattern(
    rows: Sequence[Mapping[str, object]],
    monthly_contribution: object,
) -> str:
    monthly = (
        float(monthly_contribution)
        if isinstance(monthly_contribution, (int, float))
        else 0.0
    )
    contributions = [
        float(row.get("annualContribution") or 0)
        for row in rows
    ]
    if monthly <= 0 or not any(contribution > 0 for contribution in contributions):
        return "none"
    seen_positive = False
    for contribution in contributions:
        if contribution > 0:
            seen_positive = True
        elif seen_positive:
            return "stops_at_cap"
    return "building"


def _repair_fund_monthly_card_note(pattern: str) -> str:
    if pattern == "none":
        return "No monthly reserve is modeled for this deal."
    if pattern == "stops_at_cap":
        return (
            "Annual contributions in the trace table stop once the reserve cap (B21) "
            "is reached; repairs can restart contributions in later years."
        )
    return (
        "Trace contributions continue until the reserve cap (B21) is reached "
        "within this 10-year view."
    )


def _repair_fund_trace_note(pattern: str) -> str:
    if pattern == "none":
        return (
            "Teaching-only timeline: no monthly reserve is modeled. Compare reserve "
            "balance vs. cumulative surprise cost when repairs land."
        )
    if pattern == "stops_at_cap":
        return (
            "Teaching-only timeline: the dashboard monthly rate (B34) funds "
            "contributions until the cap (B21) stops new annual set-aside in the "
            "trace—see the Contribution column. Reserve dips when repairs land, then "
            "can rebuild when balance falls below the cap."
        )
    return (
        "Teaching-only timeline: contributions follow the dashboard monthly rate "
        "(B34) until the reserve cap (B21) is reached. Compare reserve balance vs. "
        "cumulative surprise cost when repairs land."
    )


def _repair_fund_info_copy(pattern: str) -> str:
    if pattern == "none":
        return (
            "This teaching trace compares reserve balance vs. no-reserve surprise "
            "cost when repairs land. No monthly repair reserve is modeled for this deal."
        )
    if pattern == "stops_at_cap":
        return (
            "This teaching trace compares reserve balance vs. no-reserve surprise "
            "cost. The dashboard monthly rate (B34) drives contributions until the "
            "reserve cap (B21) stops new annual set-aside—use the Contribution column, "
            "not a flat “every year” monthly deposit story."
        )
    return (
        "This teaching trace compares reserve balance vs. no-reserve surprise cost. "
        "Contributions follow the dashboard monthly rate (B34) until the reserve cap "
        "(B21) is reached in the trace table."
    )


def _repair_fund_cumulative_interest(
    rows: Sequence[Mapping[str, object]],
) -> float:
    return sum(
        float(row["interestEarned"])
        for row in rows
        if isinstance(row.get("interestEarned"), (int, float))
    )


def _repair_fund_trace(result: Mapping[str, object]) -> dict[str, object]:
    trace = dict(result.get("repairReservePathTrace", {}))
    rows = [dict(row) for row in trace.get("years", [])]
    events = [dict(event) for event in trace.get("eventMarkers", [])]
    pattern = _repair_fund_contribution_pattern(rows, trace.get("monthlyContribution"))
    cumulative_interest = _repair_fund_cumulative_interest(rows)
    reserve_apy = trace.get("reserveAccountApy")
    largest = trace.get("largestEvent")
    largest_label = "None in 10 years"
    largest_note = "No modeled component replacement lands inside the 10-year view."
    largest_value = 0
    if isinstance(largest, Mapping):
        largest_label = str(largest.get("label") or largest.get("component") or "Repair")
        largest_value = largest.get("amount") or 0
        largest_note = f"Year {largest.get('year')}"

    return {
        "id": "repairFund",
        "title": "Repair Fund",
        "summary": [
            _card(
                "Dashboard monthly rate (B34)",
                trace.get("monthlyContribution"),
                "moneyCents",
                note=_repair_fund_monthly_card_note(pattern),
            ),
            _card("Target reserve", trace.get("targetReserve"), "money"),
            _card(
                "Repair fund APY (B20)",
                reserve_apy,
                "percent",
                note="Interest-bearing reserve account — not checking cash.",
            ),
            _card(
                "Interest earned Yr 0-10",
                cumulative_interest,
                "money",
                note="From repairReservePathTrace balance × APY each year.",
            ),
            {
                "label": "Largest single repair",
                "value": largest_value,
                "kind": "money",
                "note": largest_label if largest_value else largest_note,
            },
            {
                "label": "Total repairs Yr 0-10",
                "value": trace.get("totalEventCost"),
                "kind": "money",
                "note": "No-reserve path peak",
            },
        ],
        "rows": rows,
        "events": events,
        "graph": {
            "series": [
                {
                    "id": "reserveBalance",
                    "label": "Reserve balance",
                    "values": [row.get("endingBalance") for row in rows],
                },
                {
                    "id": "noReserveSurpriseCost",
                    "label": "Cumulative surprise cost",
                    "values": [row.get("noReserveSurpriseCost") for row in rows],
                },
            ],
            "events": events,
        },
        "note": _repair_fund_trace_note(pattern),
        "infoCopy": _repair_fund_info_copy(pattern),
        "reserveContributionPattern": pattern,
        "workbookCanonical": False,
        "teachingOnly": True,
        "decisionId": REPAIR_RESERVE_PATH_TRACE_DECISION_ID,
        "canonicalReserveSource": "proForma_and_dashboard",
        "canonicalReserveFields": list(CANONICAL_RESERVE_FIELD_PATHS),
        "sourceNote": (
            "Teaching-only timeline from repairReservePathTrace — not workbook-contract "
            "and not in the 17-case parity gate. Monthly cap, contribution diversion, and "
            "year-10 reserve story use workbook-canonical pro forma and dashboard fields "
            "(see canonicalReserveFields). Do not describe this layer as spreadsheet parity."
        ),
        "monthlyContribution": trace.get("monthlyContribution"),
        "targetReserve": trace.get("targetReserve"),
    }


def _what_works_trace(
    result: Mapping[str, object],
    *,
    solver_variables: Sequence[Mapping[str, object]],
    model_spec: Mapping[str, object],
) -> dict[str, object]:
    dashboard = result["dashboard"]
    return {
        "id": "whatWorks",
        "title": "What Would Work?",
        "summary": [
            _card("Current cash flow", dashboard["trueMonthlyCashFlow"], "moneyCents"),
            _card("Cash needed up front", dashboard["totalInitialInvestment"], "money"),
        ],
        "questions": _threshold_question_traces(
            result,
            solver_variables=solver_variables,
            model_spec=model_spec,
        ),
        "graph": {
            "bars": [
                _bar("True cash flow", dashboard["trueMonthlyCashFlow"], "moneyCents"),
                _bar("Income before debt", dashboard["netOperatingIncomeMonthly"], "moneyCents"),
                _bar("Cash up front", dashboard["totalInitialInvestment"], "money"),
            ]
        },
        **deepcopy(SOLVER_DISCLAIMER),
    }


def _receipt_row(
    label: str,
    engine_field: str,
    value: object,
    receipt_kind: str,
) -> dict[str, object]:
    return {
        "label": label,
        "engineField": engine_field,
        "value": value,
        "kind": "moneyCents",
        "receiptKind": receipt_kind,
    }


def _repair_driver_display_rows(
    rows: list[dict[str, object]],
    total_monthly_reserve: object,
) -> list[dict[str, object]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: row.get("monthlyReserve") or 0,
        reverse=True,
    )
    shown = [dict(row) for row in sorted_rows[:8]]
    remaining = sorted_rows[8:]
    if remaining:
        total = total_monthly_reserve if isinstance(total_monthly_reserve, (int, float)) else 1
        other_monthly_reserve = sum(
            row.get("monthlyReserve") or 0
            for row in remaining
            if isinstance(row.get("monthlyReserve"), (int, float))
        )
        shown.append(
            {
                "component": f"Other ({len(remaining)})",
                "label": f"Other ({len(remaining)})",
                "monthlyReserve": other_monthly_reserve,
                "value": other_monthly_reserve,
                "kind": "moneyCents",
                "shareOfReserve": other_monthly_reserve / (total or 1),
                "source": "Various",
                "quantityLabel": "-",
                "ageLifeLabel": "-",
                "remainingLifeLabel": "-",
                "isOtherBucket": True,
            }
        )
    return shown


def _threshold_question_traces(
    result: Mapping[str, object],
    *,
    solver_variables: Sequence[Mapping[str, object]],
    model_spec: Mapping[str, object],
) -> list[dict[str, object]]:
    input_data = result["input"]
    variables = {variable["id"]: variable for variable in solver_variables}
    traces = []
    for question in threshold_questions_to_contract():
        solver_config = dict(question.get("solver", {}))
        solver_request = {
            key: value
            for key, value in {
                **solver_config,
                "baseInput": dict(input_data),
                "tolerance": threshold_solver_tolerance(
                    metric=str(solver_config.get("metric") or ""),
                ),
            }.items()
            if key
            in {
                "baseInput",
                "variable",
                "metric",
                "targetValue",
                "lowerBound",
                "upperBound",
                "tolerance",
                "maxIterations",
            }
        }
        solver_result = {"ok": False, "message": "Solver unavailable."}
        try:
            solved = solve_rental_capex(
                RentalCapexSolverRequest.from_contract_dict(solver_request),
                model_spec=model_spec_record(model_spec),
            )
            solver_result = solved.to_contract_dict()
        except Exception as error:
            solver_result = {"ok": False, "message": str(error)}

        variable = variables.get(str(solver_request.get("variable") or ""), {})
        apply_field = str(variable.get("applyField") or "")
        current_value = input_data.get(apply_field) if apply_field else None
        solved_value = solver_result.get("solvedValue")
        gap_value = (
            solved_value - current_value
            if isinstance(solved_value, (int, float))
            and isinstance(current_value, (int, float))
            else None
        )
        traces.append(
            {
                **deepcopy(question),
                "solverPreview": solver_result,
                "applyField": apply_field,
                "currentValue": current_value,
                "gapValue": gap_value,
                "thresholdState": _threshold_state(str(question["id"]), gap_value, solver_result),
            }
        )
    return traces


def _threshold_state(
    question_id: str,
    gap_value: object,
    solver_result: Mapping[str, object],
) -> str:
    if not solver_result.get("ok") or not isinstance(gap_value, (int, float)):
        return "warning"
    if question_id in {"breakEvenRent", "requiredDownPaymentCashFlowZero"}:
        return "ok" if gap_value <= 0 else "warning"
    if question_id in {"maxPurchasePriceCashFlowZero", "maxRehabBudgetCashOnCash8Pct"}:
        return "ok" if gap_value >= 0 else "warning"
    return "ok"


def _card(label: str, value: object, kind: str, *, note: str = "") -> dict[str, object]:
    card: dict[str, object] = {"label": label, "value": value, "kind": kind}
    if note:
        card["note"] = note
    return card


def _bar(label: str, value: object, kind: str) -> dict[str, object]:
    return {"label": label, "value": value, "kind": kind}
