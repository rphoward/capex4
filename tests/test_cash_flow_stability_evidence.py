import ast
import unittest
from pathlib import Path

from capex3.presentation.http_contracts import calculate_payload
from capex3.core.teaching.cash_flow_stability_evidence import (
    CASH_FLOW_STABILITY_CONTRACT_SOURCE,
    CASH_FLOW_STABILITY_EVIDENCE_CONCEPT,
    CASH_FLOW_STABILITY_LAYER_ID,
    FIELD_ROLE_CATALOG,
    PRIMARY_FRAMING_COPY,
    TRACE_DEBT_SHOCK_ROW_ROLES,
    TRACE_PLANNED_ROW_ROLES,
    cash_flow_stability_evidence_to_contract,
    catalog_entry,
    describe_cash_flow_stability_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TEACHING_MODULE = (
    REPO_ROOT
    / "src"
    / "capex3"
    / "core"
    / "teaching"
    / "cash_flow_stability_evidence.py"
)
KNOWN_RESOLVERS = frozenset({"dotPath", "maxMonthlyPayment", "resultRef"})


class CashFlowStabilityEvidenceTest(unittest.TestCase):
    def test_evidence_concept_exports_layer_metadata(self) -> None:
        self.assertEqual(CASH_FLOW_STABILITY_LAYER_ID, "cashFlowStability")
        self.assertEqual(
            CASH_FLOW_STABILITY_EVIDENCE_CONCEPT["title"],
            "Cash Flow Stability",
        )
        self.assertEqual(CASH_FLOW_STABILITY_EVIDENCE_CONCEPT["shortLabel"], "S")

    def test_field_role_catalog_covers_planned_and_debt_shock_paths(self) -> None:
        path_kinds = {entry.path_kind for entry in FIELD_ROLE_CATALOG}
        self.assertIn("planned", path_kinds)
        self.assertIn("debtShock", path_kinds)
        roles = {entry.role for entry in FIELD_ROLE_CATALOG}
        self.assertIn("plannedMonthlyReserve", roles)
        self.assertIn("peakEmergencyPayment", roles)
        self.assertIn("overlapDetected", roles)
        for entry in FIELD_ROLE_CATALOG:
            self.assertIn(entry.resolver, KNOWN_RESOLVERS)

    def test_describe_contract_includes_framing_copy_and_field_roles(self) -> None:
        payload = calculate_payload({})
        contract = cash_flow_stability_evidence_to_contract(payload["result"])

        self.assertEqual(contract["layerId"], CASH_FLOW_STABILITY_LAYER_ID)
        self.assertEqual(contract["primaryFramingCopy"], PRIMARY_FRAMING_COPY)
        self.assertEqual(contract["contractSource"], CASH_FLOW_STABILITY_CONTRACT_SOURCE)
        self.assertGreater(len(contract["fieldRoles"]), 0)
        role_names = {role["role"] for role in contract["fieldRoles"]}
        self.assertIn("plannedMonthlyReserve", role_names)
        self.assertIn("peakEmergencyPayment", role_names)
        planned_role = next(
            role for role in contract["fieldRoles"] if role["role"] == "plannedMonthlyReserve"
        )
        self.assertEqual(planned_role["pathKind"], "planned")
        self.assertEqual(planned_role["resolver"], "dotPath")
        self.assertNotIn("path_kind", planned_role)
        trace_ref = next(
            role
            for role in contract["fieldRoles"]
            if role["role"] == "repairTraceCrossReference"
        )
        self.assertEqual(trace_ref["resolver"], "resultRef")
        self.assertEqual(trace_ref["value"], {"resultRef": "repairReservePathTrace"})

    def test_trace_two_path_rows_follow_catalog_roles(self) -> None:
        payload = calculate_payload({})
        trace = payload["result"]["traces"]["cashFlowStability"]
        planned_rows = trace["twoPathComparison"]["plannedReservePath"]["rows"]
        debt_shock_rows = trace["twoPathComparison"]["debtShockPath"]["rows"]

        self.assertEqual(
            [row["role"] for row in planned_rows],
            list(TRACE_PLANNED_ROW_ROLES),
        )
        self.assertEqual(
            [row["role"] for row in debt_shock_rows[: len(TRACE_DEBT_SHOCK_ROW_ROLES)]],
            list(TRACE_DEBT_SHOCK_ROW_ROLES),
        )
        for row in planned_rows + debt_shock_rows[: len(TRACE_DEBT_SHOCK_ROW_ROLES)]:
            entry = catalog_entry(str(row["role"]))
            self.assertEqual(row["label"], entry.label)
            self.assertEqual(row["kind"], entry.value_kind)

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

    def test_describe_from_raw_result_matches_helper(self) -> None:
        payload = calculate_payload({})
        described = describe_cash_flow_stability_evidence(payload["result"])
        self.assertEqual(
            described.to_contract_dict(),
            cash_flow_stability_evidence_to_contract(payload["result"]),
        )


if __name__ == "__main__":
    unittest.main()
