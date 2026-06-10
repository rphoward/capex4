"""Phase 5 Slice 7 — reserve-increase solver first shortfall."""

from __future__ import annotations

import json
import re
import unittest

from capex3.core.reserve_first_shortfall_solver import (
    YEAR_ONE_MAKE_READY_REASON,
    bisect_monthly_reserve_increase,
    emergency_gap_at_year,
    find_first_emergency_gap_year,
    find_first_raw_shortfall_year,
    reserve_solver_decline_reason,
)
from capex3.presentation.http_contracts import (
    calculate_payload,
    defaults_payload,
    solve_payload,
)
from capex3.core.calculate_rental_capex import (
    RentalCapexCalculationRequest,
    calculate_rental_capex,
)
from capex3.infrastructure.workbook_assumptions import load_workbook_model_spec_record
from capex3.presentation.htmx_renderer import render_ui_fragment


class ReserveFirstShortfallSolverTest(unittest.TestCase):
    def test_core_bisect_finds_minimum_bump(self) -> None:
        target_gap = 120.0

        def evaluate_gap(monthly_increase: float) -> float:
            return max(0.0, target_gap - monthly_increase * 12)

        result = bisect_monthly_reserve_increase(
            evaluate_gap=evaluate_gap,
            lower_bound=0.0,
            upper_bound=20.0,
            tolerance=0.01,
            max_iterations=50,
        )

        self.assertTrue(result["ok"])
        self.assertAlmostEqual(float(result["solvedValue"]), 10.0, places=1)
        self.assertLessEqual(abs(float(result["residual"])), 0.01)

    def test_decline_reason_year_one_raw_shortfall(self) -> None:
        ledger = {
            "years": [
                {
                    "year": 1,
                    "rawShortfall": 15_000.0,
                    "emergencyGap": 0.0,
                },
                {
                    "year": 2,
                    "rawShortfall": 0.0,
                    "emergencyGap": 0.0,
                },
            ]
        }
        self.assertEqual(find_first_raw_shortfall_year(ledger), 1)
        self.assertEqual(
            reserve_solver_decline_reason(ledger),
            YEAR_ONE_MAKE_READY_REASON,
        )

    def test_solve_clears_first_emergency_gap_on_synthetic_deal(self) -> None:
        model_spec = load_workbook_model_spec_record()
        inputs = _shortfall_at_year_three_inputs()
        baseline = calculate_rental_capex(
            RentalCapexCalculationRequest.from_contract_dict(inputs),
            model_spec=model_spec,
        )
        first_gap_year = find_first_emergency_gap_year(baseline.emergency_debt_ledger)
        self.assertEqual(first_gap_year, 3)
        baseline_gap = emergency_gap_at_year(baseline.emergency_debt_ledger, 3)
        self.assertGreater(baseline_gap, 0.0)

        status, payload = solve_payload(
            {
                "questionId": "reserveIncreaseFirstShortfall",
                "baseInput": inputs,
            }
        )
        self.assertEqual(status, 200)
        solver_result = payload["result"]
        self.assertTrue(solver_result["ok"])
        solved_bump = float(solver_result["solvedValue"])
        self.assertGreater(solved_bump, 0.0)

        solved = calculate_rental_capex(
            RentalCapexCalculationRequest.from_contract_dict(
                {**inputs, "monthlyReserveIncrease": solved_bump}
            ),
            model_spec=model_spec,
        )
        self.assertAlmostEqual(
            emergency_gap_at_year(solved.emergency_debt_ledger, 3),
            0.0,
            places=0,
        )

    def test_monthly_reserve_increase_round_trips_and_affects_trace(self) -> None:
        inputs = {"monthlyReserveIncrease": 125.5}
        payload = calculate_payload(inputs)
        normalized = payload["result"]["input"]
        self.assertEqual(normalized["monthlyReserveIncrease"], 125.5)

        trace = payload["result"]["repairReservePathTrace"]
        self.assertEqual(trace["monthlyReserveIncrease"], 125.5)
        self.assertGreater(trace["monthlyContribution"], trace["monthlyReserveIncrease"])

    def test_overlap_latch_unchanged_after_reserve_apply(self) -> None:
        inputs = _shortfall_at_year_three_inputs()
        status, solve = solve_payload(
            {
                "questionId": "reserveIncreaseFirstShortfall",
                "baseInput": inputs,
            }
        )
        self.assertEqual(status, 200)
        self.assertTrue(solve["result"]["ok"])
        solved_bump = solve["result"]["solvedValue"]
        overrides = inputs["componentOverrides"]
        snapshot = json.dumps(
            {
                "effectiveAgeYears": inputs["effectiveAgeYears"],
                "componentAges": {
                    component: override["age"]
                    for component, override in sorted(overrides.items())
                    if override.get("age") is not None
                },
            },
            separators=(",", ":"),
        )

        latched = render_ui_fragment(
            {
                **{k: v for k, v in inputs.items() if k != "componentOverrides"},
                "activeStep": "walkthrough",
                "componentOverridesJson": json.dumps(overrides),
                "overlapWarningLatched": "true",
                "overlapWarningAgeSnapshotKey": snapshot,
                "solverApplyField": "monthlyReserveIncrease",
                "solverSolvedValue": str(solved_bump),
            },
            "apply-solver",
        )
        self.assertIn('name="overlapWarningLatched" value="true"', latched)
        self.assertIn("monthlyReserveIncrease", latched)

    def test_idempotent_reapply_sets_same_bump(self) -> None:
        inputs = _shortfall_at_year_three_inputs()
        status, solve = solve_payload(
            {
                "questionId": "reserveIncreaseFirstShortfall",
                "baseInput": inputs,
            }
        )
        self.assertTrue(solve["result"]["ok"])
        solved_bump = float(solve["result"]["solvedValue"])

        overrides = inputs["componentOverrides"]
        base_form = {
            **{k: v for k, v in inputs.items() if k != "componentOverrides"},
            "activeStep": "walkthrough",
            "componentOverridesJson": json.dumps(overrides),
            "solverApplyField": "monthlyReserveIncrease",
            "solverSolvedValue": str(solved_bump),
        }
        first_apply = render_ui_fragment(base_form, "apply-solver")
        second_apply = render_ui_fragment(
            {**base_form, "monthlyReserveIncrease": str(solved_bump)},
            "apply-solver",
        )
        first_result = calculate_payload(
            _extract_monthly_reserve_increase(first_apply)
        )["result"]["input"]["monthlyReserveIncrease"]
        second_result = calculate_payload(
            _extract_monthly_reserve_increase(second_apply)
        )["result"]["input"]["monthlyReserveIncrease"]
        self.assertAlmostEqual(first_result, solved_bump, places=2)
        self.assertAlmostEqual(second_result, solved_bump, places=2)

    def test_offer_ready_renders_reserve_solver_section(self) -> None:
        inputs = _shortfall_at_year_three_inputs()
        overrides = inputs["componentOverrides"]
        body = render_ui_fragment(
            {
                **{k: v for k, v in inputs.items() if k != "componentOverrides"},
                "activeStep": "walkthrough",
                "componentOverridesJson": json.dumps(overrides),
            },
            "calculate",
        )
        self.assertIn('id="reserve-first-shortfall-solver"', body)
        self.assertIn("Solve reserve bump", body)


def _shortfall_at_year_three_inputs() -> dict[str, object]:
    components = [
        component["name"]
        for component in defaults_payload()["assumptions"]["components"]
    ]
    overrides = {name: {"quantity": 0, "age": 0} for name in components}
    overrides["Roofing: Arch. Asphalt (per sq)"] = {"quantity": 30, "age": 15}
    return {
        "effectiveAgeYears": 15,
        "reserveAccountApy": 0.0,
        "capexInflationRate": 0.0,
        "componentOverrides": overrides,
    }


def _extract_monthly_reserve_increase(html: str) -> dict[str, object]:
    match = re.search(r'name="monthlyReserveIncrease"[^>]*value="([^"]*)"', html)
    if match is None:
        return {}
    return {"monthlyReserveIncrease": float(match.group(1))}


if __name__ == "__main__":
    unittest.main()
