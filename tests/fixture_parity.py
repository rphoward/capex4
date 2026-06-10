import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from capex3.core.calculate_rental_capex import (
    RentalCapexCalculationRequest,
    calculate_rental_capex,
)
from capex3.core.solve_rental_capex import (
    RentalCapexSolverRequest,
    solve_rental_capex,
)
from capex3.infrastructure.workbook_assumptions import (
    load_workbook_model_spec_record,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFICATION_CASES = REPO_ROOT / "tests" / "fixtures" / "model-verification-cases.json"


def run_fixture_parity(cases_path: Path | None = None) -> dict[str, object]:
    cases_file = cases_path if cases_path is not None else VERIFICATION_CASES
    verification = _load_json(cases_file)
    model_spec = load_workbook_model_spec_record()
    failures: list[dict[str, object]] = []
    calculation_case_count = 0
    solver_case_count = 0

    for fixture_case in verification["cases"]:
        if fixture_case["id"].startswith("solver."):
            solver_case_count += 1
            failures.extend(_compare_solver_case(fixture_case, verification, model_spec))
        else:
            calculation_case_count += 1
            failures.extend(
                _compare_calculation_case(fixture_case, verification, model_spec)
            )

    return {
        "ok": len(failures) == 0,
        "sourceWorkbook": model_spec["sourceWorkbook"],
        "calculationCaseCount": calculation_case_count,
        "solverCaseCount": solver_case_count,
        "totalCaseCount": calculation_case_count + solver_case_count,
        "failures": failures,
        "runtimeSource": "src/capex3/infrastructure/workbook_assumptions/data",
        "fixtureSource": _fixture_source_label(cases_file),
    }


def main() -> int:
    report = run_fixture_parity()
    print(json.dumps(report, separators=(",", ":")))
    return 0 if report["ok"] else 1


def _compare_calculation_case(
    fixture_case: Mapping[str, object],
    verification: Mapping[str, object],
    model_spec: Mapping[str, object],
) -> list[dict[str, object]]:
    result = calculate_rental_capex(
        RentalCapexCalculationRequest.from_contract_dict(
            fixture_case.get("inputs") or {}
        ),
        model_spec=model_spec,
    ).to_contract_dict()
    failures = []

    for check in _compare_expected_outputs(
        result,
        fixture_case["expected"],
        verification["numericTolerance"],
    ):
        if not check["ok"]:
            failures.append({"caseId": fixture_case["id"], **check})

    return failures


def _compare_solver_case(
    fixture_case: Mapping[str, object],
    verification: Mapping[str, object],
    model_spec: Mapping[str, object],
) -> list[dict[str, object]]:
    result = solve_rental_capex(
        RentalCapexSolverRequest.from_contract_dict(
            {
                "baseInput": fixture_case.get("baseInputs") or {},
                "variable": fixture_case["variable"],
                "metric": fixture_case["targetMetric"],
                "targetValue": fixture_case["targetValue"],
                "lowerBound": fixture_case.get("lowerBound"),
                "upperBound": fixture_case.get("upperBound"),
                "tolerance": 0.000001,
            }
        ),
        model_spec=model_spec,
    ).to_contract_dict()
    failures = []

    if not result["ok"]:
        return [
            {
                "caseId": fixture_case["id"],
                "field": "solver.ok",
                "actual": False,
                "expected": True,
                "message": result.get("message"),
            }
        ]

    solved_value_delta = result["solvedValue"] - fixture_case["solvedValue"]
    if abs(solved_value_delta) > 0.01:
        failures.append(
            {
                "caseId": fixture_case["id"],
                "field": "solvedValue",
                "actual": result["solvedValue"],
                "expected": fixture_case["solvedValue"],
                "delta": solved_value_delta,
                "tolerance": 0.01,
            }
        )

    solved_metric_delta = result["solvedMetricValue"] - fixture_case["targetValue"]
    metric_tolerance = verification["numericTolerance"]["ratioAbsolute"]
    if abs(solved_metric_delta) > metric_tolerance:
        failures.append(
            {
                "caseId": fixture_case["id"],
                "field": "solvedMetricValue",
                "actual": result["solvedMetricValue"],
                "expected": fixture_case["targetValue"],
                "delta": solved_metric_delta,
                "tolerance": metric_tolerance,
            }
        )

    if fixture_case.get("expectedMetricPath") and (
        result["metricPath"] != fixture_case["expectedMetricPath"]
    ):
        failures.append(
            {
                "caseId": fixture_case["id"],
                "field": "metricPath",
                "actual": result["metricPath"],
                "expected": fixture_case["expectedMetricPath"],
            }
        )

    return failures


def _compare_expected_outputs(
    result: Mapping[str, object],
    expected: Mapping[str, object],
    numeric_tolerance: Mapping[str, float],
) -> list[dict[str, object]]:
    checks = []

    for key, expected_value in expected.items():
        if key == "proFormaRows":
            checks.extend(
                _compare_pro_forma_rows(
                    result["proForma"],
                    expected_value,
                    numeric_tolerance,
                )
            )
            continue

        if key == "roofRow":
            checks.extend(
                _compare_sinking_fund_rows(
                    result["sinkingFundRows"],
                    [expected_value],
                    numeric_tolerance,
                )
            )
            continue

        checks.append(
            _compare_value(
                _dashboard_value(result, key),
                expected_value,
                key,
                key,
                numeric_tolerance,
            )
        )

    return checks


def _compare_pro_forma_rows(
    actual_rows: Sequence[Mapping[str, object]],
    expected_rows: Sequence[Mapping[str, object]],
    numeric_tolerance: Mapping[str, float],
) -> list[dict[str, object]]:
    checks = []

    for expected_row in expected_rows:
        actual_row = _find_by_key(actual_rows, "year", expected_row["year"])

        if not actual_row:
            checks.append(
                {
                    "ok": False,
                    "field": f"proForma.year{expected_row['year']}",
                    "expected": "present",
                    "actual": "missing",
                }
            )
            continue

        for key, expected_value in expected_row.items():
            checks.append(
                _compare_value(
                    actual_row.get(key),
                    expected_value,
                    f"proForma.year{expected_row['year']}.{key}",
                    key,
                    numeric_tolerance,
                )
            )

    return checks


def _compare_sinking_fund_rows(
    actual_rows: Sequence[Mapping[str, object]],
    expected_rows: Sequence[Mapping[str, object]],
    numeric_tolerance: Mapping[str, float],
) -> list[dict[str, object]]:
    checks = []

    for expected_row in expected_rows:
        actual_row = _find_by_key(actual_rows, "component", expected_row["component"])

        if not actual_row:
            checks.append(
                {
                    "ok": False,
                    "field": f"sinkingFundRows.{expected_row['component']}",
                    "expected": "present",
                    "actual": "missing",
                }
            )
            continue

        for key, expected_value in expected_row.items():
            checks.append(
                _compare_value(
                    actual_row.get(key),
                    expected_value,
                    f"sinkingFundRows.{expected_row['component']}.{key}",
                    key,
                    numeric_tolerance,
                )
            )

    return checks


def _compare_value(
    actual: object,
    expected: object,
    field: str,
    tolerance_key: str,
    numeric_tolerance: Mapping[str, float],
) -> dict[str, object]:
    if isinstance(expected, (int, float)) and math.isfinite(expected):
        tolerance = _tolerance_for(tolerance_key, numeric_tolerance)
        delta = actual - expected
        return {
            "ok": abs(delta) <= tolerance,
            "field": field,
            "actual": actual,
            "expected": expected,
            "delta": delta,
            "tolerance": tolerance,
        }

    return {
        "ok": actual == expected,
        "field": field,
        "actual": actual,
        "expected": expected,
    }


def _dashboard_value(result: Mapping[str, object], key: str) -> object:
    if key == "activeOverridesCount":
        return result["audit"]["activeOverridesCount"]

    return result["dashboard"].get(key)


def _tolerance_for(key: str, numeric_tolerance: Mapping[str, float]) -> float:
    lower_key = key.lower()
    if (
        "rate" in lower_key
        or "ratio" in lower_key
        or "roi" in lower_key
        or "return" in lower_key
        or "caprate" in lower_key
    ):
        return numeric_tolerance["ratioAbsolute"]

    return numeric_tolerance["currencyAbsolute"]


def _find_by_key(
    rows: Sequence[Mapping[str, object]],
    key: str,
    value: object,
) -> Mapping[str, object] | None:
    for row in rows:
        if row.get(key) == value:
            return row

    return None


def _fixture_source_label(cases_path: Path) -> str:
    try:
        return cases_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return cases_path.as_posix()


def _load_json(file_path: Path) -> Mapping[str, object]:
    with file_path.open("r", encoding="utf8") as source_file:
        return json.load(source_file)


if __name__ == "__main__":
    raise SystemExit(main())
