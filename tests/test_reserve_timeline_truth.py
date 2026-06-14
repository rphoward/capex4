"""App-only regression for reserve timeline truth fields on pro forma rows."""

import math
import unittest

from capex3.core.repair_reserve_path_trace import compute_repair_reserve_path_trace
from capex3.presentation.http_contracts import calculate_payload


class ReserveTimelineTruthTest(unittest.TestCase):
    def test_defaults_both_chart_lines_start_at_zero(self) -> None:
        payload = calculate_payload({})
        rows = payload["result"]["proForma"]
        series = payload["result"]["traces"]["tenYear"]["graph"]["series"]
        by_id = {item["id"]: item for item in series}

        self.assertEqual(rows[0]["sellNowWealth"], 0.0)
        self.assertEqual(rows[0]["earningsSoFar"], 0.0)
        self.assertEqual(by_id["sellNow"]["values"][0], 0.0)
        self.assertEqual(by_id["earnings"]["values"][0], 0.0)

    def test_year10_sell_now_wealth_can_differ_from_l17_with_repairs(self) -> None:
        payload = calculate_payload({"effectiveAgeYears": 9})
        year10 = payload["result"]["proForma"][10]

        self.assertNotEqual(
            year10["sellNowWealth"],
            year10["realEstateLiquidationWealth"],
        )
        self.assertAlmostEqual(
            year10["sellNowWealth"],
            year10["netProceeds"] + year10["reserveEndingBalance"],
        )

    def test_earnings_accumulator_includes_cash_flow_and_freed_when_capped(self) -> None:
        trace = compute_repair_reserve_path_trace(
            {"reserveAccountApy": 0.0, "capexInflationRate": 0.0},
            {
                "totalMonthlyCapexReserve": 100.0,
                "targetCapExReserve": 1_000.0,
            },
            [],
            annual_cash_flow=12_000.0,
        )
        rows = trace["years"]

        self.assertEqual(rows[0]["earningsSoFar"], 0.0)
        self.assertAlmostEqual(rows[1]["earningsSoFar"], 12_000.0 + rows[1]["freedReserve"])
        capped_year = next(row for row in rows if row["freedReserve"] > 0)
        self.assertGreater(capped_year["freedReserve"], 0)
        self.assertGreater(capped_year["earningsSoFar"], 12_000.0)

    def test_repair_depletion_restarts_set_aside_and_pauses_freed_overflow(self) -> None:
        trace = compute_repair_reserve_path_trace(
            {"reserveAccountApy": 0.0, "capexInflationRate": 0.0},
            {
                "totalMonthlyCapexReserve": 100.0,
                "targetCapExReserve": 2_400.0,
            },
            [
                {
                    "component": "Roofing: Arch. Asphalt (per sq)",
                    "remainingLife": 2.0,
                    "futureCost": 2_000.0,
                }
            ],
            annual_cash_flow=6_000.0,
        )
        rows = trace["years"]
        earnings = [row["earningsSoFar"] for row in rows]
        freed = [row["freedReserve"] for row in rows]

        self.assertTrue(any(value > 0 for value in freed))
        self.assertTrue(any(value == 0 for value in freed))
        year_over_year = [
            earnings[index] - earnings[index - 1]
            for index in range(1, len(earnings))
        ]
        self.assertTrue(any(delta < 6_600 for delta in year_over_year))

    def test_pro_forma_rows_carry_reserve_timeline_fields(self) -> None:
        payload = calculate_payload({})
        for row in payload["result"]["proForma"]:
            self.assertIn("reserveEndingBalance", row)
            self.assertIn("sellNowWealth", row)
            self.assertIn("earningsSoFar", row)
            self.assertIn("freedReserve", row)
            self.assertTrue(math.isfinite(float(row["sellNowWealth"])))
            self.assertTrue(math.isfinite(float(row["earningsSoFar"])))

    def test_pro_forma_timeline_fields_match_reserve_trace(self) -> None:
        payload = calculate_payload({})
        pro_forma = payload["result"]["proForma"]
        trace_years = payload["result"]["repairReservePathTrace"]["years"]

        self.assertEqual(len(pro_forma), len(trace_years))
        for pro_forma_row, trace_row in zip(pro_forma, trace_years):
            self.assertEqual(
                pro_forma_row["reserveEndingBalance"],
                trace_row["reserveEndingBalance"],
            )
            self.assertEqual(pro_forma_row["freedReserve"], trace_row["freedReserve"])
            if pro_forma_row["year"] == 0:
                self.assertEqual(pro_forma_row["earningsSoFar"], 0.0)
            else:
                self.assertEqual(
                    pro_forma_row["earningsSoFar"],
                    trace_row["earningsSoFar"],
                )
            if pro_forma_row["year"] == 0:
                self.assertEqual(pro_forma_row["sellNowWealth"], 0.0)
            else:
                self.assertAlmostEqual(
                    pro_forma_row["sellNowWealth"],
                    pro_forma_row["netProceeds"] + pro_forma_row["reserveEndingBalance"],
                )

    def test_negative_cash_flow_reduces_earnings_so_far(self) -> None:
        payload = calculate_payload({})
        earnings = [row["earningsSoFar"] for row in payload["result"]["proForma"]]
        annual_cash_flow = payload["result"]["dashboard"]["trueMonthlyCashFlow"] * 12

        if annual_cash_flow < 0:
            self.assertLess(earnings[1], earnings[0])
        else:
            self.assertGreaterEqual(earnings[1], earnings[0])

    def test_repair_year_pauses_freed_overflow_until_reserve_refills(self) -> None:
        trace = compute_repair_reserve_path_trace(
            {"reserveAccountApy": 0.0, "capexInflationRate": 0.0},
            {
                "totalMonthlyCapexReserve": 100.0,
                "targetCapExReserve": 2_400.0,
            },
            [
                {
                    "component": "Roofing: Arch. Asphalt (per sq)",
                    "remainingLife": 2.0,
                    "futureCost": 2_000.0,
                }
            ],
            annual_cash_flow=6_000.0,
        )
        rows = trace["years"]
        repair_index = next(
            index for index, row in enumerate(rows) if row["repairCost"] > 0
        )
        following = rows[repair_index + 1]

        self.assertEqual(following["freedReserve"], 0.0)
        self.assertLess(
            following["earningsSoFar"] - rows[repair_index]["earningsSoFar"],
            6_000.0 + 1_200.0,
        )


if __name__ == "__main__":
    unittest.main()
