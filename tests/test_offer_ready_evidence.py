import ast
import unittest
from pathlib import Path

from capex3.presentation.http_contracts import calculate_payload
from capex3.core.teaching.offer_ready_evidence import (
    MAKE_READY_INTRO,
    OVERLAP_WARNING_SHORT,
    SURVIVAL_FAIL_HEADLINE,
    SURVIVAL_PASS_HEADLINE,
    build_offer_ready_copy,
)

DEFAULT_SURVIVAL_HEADLINE = SURVIVAL_FAIL_HEADLINE

REPO_ROOT = Path(__file__).resolve().parents[1]
TEACHING_MODULE = (
    REPO_ROOT
    / "src"
    / "capex3"
    / "core"
    / "teaching"
    / "offer_ready_evidence.py"
)


class OfferReadyEvidenceTest(unittest.TestCase):
    def test_build_offer_ready_copy_survival_headlines(self) -> None:
        payload = calculate_payload({})
        result = payload["result"]

        passing = build_offer_ready_copy(result)
        self.assertEqual(passing["survivalHeadline"], DEFAULT_SURVIVAL_HEADLINE)
        self.assertIn("Shock-adjusted cash flow", passing["shockAdjustedLabel"])
        self.assertEqual(passing["overlapWarning"], OVERLAP_WARNING_SHORT)
        self.assertEqual(passing["makeReadyIntro"], MAKE_READY_INTRO)

        failing = build_offer_ready_copy({**result, "dealSurvives": False})
        self.assertEqual(failing["survivalHeadline"], SURVIVAL_FAIL_HEADLINE)

    def test_teaching_module_has_no_forbidden_imports(self) -> None:
        tree = ast.parse(TEACHING_MODULE.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        forbidden_prefixes = (
            "capex3.rental_capex_calculator",
            "capex3.presentation",
            "capex3.infrastructure",
        )
        violations = [
            name
            for name in imports
            if any(
                name == prefix or name.startswith(f"{prefix}.")
                for prefix in forbidden_prefixes
            )
        ]
        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
