import unittest

from tests.fixture_parity import main, run_fixture_parity


class FixtureParityTest(unittest.TestCase):
    def test_run_fixture_parity_ok_and_17_cases(self) -> None:
        report = run_fixture_parity()

        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(report["calculationCaseCount"], 5)
        self.assertEqual(report["solverCaseCount"], 12)
        self.assertEqual(report["totalCaseCount"], 17)
        self.assertEqual(
            report["runtimeSource"],
            "src/capex3/infrastructure/workbook_assumptions/data",
        )
        self.assertEqual(
            report["fixtureSource"],
            "tests/fixtures/model-verification-cases.json",
        )


if __name__ == "__main__":
    raise SystemExit(main())
