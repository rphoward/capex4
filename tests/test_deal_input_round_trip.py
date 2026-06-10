"""Phase 4 Slice 4 — deal input defaults, round-trip, and validation proof."""

from __future__ import annotations

import math
import unittest

from capex3.core import (
    RentalCapexDealInputRequest,
    RentalCapexError,
    VALIDATION_ERROR,
    normalize_input,
    validate_input,
)
from capex3.infrastructure.workbook_assumptions import (
    load_workbook_model_spec_record,
)

PHASE_4_SURFACED_FIELDS = (
    "reserveAccountApy",
    "emergencyLoanApr",
    "emergencyLoanTermYears",
    "monthlyUtilitiesLandlordPaid",
    "legalProfessionalAnnual",
    "advertisingLeasingAnnual",
)

PHASE_5_SURFACED_FIELDS = (
    "minimumTrueMonthlyCashFlow",
    "monthlyReserveIncrease",
)

PHASE_4_DEFAULTS = {
    "reserveAccountApy": 0.0425,
    "emergencyLoanApr": 0.125,
    "emergencyLoanTermYears": 5,
    "monthlyUtilitiesLandlordPaid": 500,
    "legalProfessionalAnnual": 100,
    "advertisingLeasingAnnual": 100,
}

PHASE_5_DEFAULTS = {
    "minimumTrueMonthlyCashFlow": 0,
    "monthlyReserveIncrease": 0,
}


class DealInputRoundTripTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model_spec = load_workbook_model_spec_record()

    def _normalized(self, overrides: dict[str, object] | None = None) -> dict[str, object]:
        return normalize_input(overrides or {}, self.model_spec)

    def test_phase_4_defaults_from_workbook_json(self) -> None:
        normalized = self._normalized()
        for field in PHASE_4_SURFACED_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(normalized[field], PHASE_4_DEFAULTS[field])

    def test_phase_5_minimum_true_monthly_cash_flow_default_and_override(self) -> None:
        normalized = self._normalized()
        for field in PHASE_5_SURFACED_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(normalized[field], PHASE_5_DEFAULTS[field])

        override = {"minimumTrueMonthlyCashFlow": 400}
        request = RentalCapexDealInputRequest.from_contract_dict(override)
        self.assertEqual(request.to_input_dict(), override)
        self.assertEqual(
            normalize_input(request.to_input_dict(), self.model_spec)[
                "minimumTrueMonthlyCashFlow"
            ],
            400,
        )

    def test_partial_overrides_round_trip_through_request_and_normalize(self) -> None:
        overrides = {
            "reserveAccountApy": 0.05,
            "emergencyLoanApr": 0.09,
            "emergencyLoanTermYears": 7,
            "monthlyUtilitiesLandlordPaid": 750,
            "legalProfessionalAnnual": 200,
            "advertisingLeasingAnnual": 150,
        }
        request = RentalCapexDealInputRequest.from_contract_dict(overrides)
        self.assertEqual(set(request.to_input_dict()), set(overrides))

        normalized = normalize_input(request.to_input_dict(), self.model_spec)
        for field, expected in overrides.items():
            with self.subTest(field=field):
                self.assertEqual(normalized[field], expected)

    def test_from_contract_dict_preserves_surfaced_fields_only(self) -> None:
        overrides = {"monthlyUtilitiesLandlordPaid": 600, "legalProfessionalAnnual": 250}
        request = RentalCapexDealInputRequest.from_contract_dict(overrides)
        round_tripped = request.to_input_dict()
        self.assertEqual(round_tripped, overrides)

        normalized = normalize_input(round_tripped, self.model_spec)
        self.assertEqual(normalized["monthlyUtilitiesLandlordPaid"], 600)
        self.assertEqual(normalized["legalProfessionalAnnual"], 250)
        self.assertEqual(
            normalized["advertisingLeasingAnnual"],
            PHASE_4_DEFAULTS["advertisingLeasingAnnual"],
        )

    def _assert_validation_error(self, input_data: dict[str, object], field: str) -> None:
        with self.assertRaises(RentalCapexError) as raised:
            validate_input(input_data)
        self.assertEqual(raised.exception.code, VALIDATION_ERROR)
        self.assertEqual(raised.exception.details.get("field"), field)

    def test_validate_rejects_non_finite_values(self) -> None:
        base = self._normalized()
        for field, bad_value in (
            ("reserveAccountApy", math.nan),
            ("emergencyLoanApr", math.inf),
            ("monthlyUtilitiesLandlordPaid", -math.inf),
        ):
            with self.subTest(field=field, bad_value=bad_value):
                invalid = dict(base)
                invalid[field] = bad_value
                self._assert_validation_error(invalid, field)

    def test_validate_rejects_boolean_numeric_inputs(self) -> None:
        base = self._normalized()
        for field in ("emergencyLoanTermYears", "legalProfessionalAnnual"):
            with self.subTest(field=field):
                invalid = dict(base)
                invalid[field] = True
                self._assert_validation_error(invalid, field)

    def test_validate_rejects_invalid_emergency_loan_term_and_rate(self) -> None:
        base = self._normalized()

        zero_term = dict(base)
        zero_term["emergencyLoanTermYears"] = 0
        self._assert_validation_error(zero_term, "emergencyLoanTermYears")

        negative_rate = dict(base)
        negative_rate["emergencyLoanApr"] = -1
        self._assert_validation_error(negative_rate, "emergencyLoanApr")

    def test_from_contract_dict_rejects_boolean_numeric_on_parse(self) -> None:
        with self.assertRaises(RentalCapexError) as raised:
            RentalCapexDealInputRequest.from_contract_dict(
                {"reserveAccountApy": False}
            )
        self.assertEqual(raised.exception.code, VALIDATION_ERROR)
        self.assertEqual(raised.exception.details.get("field"), "reserveAccountApy")

    def test_normalize_input_rejects_invalid_emergency_loan_term(self) -> None:
        with self.assertRaises(RentalCapexError) as raised:
            normalize_input({"emergencyLoanTermYears": 0}, self.model_spec)
        self.assertEqual(raised.exception.code, VALIDATION_ERROR)
        self.assertEqual(
            raised.exception.details.get("field"),
            "emergencyLoanTermYears",
        )

    def test_validate_rejects_negative_minimum_true_monthly_cash_flow(self) -> None:
        base = self._normalized()
        invalid = dict(base)
        invalid["minimumTrueMonthlyCashFlow"] = -1
        self._assert_validation_error(invalid, "minimumTrueMonthlyCashFlow")

    def test_phase_5_monthly_reserve_increase_default_override_and_validation(self) -> None:
        normalized = self._normalized()
        self.assertEqual(normalized["monthlyReserveIncrease"], 0)

        override = {"monthlyReserveIncrease": 75}
        request = RentalCapexDealInputRequest.from_contract_dict(override)
        self.assertEqual(request.to_input_dict(), override)
        self.assertEqual(
            normalize_input(request.to_input_dict(), self.model_spec)[
                "monthlyReserveIncrease"
            ],
            75,
        )

        invalid = dict(normalized)
        invalid["monthlyReserveIncrease"] = -5
        self._assert_validation_error(invalid, "monthlyReserveIncrease")


if __name__ == "__main__":
    unittest.main()
