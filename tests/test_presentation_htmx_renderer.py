from http import HTTPStatus
import json
import re
from pathlib import Path
import unittest
from unittest.mock import patch

from capex3.presentation import htmx_charts
from capex3.presentation.htmx_page import FONTS_STYLESHEET_PATH, render_full_page
from capex3.presentation.htmx_renderer import _resolve_overlap_warning_latch
from capex3.presentation.rental_capex_http_api import HtmlResponse
from capex3.presentation.rental_capex_http_api import handle_get
from capex3.presentation.rental_capex_http_api import handle_post
from capex3.core.teaching.offer_ready_evidence import (
    OVERLAP_WARNING_SHORT,
    SURVIVAL_FAIL_HEADLINE,
)
from capex3.presentation.http_contracts import (
    METRIC_GUIDANCE,
    METRIC_SOURCE_NOTES,
    calculate_payload,
    defaults_payload,
    workbench_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
STYLESHEET_PATH = REPO_ROOT / "src" / "capex3" / "presentation" / "browser_assets" / "styles.css"
TOKENS_CSS_PATH = REPO_ROOT / "src" / "capex3" / "presentation" / "browser_assets" / "tokens.css"
FONTS_CSS_PATH = REPO_ROOT / "src" / "capex3" / "presentation" / "browser_assets" / "fonts.css"


def _css_hex_token(stylesheet: str, token_name: str) -> str:
    match = re.search(rf"{re.escape(token_name)}:\s*(#[0-9a-fA-F]{{6}})", stylesheet)
    if match is None:
        raise AssertionError(f"Missing CSS token {token_name}")
    return match.group(1).lower()


class PresentationHtmxRendererTest(unittest.TestCase):
    def test_ui_actions_return_server_rendered_fragments_without_app_javascript(self) -> None:
        actions = [
            ("GET", "/ui/app", {}),
            ("POST", "/ui/calculate", {}),
            ("POST", "/ui/step", {"activeStep": "decision"}),
            ("POST", "/ui/evidence", {"activeEvidenceLayer": "whatWorks"}),
            ("POST", "/ui/metric", {"activeMetricField": "year10Roi"}),
            ("POST", "/ui/reset", {"actualGrossMonthlyRent": "9999"}),
            ("POST", "/ui/new-walkthrough", {"activeStep": "walkthrough"}),
            (
                "POST",
                "/ui/override",
                {
                    "activeStep": "walkthrough",
                    "overrideComponent": "Roofing: Arch. Asphalt (per sq)",
                    "overrideQuantity": "33",
                    "overrideAge": "7",
                },
            ),
            (
                "POST",
                "/ui/solve",
                {
                    "activeStep": "decision",
                    "solverVariable": "rent",
                    "solverMetric": "monthlyCashFlow",
                    "solverTarget": "0",
                },
            ),
            (
                "POST",
                "/ui/solve-threshold",
                {
                    "activeStep": "decision",
                    "activeEvidenceLayer": "whatWorks",
                    "questionId": "breakEvenRent",
                },
            ),
            (
                "POST",
                "/ui/apply-solver",
                {
                    "activeStep": "decision",
                    "solverApplyField": "actualGrossMonthlyRent",
                    "solverSolvedValue": "4200",
                },
            ),
        ]

        for method, path, form in actions:
            with self.subTest(path=path):
                response = handle_get(path) if method == "GET" else handle_post(path, form)

                self.assertIsInstance(response, HtmlResponse)
                self.assertEqual(HTTPStatus.OK, response.status)
                self.assertIn('id="app"', response.body)
                self.assertIn('hx-target="#app"', response.body)
                self.assertIn('hx-swap="outerHTML"', response.body)
                self.assertNotIn("<script", response.body)
                self.assertNotIn('type="' + 'module"', response.body)
                self.assertNotIn("/assets/" + "modules/", response.body)
                self.assertNotIn("fetch" + "(", response.body)
                self.assertNotIn("XML" + "HttpRequest", response.body)
                self.assertNotIn("http" + "://", response.body)
                self.assertNotIn("https" + "://", response.body)

    def test_threshold_solver_preserves_question_and_apply_contract(self) -> None:
        response = handle_post(
            "/ui/solve-threshold",
            {
                "activeStep": "decision",
                "activeEvidenceLayer": "whatWorks",
                "questionId": "breakEvenRent",
            },
        )

        self.assertIsInstance(response, HtmlResponse)
        self.assertIn("Preview ready", response.body)
        self.assertIn(
            'id="run-status" role="status" aria-live="polite">Preview ready</div>',
            response.body,
        )
        self.assertIn('data-evidence-layer="whatWorks"', response.body)
        self.assertIn('name="solverApplyField" value="actualGrossMonthlyRent"', response.body)
        self.assertIn('name="solverSolvedValue"', response.body)
        self.assertIn('data-solver-apply hx-post="/ui/apply-solver"', response.body)
        self.assertNotIn("Couldn't solve", response.body)

    def test_apply_solver_updates_server_owned_form_state(self) -> None:
        response = handle_post(
            "/ui/apply-solver",
            {
                "activeStep": "decision",
                "solverApplyField": "actualGrossMonthlyRent",
                "solverSolvedValue": "4200",
            },
        )

        self.assertIsInstance(response, HtmlResponse)
        self.assertIn(
            'id="run-status" role="status" aria-live="polite">Ready</div>',
            response.body,
        )
        self.assertIn('name="activeStep" value="decision"', response.body)
        self.assertIn('name="actualGrossMonthlyRent" value="4200.0"', response.body)
        self.assertNotIn("Preview ready", response.body)

    def test_reset_restores_default_inputs_and_clears_walkthrough_overrides(self) -> None:
        default_rent = str(defaults_payload()["inputs"]["actualGrossMonthlyRent"])

        changed = handle_post(
            "/ui/calculate",
            {
                "activeStep": "listing",
                "actualGrossMonthlyRent": "9999",
            },
        )
        self.assertIn('name="actualGrossMonthlyRent"', changed.body)
        self.assertIn('value="9999', changed.body)

        with_override = handle_post(
            "/ui/override",
            {
                "activeStep": "walkthrough",
                "overrideComponent": "Roofing: Arch. Asphalt (per sq)",
                "overrideQuantity": "33",
                "overrideAge": "7",
            },
        )
        self.assertIn("Roofing: Arch. Asphalt (per sq)", with_override.body)
        self.assertNotIn("No active overrides", with_override.body)

        reset = handle_post(
            "/ui/reset",
            {
                "activeStep": "walkthrough",
                "actualGrossMonthlyRent": "9999",
                "componentOverridesJson": '{"Roofing: Arch. Asphalt (per sq)": {"age": 7}}',
            },
        )
        self.assertNotIn('value="9999', reset.body)
        self.assertIn(f'value="{default_rent}"', reset.body)
        self.assertIn('name="actualGrossMonthlyRent"', reset.body)
        self.assertIn('name="componentOverridesJson" value="{}"', reset.body)
        self.assertIn("No active overrides", reset.body)
        self.assertEqual(1, reset.body.count('hx-post="/ui/reset"'))

    def test_malformed_hidden_state_falls_back_to_default_renderable_ui(self) -> None:
        response = handle_post(
            "/ui/calculate",
            {
                "activeStep": "missing-step",
                "activeEvidenceLayer": "missing-layer",
                "componentOverridesJson": "{not-json",
            },
        )

        self.assertIsInstance(response, HtmlResponse)
        self.assertIn(
            'id="run-status" role="status" aria-live="polite">Ready</div>',
            response.body,
        )
        self.assertIn('id="active-step-title">Listing Check</h2>', response.body)
        self.assertIn('id="evidence-title">10-Year Story</h2>', response.body)
        self.assertIn('name="componentOverridesJson" value="{}"', response.body)

    def test_user_supplied_text_is_escaped_in_server_rendered_markup(self) -> None:
        malicious_address = '<script>alert("x")</script>'

        response = handle_post(
            "/ui/calculate",
            {
                "activeStep": "listing",
                "propertyAddress": malicious_address,
            },
        )

        self.assertIsInstance(response, HtmlResponse)
        self.assertNotIn(malicious_address, response.body)
        self.assertNotIn("<script>", response.body)
        self.assertIn(
            'value="&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"',
            response.body,
        )

    def test_handoff_shell_visual_markers_are_server_rendered_and_css_owned(self) -> None:
        response = handle_get("/")
        stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")
        tokens = TOKENS_CSS_PATH.read_text(encoding="utf-8")

        self.assertIsInstance(response, HtmlResponse)
        self.assertIn('class="topbar-left"', response.body)
        self.assertIn('class="brand-lockup"', response.body)
        self.assertIn('class="deal-label" id="deal-label">New property · Avg Rent: 2-Bedroom</p>', response.body)
        self.assertIn('class="input-panel left-panel calc-inputs"', response.body)
        self.assertIn('class="output-panel right-panel calc-results"', response.body)
        self.assertIn('class="calc-workbench"', response.body)
        self.assertIn('id="results-summary"', response.body)
        self.assertIn('class="summary-value num-display"', response.body)
        self.assertIn('class="summary-panel results-hero-kpi"', response.body)
        self.assertIn("Year 1 Total Return on Equity", response.body)
        self.assertIn('class="active-step active-step-summary"', response.body)
        self.assertIn('class="journey-step active"', response.body)
        self.assertIn('class="evidence-tab active"', response.body)
        self.assertIn("--canvas:", tokens)
        self.assertIn("--amber:", tokens)
        self.assertIn("--hairline:", tokens)
        self.assertIn("--depth-shadow:", tokens)
        self.assertIn(".deal-label", stylesheet)
        self.assertIn("grid-template-columns: minmax(300px, var(--input-col)) minmax(420px, var(--results-col));", stylesheet)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 68px;", stylesheet)
        self.assertIn("overflow-y: auto;", stylesheet)
        self.assertIn("overscroll-behavior: contain;", stylesheet)
        self.assertIn("border-radius: var(--radius-shell);", stylesheet)
        self.assertIn("border: 1px solid var(--hairline)", stylesheet)
        self.assertIn('href="/assets/tokens.css"', response.body)
        self.assertIn('src="/assets/vendor/htmx.min.js"', response.body)
        self.assertNotIn('src="/assets/vendor/highcharts.js"', response.body)
        self.assertNotIn('src="/assets/charts.js"', response.body)
        self.assertNotIn('type="' + 'module"', response.body)
        self.assertNotIn("/assets/" + "modules/", response.body)
        self.assertNotIn("https" + "://", stylesheet)

    def test_refero_font_links_and_chart_token_parity(self) -> None:
        page = render_full_page()
        stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")
        tokens = TOKENS_CSS_PATH.read_text(encoding="utf-8")
        combined_css = tokens + stylesheet
        fonts_css = FONTS_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn('rel="preconnect" href="https://fonts.googleapis.com"', page)
        self.assertIn(FONTS_STYLESHEET_PATH, page)
        self.assertIn('href="/assets/tokens.css"', page)
        self.assertIn("Source+Sans+3", fonts_css)
        self.assertIn("Source+Serif+4", fonts_css)
        self.assertIn("IBM+Plex+Mono", fonts_css)
        self.assertIn("--font-ui:", combined_css)
        self.assertIn("--font-display:", combined_css)
        self.assertIn("--font-mono:", combined_css)
        self.assertIn("--link:", combined_css)
        self.assertIn("--positive:", combined_css)
        self.assertIn("--negative:", combined_css)
        self.assertIn("--chart-grid:", combined_css)
        self.assertIn("--chart-series-rental:", combined_css)

        self.assertEqual(
            _css_hex_token(tokens, "--chart-series-rental"),
            htmx_charts.CHART_RENTAL.lower(),
        )
        self.assertEqual(
            _css_hex_token(tokens, "--chart-series-cashflow"),
            htmx_charts.CHART_CASHFLOW.lower(),
        )
        self.assertEqual(
            _css_hex_token(tokens, "--chart-series-mm"),
            htmx_charts.CHART_STONE.lower(),
        )
        self.assertEqual(
            _css_hex_token(tokens, "--chart-series-ira"),
            htmx_charts.CHART_COPPER.lower(),
        )

    def test_slice2_journey_fields_controls_and_decision_packet_placeholder(self) -> None:
        listing = handle_get("/")
        walkthrough = handle_post("/ui/step", {"activeStep": "walkthrough"})
        loan = handle_post("/ui/step", {"activeStep": "loan"})
        decision = handle_post("/ui/step", {"activeStep": "decision"})

        listing_fields = _field_grid_markup(listing.body)
        self.assertIn("Property label or address", listing_fields)
        self.assertIn("Area", listing_fields)
        self.assertIn("Property type", listing_fields)
        self.assertIn("Purchase price", listing_fields)
        self.assertIn("Expected monthly rent", listing_fields)
        self.assertIn("Annual property taxes", listing_fields)
        self.assertNotIn("Monthly HOA", listing_fields)
        self.assertNotIn("Management fee", listing_fields)
        self.assertIn('id="recalculate-button"', listing.body)
        self.assertIn('id="next-step-button"', listing.body)
        self.assertIn('value="walkthrough"', listing.body)

        walkthrough_fields = _field_grid_markup(walkthrough.body)
        self.assertIn("Overall effective age", walkthrough_fields)
        self.assertIn("Repair-cost inflation", walkthrough_fields)
        self.assertIn("Annual cleaning and maintenance", walkthrough_fields)
        self.assertIn("Rough rehab or make-ready", walkthrough_fields)
        self.assertNotIn("Age Check", walkthrough.body)
        self.assertNotIn("Size / Count Check", walkthrough.body)
        self.assertIn('value="loan"', walkthrough.body)

        loan_fields = _field_grid_markup(loan.body)
        self.assertIn("Down payment", loan_fields)
        self.assertIn("Loan interest rate", loan_fields)
        self.assertIn("Loan term", loan_fields)
        self.assertIn("Repair fund APY", loan_fields)
        self.assertIn("Emergency loan APR", loan_fields)
        self.assertIn("Emergency loan term", loan_fields)
        self.assertIn("Estimated closing cost rate", loan_fields)
        self.assertIn("Monthly HOA", loan_fields)
        self.assertIn("Annual insurance", loan_fields)
        self.assertIn("Management fee", loan_fields)
        self.assertIn("Closing cost override", loan_fields)
        self.assertIn('value="decision"', loan.body)

        self.assertNotIn('id="decision-packet-placeholder"', decision.body)
        self.assertIn("Decision Packet", decision.body)
        self.assertNotIn("Generate packet", decision.body)
        self.assertNotIn('id="journey-actions"', decision.body)

    def test_phase4_slice3_operating_expense_hidden_defaults(self) -> None:
        walkthrough = handle_post("/ui/step", {"activeStep": "walkthrough"})
        loan = handle_post("/ui/step", {"activeStep": "loan"})

        walkthrough_fields = _field_grid_markup(walkthrough.body)
        self.assertIn("Annual cleaning and maintenance", walkthrough_fields)
        self.assertIn("Annual legal and professional", walkthrough_fields)
        self.assertIn("Annual advertising and leasing", walkthrough_fields)
        self.assertIn('name="legalProfessionalAnnual"', walkthrough_fields)
        self.assertIn('name="advertisingLeasingAnnual"', walkthrough_fields)

        loan_fields = _field_grid_markup(loan.body)
        self.assertIn("Monthly HOA", loan_fields)
        self.assertIn("Monthly landlord-paid utilities", loan_fields)
        self.assertIn('name="monthlyUtilitiesLandlordPaid"', loan_fields)
        self.assertIn("Annual insurance", loan_fields)

    def test_slice2_metric_strip_and_pin_controls_are_server_rendered(self) -> None:
        default = handle_get("/")
        pinned = handle_post(
            "/ui/evidence",
            {
                "activeStep": "walkthrough",
                "activeEvidenceLayer": "repairDrivers",
            },
        )

        strip = _metric_strip_markup(default.body)
        self.assertEqual(3, strip.count('name="activeMetricField"'))
        self.assertIn("True monthly cash flow", strip)
        self.assertIn("Monthly repair fund", strip)
        self.assertIn("Break-even rent", strip)
        self.assertIn("See the breakdown", strip)
        self.assertIn("See what drives it", strip)
        self.assertIn("What would work?", strip)
        self.assertIn('value="trueMonthlyCashFlow"', strip)
        self.assertIn('value="totalMonthlyCapexReserve"', strip)
        self.assertIn('value="breakevenGrossRent"', strip)

        self.assertIn('id="evidence-mode">Following Listing Check</p>', default.body)
        self.assertIn('id="evidence-follow" name="evidenceFollowsStep" type="checkbox" value="true" checked', default.body)
        self.assertIn('id="evidence-mode">Viewing: Repair Drivers</p>', pinned.body)
        self.assertNotIn('class="pin-badge">Pinned</span>', pinned.body)
        self.assertIn('id="overview-button"', pinned.body)
        self.assertIn('name="activeEvidenceLayer" value="tenYear"', pinned.body)
        self.assertIn("Follow current step", pinned.body)

    def test_slice3_ten_year_story_uses_source_chart_shell_and_four_series(self) -> None:
        response = handle_get("/")
        stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")

        self.assertIn('class="chart-wrap chart-stage" id="ten-year-story-chart"', response.body)
        self.assertIn('class="chart-side-legend"', response.body)
        self.assertIn('class="svg-wrap chart-canvas">', response.body)
        self.assertIn("<svg", response.body)
        self.assertIn('class="ten-year-series rental"', response.body)
        self.assertIn('class="ten-year-series cash-flow"', response.body)
        self.assertIn('class="ten-year-series money-market"', response.body)
        self.assertIn('class="ten-year-series ira"', response.body)
        self.assertIn('class="rental-area"', response.body)
        self.assertIn('class="endpoint-label', response.body)
        self.assertNotIn('class="highcharts-host"', response.body)
        self.assertNotIn("data-highcharts-config=", response.body)
        self.assertIn("Liquidation wealth", response.body)
        self.assertIn("Cash position (operating + initial)", response.body)
        self.assertIn("Money market", response.body)
        self.assertIn(">IRA</span>", response.body)
        self.assertIn("four paths compared", response.body)
        self.assertIn("Alternative paths use the money", response.body)
        self.assertIn(".chart-wrap", stylesheet)
        self.assertIn(".chart-side-legend", stylesheet)
        self.assertIn(".svg-wrap svg", stylesheet)
        self.assertIn('value="repairFund"', response.body)
        self.assertIn("Repair Fund", response.body)

    def test_slice5_repair_fund_layer_renders_live_trace_chart_and_summary(self) -> None:
        response = handle_post("/ui/evidence", {"activeEvidenceLayer": "repairFund"})
        stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")
        body = response.body

        self.assertIn('data-evidence-layer="repairFund"', body)
        self.assertIn('id="repair-fund-story-chart"', body)
        self.assertIn('id="repair-fund-info"', body)
        self.assertIn("Reserve balance vs. no-reserve surprise cost", body)
        self.assertIn("<svg", body)
        self.assertIn('class="repair-balance-series"', body)
        self.assertIn('class="repair-surprise-series"', body)
        self.assertIn('class="repair-event-marker"', body)
        self.assertNotIn('class="highcharts-host"', body)
        self.assertNotIn("&quot;step&quot;:&quot;left&quot;", body)
        self.assertIn('class="chart-legend repair-fund-legend"', body)
        self.assertIn('aria-label="Repair fund chart series"', body)
        self.assertIn("Cumulative surprise cost", body)
        self.assertIn('id="repair-fund-cards"', body)
        self.assertIn("Dashboard monthly rate", body)
        self.assertIn("reserve cap", body)
        self.assertIn("Largest single repair", body)
        self.assertIn('class="fund-tbl" id="repair-fund-table"', body)
        self.assertIn("repairReservePathTrace", body)
        self.assertNotIn("Teaching-only", body)
        self.assertNotIn("not workbook-contract", body)
        self.assertNotIn("Do not describe this layer as spreadsheet parity", body)
        self.assertNotIn('class="layer-copy disclaimer teaching-only"', body)
        self.assertNotIn(
            "repair_reserve_path_trace_workbook_vs_teaching",
            body,
        )
        self.assertIn("Dashboard rate", body)
        self.assertNotIn("(B34)", body)
        self.assertIn("not every year adds new set-aside", body)
        self.assertNotIn("/mo set aside - balance rebuilds", body)
        self.assertNotIn("savings rise from monthly deposits", body)
        self.assertIn(".repair-event-marker", stylesheet)
        self.assertNotIn(".layer-copy.disclaimer.teaching-only", stylesheet)

    def test_repair_fund_layer_surfaces_interest_earned_on_reserve(self) -> None:
        payload = calculate_payload({})
        trace = payload["result"]["traces"]["repairFund"]
        cumulative_interest = sum(
            row.get("interestEarned", 0) for row in trace["rows"]
        )
        self.assertGreater(cumulative_interest, 0)

        response = handle_post("/ui/evidence", {"activeEvidenceLayer": "repairFund"})
        body = response.body

        self.assertIn("Repair fund APY", body)
        self.assertIn("Interest earned Yr 0-10", body)
        self.assertIn("Interest-bearing reserve account", body)
        self.assertIn("not checking cash", body)
        self.assertIn("<th>Interest earned</th>", body)
        self.assertIn('class="evidence-card"', body)
        self.assertIn('id="repair-fund-cards"', body)
        year_one_interest = trace["rows"][1]["interestEarned"]
        self.assertIn(f"${year_one_interest:,.0f}", body)

    def test_slice6_solver_decision_step_workbench_disclaimer(self) -> None:
        response = handle_post("/ui/step", {"activeStep": "decision"})
        body = response.body
        stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")

        self.assertIn('id="solver-workbench"', body)
        self.assertIn("solver-workbench-disclaimer", body)
        self.assertIn("Each preview solves for one input", body)
        self.assertNotIn("not workbook-canonical", body)
        self.assertNotIn("fixtureContract.solverCasePolicy", body)
        self.assertNotIn("solve_rental_capex", body)
        self.assertIn(".layer-copy.disclaimer.solver-note", stylesheet)

    def test_slice6_solver_preview_and_what_works_regression_copy(self) -> None:
        solve = handle_post(
            "/ui/solve",
            {
                "activeStep": "decision",
                "solverVariable": "rent",
                "solverMetric": "monthlyCashFlow",
                "solverTarget": "0",
            },
        )
        self.assertIn("solver-preview-footnote", solve.body)
        self.assertNotIn("not workbook-canonical solver output", solve.body)

        what_works = handle_post("/ui/evidence", {"activeEvidenceLayer": "whatWorks"})
        body = what_works.body
        what_works_layer = body.split('data-evidence-layer="whatWorks"', 1)[1].split(
            "</section>",
            1,
        )[0]

        self.assertIn('class="evidence-reward-label">Threshold questions</p>', what_works_layer)
        self.assertNotIn('class="layer-copy disclaimer teaching-only"', what_works_layer)
        self.assertIn("Thresholds under current assumptions", what_works_layer)
        self.assertNotIn("app regression solver", body.lower())
        self.assertNotIn("not workbook-canonical solver output", body.lower())

    def test_slice5_repair_fund_zero_monthly_reserve_copy(self) -> None:
        component_overrides = {
            component["name"]: {"quantity": 0, "age": 0}
            for component in defaults_payload()["assumptions"]["components"]
        }
        response = handle_post(
            "/ui/evidence",
            {
                "activeEvidenceLayer": "repairFund",
                "componentOverridesJson": json.dumps(component_overrides),
            },
        )
        body = response.body

        self.assertIn("No monthly repair reserve is modeled for this deal.", body)
        self.assertIn("No monthly reserve is modeled for this deal.", body)
        self.assertNotIn("/mo set aside", body)

    def test_phase3_slice2_ten_year_sale_bridge_receipts_render_on_calculate(self) -> None:
        response = handle_post("/ui/calculate", {})
        summary = response.body.split('id="ten-year-summary"', 1)[1].split(
            "</section>",
            1,
        )[0]

        self.assertIn('data-evidence-layer="tenYear"', response.body)
        self.assertIn("Future property value", summary)
        self.assertIn("Remaining loan balance", summary)
        self.assertIn("Cost of sale", summary)
        self.assertIn("Net proceeds", summary)
        self.assertIn("Accumulated operating cash", summary)
        self.assertIn("Reserve returned at sale", summary)
        self.assertNotIn("Source: 10-Year Pro Forma B23", summary)
        self.assertNotIn("Formula: B23", summary)
        self.assertIn("Capped reserve balance returned at sale", summary)

    def test_phase3_slice3_ten_year_dual_label_table_and_chart_honesty(self) -> None:
        response = handle_post("/ui/calculate", {})
        summary = response.body.split('id="ten-year-summary"', 1)[1].split(
            "</section>",
            1,
        )[0]
        body = response.body

        self.assertIn("Year-10 ROI", summary)
        self.assertIn("Liquidation wealth", summary)
        self.assertIn("Excludes reserve returned at sale", summary)
        self.assertIn("Includes accumulated reserve returned at sale", summary)
        self.assertIn("Liquidation wealth</th>", body)
        self.assertIn("Accumulated cash</th>", body)
        self.assertIn("Annual reserve contribution</th>", body)
        self.assertIn("Accumulated reserve</th>", body)
        self.assertIn("Future property value</th>", body)
        self.assertIn("Remaining loan balance</th>", body)
        self.assertIn("Cost of sale</th>", body)
        self.assertIn("Net proceeds</th>", body)
        self.assertIn("Cash position (operating + initial)</th>", body)
        self.assertIn("cash position (operating + initial)", body.lower())
        self.assertNotIn("<th>Rental path</th>", body)

    def test_slice3_cash_flow_receipt_hides_engine_fields_in_reward_shows_in_drilldown(
        self,
    ) -> None:
        response = handle_post("/ui/evidence", {"activeEvidenceLayer": "cashFlow"})
        stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")
        cash_flow_layer = response.body.split('data-evidence-layer="cashFlow"', 1)[1].split(
            "</section>",
            1,
        )[0]
        reward = cash_flow_layer.split('id="cash-flow-receipt">', 1)[1].split(
            '<details class="evidence-drilldown">',
            1,
        )[0]
        drilldown = cash_flow_layer.split('<details class="evidence-drilldown">', 1)[1]

        self.assertIn('class="receipt receipt-waterfall evidence-reward"', response.body)
        self.assertIn('class="receipt-panel-kicker">Cash flow breakdown</p>', cash_flow_layer)
        self.assertIn("Expected monthly rent", reward)
        self.assertIn("Vacancy rate", reward)
        self.assertIn("Usable income", reward)
        self.assertIn("Monthly repair fund (snapshot)", reward)
        self.assertIn("True monthly cash flow", reward)
        self.assertIn('class="rcpt-row sub"', reward)
        self.assertIn('class="rcpt-row total-row"', reward)
        self.assertIn('class="rcpt-val ded">-$', reward)
        self.assertIn('class="rcpt-val neg">-$', reward)
        self.assertNotIn('class="rcpt-eng">actualGrossMonthlyRent</span>', reward)
        self.assertIn(".rcpt-eng", stylesheet)
        self.assertNotIn('class="rcpt-eng">actualGrossMonthlyRent</span>', drilldown)
        self.assertNotIn('class="rcpt-eng">totalMonthlyCapexReserve</span>', drilldown)
        self.assertIn("See calculation details", response.body)

    def test_phase3_slice4_cash_flow_snapshot_labels_and_pro_forma_pointer(self) -> None:
        response = handle_post("/ui/evidence", {"activeEvidenceLayer": "cashFlow"})
        body = response.body

        self.assertIn('data-evidence-layer="cashFlow"', body)
        self.assertIn("dashboard snapshot:", body)
        self.assertIn("accumulated cash flow", body)
        self.assertIn("10-Year Story", body)
        self.assertIn("Monthly repair fund (snapshot)", body)
        self.assertIn("True monthly cash flow", body)

        trace = calculate_payload({})["result"]["traces"]["cashFlow"]
        bar_labels = [bar["label"] for bar in trace["graph"]["bars"]]
        self.assertIn("Repair fund (snapshot)", bar_labels)
        self.assertIn("True monthly cash flow", bar_labels)

        guidance = {
            item["field"]: item
            for item in workbench_payload()["workbench"]["metricGuidance"]
        }
        self.assertEqual(
            guidance["trueMonthlyCashFlow"]["label"],
            "True monthly cash flow",
        )
        self.assertIn("Dashboard underwriting snapshot", guidance["trueMonthlyCashFlow"]["sourceNote"])
        self.assertIn("accumulated cash flow", guidance["trueMonthlyCashFlow"]["sourceNote"])
        self.assertEqual(
            METRIC_GUIDANCE[0][1],
            "True monthly cash flow",
        )
        self.assertNotIn("B40", METRIC_SOURCE_NOTES["trueMonthlyCashFlow"])

    def test_slice3_repair_drivers_render_summary_cards_share_bars_and_other_bucket(self) -> None:
        response = handle_post("/ui/evidence", {"activeEvidenceLayer": "repairDrivers"})
        stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")

        self.assertIn('id="repair-drivers-cards"', response.body)
        self.assertIn("Total monthly reserve", response.body)
        self.assertIn("Components tracked", response.body)
        self.assertIn("Walkthrough overrides", response.body)
        self.assertIn('class="drv-tbl" id="repair-drivers-table"', response.body)
        self.assertIn("<th>Share</th>", response.body)
        self.assertIn("<th>Remaining</th>", response.body)
        self.assertIn('class="bar-tr"', response.body)
        self.assertIn('class="bar-fl" style="width:', response.body)
        self.assertIn("Other (", response.body)
        self.assertIn(".drv-tbl", stylesheet)
        self.assertIn(".bar-tr", stylesheet)
        self.assertIn(".age-warn", stylesheet)

    def test_slice3_what_works_reward_hides_ids_solver_note_in_drilldown(self) -> None:
        what_works = handle_post("/ui/evidence", {"activeEvidenceLayer": "whatWorks"})
        stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")
        body = what_works.body

        self.assertIn('class="slv-grid evidence-reward" id="threshold-grid"', body)
        self.assertIn('class="slv-card threshold-card threshold-warn"', body)
        self.assertNotIn('class="threshold-id">breakEvenRent</p>', body)
        self.assertIn("What rent would make monthly cash flow hit zero?", body)
        self.assertIn('class="slv-v">$', body)
        self.assertIn('class="slv-gap">$', body)
        self.assertIn('hx-post="/ui/solve-threshold"', body)
        self.assertIn("Assumptions behind the numbers", body)
        self.assertNotIn("fixtureContract.solverCasePolicy", body)
        self.assertNotIn("app-side regression", body.lower())
        self.assertIn(".slv-grid", stylesheet)
        self.assertIn(".evidence-drilldown", stylesheet)

    def test_stakeholder_ui_excludes_debug_diagnostics_and_metric_detail(self) -> None:
        response = handle_get("/")
        body = response.body

        self.assertNotIn('class="debug-panel"', body)
        self.assertNotIn("Calculation diagnostics", body)
        self.assertNotIn('data-evidence-layer="diagnostics"', body)
        self.assertNotIn('data-evidence-layer="metricDetail"', body)
        self.assertNotIn('class="diagnostics-drilldown"', body)

    def test_metric_strip_reserve_navigates_to_repair_drivers(self) -> None:
        response = handle_post(
            "/ui/metric",
            {"activeMetricField": "totalMonthlyCapexReserve"},
        )
        body = response.body

        self.assertIn('name="activeEvidenceLayer" value="repairDrivers"', body)
        self.assertIn('id="evidence-title">Repair Drivers</h2>', body)
        self.assertIn('data-evidence-layer="repairDrivers"', body)
        self.assertNotIn('data-evidence-layer="repairFund"', body.split(
            'data-evidence-layer="repairDrivers"',
            1,
        )[0])

    def test_metric_strip_cash_flow_focuses_receipt_reward(self) -> None:
        response = handle_post(
            "/ui/metric",
            {"activeMetricField": "trueMonthlyCashFlow"},
        )
        cash_flow_layer = response.body.split('data-evidence-layer="cashFlow"', 1)[1].split(
            "</section>",
            1,
        )[0]

        self.assertIn('name="activeEvidenceLayer" value="cashFlow"', response.body)
        self.assertIn('id="metric-breakdown-panel"', response.body)
        self.assertIn(
            'class="receipt receipt-waterfall evidence-reward evidence-focus"',
            response.body,
        )

    def test_walkthrough_follow_step_opens_cash_flow_stability(self) -> None:
        response = handle_post("/ui/step", {"activeStep": "walkthrough"})
        body = response.body

        self.assertIn('id="evidence-title">Cash Flow Stability</h2>', body)
        self.assertIn('id="evidence-mode">Following Walkthrough</p>', body)
        self.assertIn('data-evidence-layer="cashFlowStability"', body)

    def test_phase5_slice6_cash_flow_stability_evidence_layer_renders(self) -> None:
        response = handle_post("/ui/evidence", {"activeEvidenceLayer": "cashFlowStability"})
        body = response.body
        stylesheet = STYLESHEET_PATH.read_text(encoding="utf-8")

        self.assertIn('data-evidence-layer="cashFlowStability"', body)
        self.assertIn("Cash Flow Stability", body)
        self.assertIn('id="cash-flow-stability-cards"', body)
        self.assertIn('id="cash-flow-stability-two-path"', body)
        self.assertIn("Planned reserve path", body)
        self.assertIn("Debt-shock path", body)
        self.assertIn('id="cash-flow-stability-refi-table"', body)
        self.assertIn('id="cash-flow-stability-payment-table"', body)
        self.assertIn("Not reserving does not remove the repair", body)
        self.assertNotIn("App-only resilience", body)
        self.assertNotIn("not workbook-contract", body)
        self.assertIn(".two-path-comparison", stylesheet)
        self.assertIn(".offer-ready-panel", stylesheet)

    def test_phase5_slice6_offer_ready_panel_on_walkthrough(self) -> None:
        response = handle_post("/ui/step", {"activeStep": "walkthrough"})
        body = response.body

        self.assertIn('id="offer-ready-panel"', body)
        self.assertIn("Offer-ready survival", body)
        self.assertIn(SURVIVAL_FAIL_HEADLINE, body)
        self.assertIn("Shock-adjusted cash flow (worst month)", body)
        self.assertIn("True monthly cash flow", body)
        self.assertIn('id="new-walkthrough-button"', body)
        self.assertIn('hx-post="/ui/new-walkthrough"', body)
        self.assertIn('name="overlapWarningLatched"', body)
        self.assertIn('name="overlapWarningAgeSnapshotKey"', body)

    def test_offer_ready_stability_cta_navigates_to_cash_flow_stability(self) -> None:
        walkthrough = handle_post("/ui/step", {"activeStep": "walkthrough"})
        self.assertIn('class="offer-ready-stability-cta"', walkthrough.body)
        self.assertIn("See how reserves vs debt shock compare", walkthrough.body)
        self.assertIn(
            'name="activeEvidenceLayer" value="cashFlowStability" hx-post="/ui/evidence"',
            walkthrough.body,
        )

        navigated = handle_post(
            "/ui/evidence",
            {
                "activeStep": "walkthrough",
                "activeEvidenceLayer": "cashFlowStability",
                "evidenceFollowsStep": "false",
            },
        )
        self.assertIn('id="evidence-title">Cash Flow Stability</h2>', navigated.body)
        self.assertIn('data-evidence-layer="cashFlowStability"', navigated.body)

    def test_phase5_slice6_offer_ready_hidden_on_other_steps(self) -> None:
        response = handle_post("/ui/step", {"activeStep": "listing"})
        self.assertNotIn('id="offer-ready-panel"', response.body)

    def test_phase5_slice6_overlap_latch_display_when_posted(self) -> None:
        response = handle_post(
            "/ui/calculate",
            {
                "activeStep": "walkthrough",
                "overlapWarningLatched": "true",
                "overlapWarningAgeSnapshotKey": '{"componentAges":{},"effectiveAgeYears":0}',
            },
        )
        self.assertIn('id="overlap-warning"', response.body)
        self.assertIn(OVERLAP_WARNING_SHORT, response.body)
        self.assertIn('name="overlapWarningLatched" value="true"', response.body)

    def test_phase5_slice6_new_walkthrough_clears_overrides_and_latch(self) -> None:
        with_override = handle_post(
            "/ui/override",
            {
                "activeStep": "walkthrough",
                "overrideComponent": "Roofing: Arch. Asphalt (per sq)",
                "overrideQuantity": "33",
                "overrideAge": "7",
            },
        )
        self.assertIn("Roofing: Arch. Asphalt (per sq)", with_override.body)

        cleared = handle_post(
            "/ui/new-walkthrough",
            {
                "activeStep": "walkthrough",
                "overlapWarningLatched": "true",
                "overlapWarningAgeSnapshotKey": '{"componentAges":{"Roofing: Arch. Asphalt (per sq)":7},"effectiveAgeYears":0}',
            },
        )
        self.assertIn("No active overrides", cleared.body)
        self.assertIn('name="componentOverridesJson" value="{}"', cleared.body)
        self.assertIn('name="overlapWarningLatched" value="false"', cleared.body)
        self.assertIn('name="overlapWarningAgeSnapshotKey" value=""', cleared.body)
        self.assertNotIn('id="overlap-warning"', cleared.body)

    def test_phase5_slice6_latch_clears_when_age_snapshot_changes(self) -> None:
        latched = handle_post(
            "/ui/calculate",
            {
                "activeStep": "walkthrough",
                "overlapWarningLatched": "true",
                "overlapWarningAgeSnapshotKey": '{"componentAges":{},"effectiveAgeYears":0}',
            },
        )
        self.assertIn('name="overlapWarningLatched" value="true"', latched.body)

        changed = handle_post(
            "/ui/override",
            {
                "activeStep": "walkthrough",
                "overlapWarningLatched": "true",
                "overlapWarningAgeSnapshotKey": '{"componentAges":{},"effectiveAgeYears":0}',
                "overrideComponent": "Roofing: Arch. Asphalt (per sq)",
                "overrideAge": "12",
            },
        )
        self.assertIn('name="overlapWarningLatched" value="false"', changed.body)
        self.assertNotIn('id="overlap-warning"', changed.body)

    def test_phase5_slice6_reset_clears_overlap_latch(self) -> None:
        response = handle_post(
            "/ui/reset",
            {
                "activeStep": "walkthrough",
                "overlapWarningLatched": "true",
                "overlapWarningAgeSnapshotKey": '{"componentAges":{},"effectiveAgeYears":0}',
            },
        )
        self.assertIn('name="overlapWarningLatched" value="false"', response.body)
        self.assertIn('name="overlapWarningAgeSnapshotKey" value=""', response.body)

    def test_resolve_overlap_warning_latch_sets_on_overlap_detected(self) -> None:
        latched, key = _resolve_overlap_warning_latch(
            action="calculate",
            form={
                "overlapWarningLatched": "false",
                "overlapWarningAgeSnapshotKey": "",
            },
            current_snapshot_key='{"effectiveAgeYears":0,"componentAges":{}}',
            overlap_detected=True,
        )
        self.assertTrue(latched)
        self.assertEqual(key, '{"effectiveAgeYears":0,"componentAges":{}}')

    def test_phase5_slice6_overlap_latch_sets_on_calculate_when_overlap_detected(self) -> None:
        payload = calculate_payload({})
        result = dict(payload["result"])
        result["overlapDetected"] = True
        ledger = dict(result["emergencyDebtLedger"])
        ledger["overlapDetected"] = True
        ledger["overlapRefinanceYears"] = [3]
        result["emergencyDebtLedger"] = ledger

        with patch(
            "capex3.presentation.htmx_state.calculate_payload",
            return_value={"result": result},
        ):
            response = handle_post("/ui/calculate", {"activeStep": "walkthrough"})

        self.assertIn('name="overlapWarningLatched" value="true"', response.body)
        self.assertIn('id="overlap-warning"', response.body)

    def test_phase5_slice6_latch_survives_non_age_recalculate(self) -> None:
        response = handle_post(
            "/ui/calculate",
            {
                "activeStep": "walkthrough",
                "actualGrossMonthlyRent": "4500",
                "overlapWarningLatched": "true",
                "overlapWarningAgeSnapshotKey": '{"effectiveAgeYears":0,"componentAges":{}}',
            },
        )
        self.assertIn('name="overlapWarningLatched" value="true"', response.body)
        self.assertIn('id="overlap-warning"', response.body)
        self.assertIn('value="4500', response.body)

    def test_phase5_slice6_make_ready_warning_renders_from_ledger_reason(self) -> None:
        payload = calculate_payload({})
        result = dict(payload["result"])
        ledger = dict(result["emergencyDebtLedger"])
        ledger["makeReadyShortfallFlag"] = True
        ledger["reason"] = (
            "Near-term repairs from walkthrough exceed make-ready; not emergency-rate debt."
        )
        result["emergencyDebtLedger"] = ledger

        with patch(
            "capex3.presentation.htmx_state.calculate_payload",
            return_value={"result": result},
        ):
            response = handle_post("/ui/step", {"activeStep": "walkthrough"})

        self.assertIn('id="make-ready-warning"', response.body)
        self.assertIn("Make-ready shortfall flagged", response.body)
        self.assertIn("Near-term repairs from walkthrough", response.body)


class HtmxChartsSvgGeometryTest(unittest.TestCase):
    def test_point_centers_when_count_is_one(self) -> None:
        height = htmx_charts.TEN_YEAR_SVG_HEIGHT
        x, _ = htmx_charts._point(0, 100.0, 1, 0.0, 200.0, height)
        left, _, width, _ = htmx_charts._plot_area(height)
        self.assertAlmostEqual(x, left + width / 2)

    def test_point_maps_negative_value_into_plot_area(self) -> None:
        height = htmx_charts.TEN_YEAR_SVG_HEIGHT
        min_y, max_y = -100.0, 100.0
        _, y = htmx_charts._point(0, -50.0, 5, min_y, max_y, height)
        _, top, _, plot_height = htmx_charts._plot_area(height)
        mid_y = top + plot_height / 2
        baseline_y = top + plot_height
        self.assertGreater(y, mid_y)
        self.assertLess(y, baseline_y)

    def test_value_bounds_includes_negative_series(self) -> None:
        min_y, max_y = htmx_charts._value_bounds([-50.0, 10.0, 100.0])
        self.assertLess(min_y, 0.0)
        self.assertGreater(max_y, 100.0)

    def test_step_path_holds_then_jumps(self) -> None:
        points = [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]
        path = htmx_charts._step_path(points)
        self.assertIn("M 10.00,20.00", path)
        self.assertIn("L 30.00,20.00", path)
        self.assertIn("L 30.00,40.00", path)
        self.assertIn("L 50.00,40.00", path)
        self.assertIn("L 50.00,60.00", path)

    def test_empty_geometry_helpers_return_empty_paths(self) -> None:
        self.assertEqual(htmx_charts._line_path([]), "")
        self.assertEqual(htmx_charts._area_path([], 0.0), "")
        self.assertEqual(htmx_charts._step_path([]), "")
        self.assertEqual(htmx_charts._step_area_path([], 0.0), "")

    def test_repair_event_marker_escapes_html_in_labels(self) -> None:
        events = [{"year": 2, "amount": 1000.0, "label": 'Roof & "<skylight>"'}]
        markup = htmx_charts._repair_event_markers(
            events,
            5,
            0.0,
            5000.0,
            htmx_charts.REPAIR_FUND_SVG_HEIGHT,
        )
        self.assertIn("&amp;", markup)
        self.assertIn("&lt;skylight&gt;", markup)
        self.assertNotIn('"<skylight>"', markup)

    def test_repair_fund_svg_emits_stepped_surprise_path(self) -> None:
        svg = htmx_charts._repair_fund_svg([0.0, 100.0, 200.0], [0.0, 50.0, 150.0], [], 3, 0.0, 500.0)
        self.assertIn('class="repair-surprise-series"', svg)
        self.assertIn('class="surprise-cost-area"', svg)
        self.assertRegex(svg, r'd="[^"]*L \d+\.\d+,\d+\.\d+ L \d+\.\d+,\d+\.\d+"')

    def test_endpoint_label_anchors_end_near_right_edge(self) -> None:
        height = htmx_charts.TEN_YEAR_SVG_HEIGHT
        left, _, width, _ = htmx_charts._plot_area(height)
        x = left + width - 1.0
        label_x, anchor = htmx_charts._endpoint_label_position(x, height)
        self.assertEqual(anchor, "end")
        self.assertLess(label_x, x)

    def test_hex_alpha_derives_gradient_from_chart_rental(self) -> None:
        rgba = htmx_charts._hex_alpha(htmx_charts.CHART_RENTAL, 0.12)
        self.assertEqual(rgba, "rgba(26, 122, 76, 0.12)")

    def test_line_series_from_graph_skips_non_numeric_values(self) -> None:
        graph = {
            "series": [
                {"id": "a", "label": "A", "values": [1, None, 3]},
                {"id": "b", "label": "B", "values": []},
            ]
        }
        series = htmx_charts._line_series_from_graph(graph)
        self.assertEqual(len(series), 1)
        self.assertEqual(series[0]["values"], [1, 3])

    def test_ten_year_chart_empty_trace_shows_unavailable_message(self) -> None:
        from dataclasses import replace

        from capex3.presentation.htmx_state import _build_state

        state = replace(
            _build_state({}, "calculate"),
            active_evidence_layer="tenYear",
            result={},
        )
        body = htmx_charts._ten_year_chart(state)
        self.assertIn("Evidence trace unavailable.", body)

    def test_repair_fund_chart_empty_trace_shows_unavailable_message(self) -> None:
        from dataclasses import replace

        from capex3.presentation.htmx_state import _build_state

        state = replace(
            _build_state({}, "calculate"),
            active_evidence_layer="repairFund",
            result={},
        )
        body = htmx_charts._repair_fund_chart(state)
        self.assertIn("Repair reserve path trace unavailable.", body)

    def test_ten_year_endpoints_escape_class_names(self) -> None:
        series = [
            {
                "className": 'cash-flow"><script>',
                "label": "Cash",
                "values": [100.0, 200.0],
            }
        ]
        markup = htmx_charts._ten_year_endpoints(series, 2, 0.0, 300.0, htmx_charts.TEN_YEAR_SVG_HEIGHT)
        self.assertNotIn("<script>", markup)
        self.assertIn("&lt;script&gt;", markup)


def _field_grid_markup(body: str) -> str:
    return body.split('<div class="field-grid" id="field-grid">', 1)[1].split(
        "</div>",
        1,
    )[0]


def _metric_strip_markup(body: str) -> str:
    return body.split('data-source-role="metric-strip">', 1)[1].split(
        "</div>",
        1,
    )[0]


if __name__ == "__main__":
    unittest.main()
