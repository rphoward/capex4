import unittest

from capex3.presentation.htmx_evidence_debug import (
    _debug_panel,
    _diagnostics_section,
)
from capex3.presentation.htmx_state import _build_state


class EvidenceDebugRenderTest(unittest.TestCase):
    def test_diagnostics_section_renders_linkage_table(self) -> None:
        state = _build_state({}, "calculate")
        html = _diagnostics_section(state)

        self.assertIn('data-evidence-layer="diagnostics"', html)
        self.assertIn('class="diagnostics-drilldown" id="diagnostics-drilldown"', html)
        self.assertIn("<span>Show table</span>", html)
        self.assertIn('class="diag-tbl" id="diagnostics-table"', html)
        self.assertIn(
            "<th>Engine field</th><th>User label</th><th>UI value</th>"
            "<th>Engine value</th><th>Workbook cell</th>",
            html,
        )
        self.assertIn("Dashboard!B6", html)
        self.assertIn("dashboard.trueMonthlyCashFlow", html)

    def test_debug_panel_renders_json_expander(self) -> None:
        state = _build_state({}, "calculate")
        html = _debug_panel(state)

        self.assertIn('class="debug-panel"', html)
        self.assertIn("Calculation diagnostics", html)
        self.assertIn('id="debug-output"', html)
        self.assertIn('class="debug-table"', html)


if __name__ == "__main__":
    unittest.main()
