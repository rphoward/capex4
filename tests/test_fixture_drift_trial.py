import copy
import json
import tempfile
import unittest
from pathlib import Path

from tests.fixture_parity import VERIFICATION_CASES, run_fixture_parity


class FixtureDriftTrialTest(unittest.TestCase):
    def test_intentional_calculation_expected_drift_fails_parity(self) -> None:
        verification = json.loads(VERIFICATION_CASES.read_text(encoding="utf8"))
        drifted = copy.deepcopy(verification)

        default_case = next(
            case
            for case in drifted["cases"]
            if case["id"] == "default.currentWorkbook"
        )
        default_case["expected"]["year10Roi"] = 0.0

        with tempfile.TemporaryDirectory() as temp_dir:
            drift_path = Path(temp_dir) / "drifted-model-verification-cases.json"
            drift_path.write_text(
                json.dumps(drifted, indent=2),
                encoding="utf8",
            )
            report = run_fixture_parity(cases_path=drift_path)

        self.assertFalse(report["ok"])
        failure_text = json.dumps(report["failures"])
        self.assertTrue(
            "year10Roi" in failure_text or "default.currentWorkbook" in failure_text,
            failure_text,
        )

    def test_canonical_fixtures_still_pass_after_drift_trial_module_import(self) -> None:
        report = run_fixture_parity()

        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(report["totalCaseCount"], 17)
        self.assertEqual(
            report["fixtureSource"],
            "tests/fixtures/model-verification-cases.json",
        )


if __name__ == "__main__":
    unittest.main()
