"""Phase 4 Slice 5: reserveAccountApy parity case contract and drift guard."""

from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from capex3.core.calculate_rental_capex import (
    RentalCapexCalculationRequest,
    calculate_rental_capex,
)
from capex3.infrastructure.workbook_assumptions import (
    load_workbook_model_spec_record,
)
from tests.fixture_parity import VERIFICATION_CASES, run_fixture_parity

HIGH_RESERVE_APY_CASE_ID = "proForma.reserveCapAccelerated.highReserveApy"
HIGH_RESERVE_APY_INPUT = 0.5
DRIFT_RESERVE_APY = 0.51


def _load_verification() -> dict[str, Any]:
    return json.loads(VERIFICATION_CASES.read_text(encoding="utf-8"))


def _case_by_id(verification: Mapping[str, Any], case_id: str) -> dict[str, Any]:
    for case in verification["cases"]:
        if case["id"] == case_id:
            return case
    raise AssertionError(f"Missing fixture case {case_id!r}")


def _pro_forma_row(
    rows: list[Mapping[str, Any]], year: int
) -> Mapping[str, Any]:
    for row in rows:
        if row["year"] == year:
            return row
    raise AssertionError(f"Missing pro forma year {year}")


def _calculate_case(fixture_case: Mapping[str, Any]) -> dict[str, Any]:
    model_spec = load_workbook_model_spec_record()
    return calculate_rental_capex(
        RentalCapexCalculationRequest.from_contract_dict(
            fixture_case.get("inputs") or {}
        ),
        model_spec=model_spec,
    ).to_contract_dict()


class ReserveAccountApyParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verification = _load_verification()
        cls.fixture_case = _case_by_id(cls.verification, HIGH_RESERVE_APY_CASE_ID)
        cls.currency_tolerance = cls.verification["numericTolerance"][
            "currencyAbsolute"
        ]

    def test_fixture_case_documents_high_reserve_apy(self) -> None:
        inputs = self.fixture_case["inputs"]
        description = self.fixture_case["description"].lower()

        self.assertEqual(inputs.get("reserveAccountApy"), HIGH_RESERVE_APY_INPUT)
        self.assertIn("reserve", description)
        self.assertTrue(
            "cap" in description or "apy" in description,
            description,
        )

    def test_parity_harness_passes_for_high_reserve_apy_case(self) -> None:
        report = run_fixture_parity()

        self.assertTrue(report["ok"], report["failures"])
        case_failures = [
            failure
            for failure in report["failures"]
            if failure.get("caseId") == HIGH_RESERVE_APY_CASE_ID
        ]
        self.assertEqual(case_failures, [])

    def test_reserve_cap_behavior_matches_fixture_expected(self) -> None:
        expected = self.fixture_case["expected"]
        result = _calculate_case(self.fixture_case)
        pro_forma = result["proForma"]

        target = expected["targetCapExReserve"]
        actual_target = result["dashboard"]["targetCapExReserve"]
        self.assertTrue(
            math.isclose(actual_target, target, abs_tol=self.currency_tolerance),
            (actual_target, target),
        )

        year2_expected = _pro_forma_row(expected["proFormaRows"], 2)
        year2_actual = _pro_forma_row(pro_forma, 2)
        self.assertTrue(
            math.isclose(
                year2_actual["accumulatedCapexReserve"],
                year2_expected["accumulatedCapexReserve"],
                abs_tol=self.currency_tolerance,
            ),
            (year2_actual["accumulatedCapexReserve"], year2_expected),
        )
        self.assertTrue(
            math.isclose(actual_target, year2_actual["accumulatedCapexReserve"], abs_tol=self.currency_tolerance),
            "Year 2 reserve balance should reach targetCapExReserve",
        )

        year3_expected = _pro_forma_row(expected["proFormaRows"], 3)
        year3_actual = _pro_forma_row(pro_forma, 3)
        self.assertEqual(year3_expected["annualCapexContribution"], 0)
        self.assertEqual(year3_actual["annualCapexContribution"], 0)

        for year in range(3, 11):
            row = _pro_forma_row(pro_forma, year)
            self.assertEqual(
                row["annualCapexContribution"],
                0,
                f"year {year} should shut off contributions after cap",
            )

    def test_intentional_reserve_account_apy_drift_fails_parity(self) -> None:
        drifted = copy.deepcopy(self.verification)
        drift_case = _case_by_id(drifted, HIGH_RESERVE_APY_CASE_ID)
        drift_case["inputs"]["reserveAccountApy"] = DRIFT_RESERVE_APY

        with tempfile.TemporaryDirectory() as temp_dir:
            drift_path = Path(temp_dir) / "drifted-model-verification-cases.json"
            drift_path.write_text(json.dumps(drifted, indent=2), encoding="utf-8")
            report = run_fixture_parity(cases_path=drift_path)

        self.assertFalse(report["ok"])
        failure_text = json.dumps(report["failures"])
        self.assertIn(HIGH_RESERVE_APY_CASE_ID, failure_text)
        self.assertTrue(
            "reserveAccountApy" in failure_text
            or "targetCapExReserve" in failure_text
            or "accumulatedCapexReserve" in failure_text
            or "annualCapexContribution" in failure_text
            or "proForma" in failure_text,
            failure_text,
        )


if __name__ == "__main__":
    unittest.main()
