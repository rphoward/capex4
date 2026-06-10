"""Pro forma fixture contract: calculation cases assert years 0-10."""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFICATION_CASES = REPO_ROOT / "tests" / "fixtures" / "model-verification-cases.json"
REQUIRED_YEARS = list(range(11))


class ProFormaFixtureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verification = json.loads(
            VERIFICATION_CASES.read_text(encoding="utf-8")
        )
        cls.solver_policy = cls.verification["fixtureContract"]["solverCasePolicy"]

    def test_solver_case_policy_documents_app_side_regression(self) -> None:
        self.assertIn("app-side", self.solver_policy.lower())

    def test_calculation_cases_have_pro_forma_years_zero_through_ten(self) -> None:
        violations: list[str] = []
        for case in self.verification["cases"]:
            case_id = case["id"]
            if case_id.startswith("solver."):
                continue
            expected = case.get("expected") or {}
            rows = expected.get("proFormaRows")
            if not rows:
                violations.append(f"{case_id}: missing proFormaRows")
                continue
            years = sorted(row["year"] for row in rows)
            if years != REQUIRED_YEARS:
                violations.append(
                    f"{case_id}: years {years} != required {REQUIRED_YEARS}"
                )
            if len(rows) != 11:
                violations.append(
                    f"{case_id}: expected 11 rows, got {len(rows)}"
                )
        self.assertEqual(violations, [], "\n".join(violations))

    def test_solver_cases_may_omit_pro_forma_rows(self) -> None:
        for case in self.verification["cases"]:
            if not case["id"].startswith("solver."):
                continue
            self.assertNotIn(
                "proFormaRows",
                case.get("expected") or {},
                msg=f"{case['id']} should not carry workbook pro forma expectations",
            )


if __name__ == "__main__":
    unittest.main()
