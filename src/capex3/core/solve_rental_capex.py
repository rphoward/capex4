import math
from dataclasses import dataclass, field
from typing import Mapping

from capex3.core.calculate_rental_capex import (
    RentalCapexCalculationRequest,
    calculate_rental_capex,
)
from capex3.core.deal_inputs import (
    RentalCapexDealInputRequest,
    _assert_not_boolean_number,
    assert_model_spec,
    normalize_input,
)
from capex3.core.errors import (
    MAX_ITERATIONS_EXCEEDED,
    NO_BRACKET,
    NON_FINITE_RESULT,
    RentalCapexError,
    UNDEFINED_METRIC,
    VALIDATION_ERROR,
    json_safe_value,
)
from capex3.core.reserve_first_shortfall_solver import (
    ALREADY_CLEARED_REASON,
    YEAR_ONE_MAKE_READY_REASON,
    bisect_monthly_reserve_increase,
    emergency_gap_at_year,
    estimate_upper_bound_for_reserve_increase,
    find_first_emergency_gap_year,
    reserve_solver_decline_reason,
    round_reserve_increase,
)
from capex3.core.workbook_assumptions import model_spec_record


DEFAULT_BOUNDS = {
    "rent": (0, 12000),
    "purchasePriceWithDefaultDownPayment": (50000, 700000),
    "purchasePriceWithFixedDownPayment": (50000, 700000),
    "rehabBudget": (0, 300000),
    "downPayment": None,
}

RESERVE_FIRST_SHORTFALL_METRIC = "firstEmergencyGap"
RESERVE_INCREASE_VARIABLE = "monthlyReserveIncrease"

METRIC_PATHS = {
    "monthlyCashFlow": ("dashboard", "trueMonthlyCashFlow"),
    "cashOnCashReturn": ("dashboard", "cashOnCashReturn"),
    "year10Roi": ("dashboard", "year10Roi"),
    "year10AnnualizedRoi": ("dashboard", "year10AnnualizedRoi"),
    "debtServiceCoverageRatio": ("dashboard", "debtServiceCoverageRatio"),
    "yearOneTotalReturnOnEquity": (
        "dashboard",
        "yearOneTotalReturnOnEquity",
    ),
    "breakevenGrossRent": ("dashboard", "breakevenGrossRent"),
    "rentToValueRatio": ("dashboard", "rentToValueRatio"),
}

NUMERIC_SOLVER_FIELDS = frozenset(
    ("targetValue", "lowerBound", "upperBound", "tolerance")
)


@dataclass(frozen=True)
class RentalCapexSolverRequest:
    base_input: RentalCapexDealInputRequest = field(
        default_factory=RentalCapexDealInputRequest
    )
    variable: str | None = None
    metric: str | None = None
    target_value: float | int | None = None
    lower_bound: float | int | None = None
    upper_bound: float | int | None = None
    tolerance: float | int = 0.000001
    max_iterations: int = 100

    @classmethod
    def from_contract_dict(
        cls,
        request: Mapping[str, object] | None = None,
    ) -> "RentalCapexSolverRequest":
        if request is None:
            return cls()

        if not isinstance(request, Mapping):
            raise RentalCapexError(
                VALIDATION_ERROR,
                "Solver request must be an object.",
                {"request": request},
            )

        field_map = {
            "baseInput": "base_input",
            "variable": "variable",
            "metric": "metric",
            "targetValue": "target_value",
            "lowerBound": "lower_bound",
            "upperBound": "upper_bound",
            "tolerance": "tolerance",
            "maxIterations": "max_iterations",
        }
        unknown_fields = sorted(set(request) - set(field_map))
        if unknown_fields:
            raise RentalCapexError(
                VALIDATION_ERROR,
                "Solver request includes unknown fields.",
                {"fields": unknown_fields},
            )

        kwargs = {}
        for field_name, attribute_name in field_map.items():
            if field_name not in request:
                continue

            if field_name == "baseInput":
                kwargs[attribute_name] = RentalCapexDealInputRequest.from_contract_dict(
                    request.get(field_name)
                )
                continue

            value = request.get(field_name)
            if field_name in NUMERIC_SOLVER_FIELDS or field_name == "maxIterations":
                _assert_not_boolean_number(value, field_name)

            kwargs[attribute_name] = value

        return cls(**kwargs)

    def base_input_dict(self) -> dict[str, object]:
        return self.base_input.to_input_dict()


@dataclass(frozen=True)
class RentalCapexSolverResult:
    ok: bool
    fields: Mapping[str, object] = field(default_factory=dict)

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            **dict(self.fields),
        }


def solve_rental_capex(
    request: RentalCapexSolverRequest | None = None,
    *,
    model_spec: Mapping[str, object],
) -> RentalCapexSolverResult:
    request = _solver_request(request)
    resolved_model_spec = assert_model_spec(model_spec_record(model_spec))
    if request.metric == RESERVE_FIRST_SHORTFALL_METRIC:
        return solve_reserve_first_shortfall(request, model_spec=resolved_model_spec)
    base_input = request.base_input_dict()
    variable = request.variable
    metric = request.metric
    target_value = request.target_value
    tolerance = request.tolerance
    max_iterations = request.max_iterations

    try:
        baseline_input = normalize_input(base_input, resolved_model_spec)
    except RentalCapexError as error:
        return _solver_error(error.code, str(error), _caught_error_contract(error))

    default_bound_pair = _default_bounds(variable, baseline_input)

    if not default_bound_pair:
        return _solver_error(
            VALIDATION_ERROR,
            f"Unsupported solver variable: {variable}",
            {"variable": variable},
        )

    lower_bound = (
        default_bound_pair[0]
        if request.lower_bound is None
        else request.lower_bound
    )
    upper_bound = (
        default_bound_pair[1]
        if request.upper_bound is None
        else request.upper_bound
    )

    if (
        not _is_finite_number(target_value)
        or not _is_finite_number(lower_bound)
        or not _is_finite_number(upper_bound)
        or lower_bound >= upper_bound
    ):
        return _solver_error(
            VALIDATION_ERROR,
            "Solver target and bounds must be finite, with lowerBound < upperBound.",
            {
                "targetValue": target_value,
                "lowerBound": lower_bound,
                "upperBound": upper_bound,
            },
        )

    if (
        not _is_finite_number(tolerance)
        or tolerance <= 0
        or isinstance(max_iterations, bool)
        or not isinstance(max_iterations, int)
        or max_iterations < 1
    ):
        return _solver_error(
            VALIDATION_ERROR,
            "Solver tolerance must be positive and maxIterations must be a positive integer.",
            {"tolerance": tolerance, "maxIterations": max_iterations},
        )

    def evaluate(value: float) -> RentalCapexSolverResult:
        candidate_input = _input_with_variable(baseline_input, variable, value)
        if not candidate_input:
            return _solver_error(
                VALIDATION_ERROR,
                f"Unsupported solver variable: {variable}",
                {"variable": variable},
            )

        try:
            result = calculate_rental_capex(
                RentalCapexCalculationRequest.from_contract_dict(candidate_input),
                model_spec=resolved_model_spec,
            )
            metric_result = _metric_value(result.to_contract_dict(), metric)
            if not metric_result.ok:
                return metric_result

            metric_fields = metric_result.to_contract_dict()
            metric_value = metric_fields["value"]
            return RentalCapexSolverResult(
                ok=True,
                fields={
                    "input": candidate_input,
                    "result": result.to_contract_dict(),
                    "metricPath": metric_fields["metricPath"],
                    "metricValue": metric_value,
                    "residual": metric_value - target_value,
                },
            )
        except RentalCapexError as error:
            return _solver_error(error.code, str(error), _caught_error_contract(error))

    lower = evaluate(lower_bound)
    if not lower.ok:
        return lower

    upper = evaluate(upper_bound)
    if not upper.ok:
        return upper

    baseline = evaluate(_current_variable_value(baseline_input, variable))
    lower_fields = lower.to_contract_dict()
    upper_fields = upper.to_contract_dict()

    if abs(lower_fields["residual"]) <= tolerance:
        return _successful_solution(lower_bound, lower_fields, 0)

    if abs(upper_fields["residual"]) <= tolerance:
        return _successful_solution(upper_bound, upper_fields, 0)

    if _sign(lower_fields["residual"]) == _sign(upper_fields["residual"]):
        baseline_fields = baseline.to_contract_dict() if baseline.ok else {}
        return _solver_error(
            NO_BRACKET,
            "Solver bounds do not bracket the target.",
            {
                "lowerBound": lower_bound,
                "upperBound": upper_bound,
                "metricPath": lower_fields.get("metricPath")
                or upper_fields.get("metricPath"),
                "currentValue": _current_variable_value(baseline_input, variable),
                "currentMetricValue": baseline_fields.get("metricValue"),
                "lowerMetricValue": lower_fields["metricValue"],
                "upperMetricValue": upper_fields["metricValue"],
                "lowerResidual": lower_fields["residual"],
                "upperResidual": upper_fields["residual"],
            },
        )

    low_value = lower_bound
    high_value = upper_bound
    low = lower
    high = upper

    for iteration in range(1, max_iterations + 1):
        midpoint = (low_value + high_value) / 2
        mid = evaluate(midpoint)
        if not mid.ok:
            return mid

        mid_fields = mid.to_contract_dict()

        if abs(mid_fields["residual"]) <= tolerance:
            return _successful_solution(midpoint, mid_fields, iteration)

        low_fields = low.to_contract_dict()

        if _sign(mid_fields["residual"]) == _sign(low_fields["residual"]):
            low_value = midpoint
            low = mid
        else:
            high_value = midpoint
            high = mid

    midpoint = (low_value + high_value) / 2
    mid = evaluate(midpoint)
    mid_fields = mid.to_contract_dict() if mid.ok else {}
    low_fields = low.to_contract_dict()
    high_fields = high.to_contract_dict()

    return _solver_error(
        MAX_ITERATIONS_EXCEEDED,
        "Solver reached the maximum iteration count before meeting tolerance.",
        {
            "solvedValue": midpoint,
            "solvedMetricValue": mid_fields.get("metricValue"),
            "metricPath": mid_fields.get("metricPath")
            or low_fields.get("metricPath")
            or high_fields.get("metricPath"),
            "residual": mid_fields.get("residual"),
            "lowResidual": low_fields["residual"],
            "highResidual": high_fields["residual"],
        },
    )


def solve_reserve_first_shortfall(
    request: RentalCapexSolverRequest | None = None,
    *,
    model_spec: Mapping[str, object],
) -> RentalCapexSolverResult:
    """Bisect monthlyReserveIncrease for first y>=2 emergency gap."""
    request = _solver_request(request)
    resolved_model_spec = assert_model_spec(model_spec_record(model_spec))
    tolerance = request.tolerance if request.tolerance is not None else 0.01
    max_iterations = request.max_iterations

    try:
        baseline_input = normalize_input(request.base_input_dict(), resolved_model_spec)
    except RentalCapexError as error:
        return _solver_error(error.code, str(error), _caught_error_contract(error))

    current_increase = float(baseline_input.get("monthlyReserveIncrease") or 0.0)

    try:
        baseline_result = calculate_rental_capex(
            RentalCapexCalculationRequest.from_contract_dict(baseline_input),
            model_spec=resolved_model_spec,
        )
    except RentalCapexError as error:
        return _solver_error(error.code, str(error), _caught_error_contract(error))

    baseline_ledger = baseline_result.emergency_debt_ledger
    decline_reason = reserve_solver_decline_reason(baseline_ledger)
    if decline_reason is not None:
        reason_code = (
            "yearOneMakeReady"
            if decline_reason == YEAR_ONE_MAKE_READY_REASON
            else "noEmergencyGap"
        )
        return _solver_error(
            VALIDATION_ERROR,
            decline_reason,
            {"reason": reason_code},
        )

    first_gap_year = find_first_emergency_gap_year(baseline_ledger)

    baseline_gap = emergency_gap_at_year(baseline_ledger, first_gap_year)
    lower_bound = (
        current_increase
        if request.lower_bound is None
        else float(request.lower_bound)
    )
    upper_bound = (
        estimate_upper_bound_for_reserve_increase(
            first_shortfall_year=first_gap_year,
            gap_amount=baseline_gap,
            current_monthly_increase=lower_bound,
        )
        if request.upper_bound is None
        else float(request.upper_bound)
    )

    def evaluate_gap(monthly_increase: float) -> float:
        candidate_input = {
            **baseline_input,
            "monthlyReserveIncrease": monthly_increase,
        }
        result = calculate_rental_capex(
            RentalCapexCalculationRequest.from_contract_dict(candidate_input),
            model_spec=resolved_model_spec,
        )
        return emergency_gap_at_year(result.emergency_debt_ledger, first_gap_year)

    try:
        bisection = bisect_monthly_reserve_increase(
            evaluate_gap=evaluate_gap,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            tolerance=tolerance,
            max_iterations=max_iterations,
        )
    except RentalCapexError as error:
        return _solver_error(error.code, str(error), _caught_error_contract(error))

    if not bisection.get("ok"):
        return _solver_error(
            str(bisection.get("code") or NO_BRACKET),
            str(bisection.get("message") or "Reserve solver failed."),
            dict(bisection),
        )

    solved_value = round_reserve_increase(float(bisection["solvedValue"]))
    candidate_input = {**baseline_input, "monthlyReserveIncrease": solved_value}
    solved_result = calculate_rental_capex(
        RentalCapexCalculationRequest.from_contract_dict(candidate_input),
        model_spec=resolved_model_spec,
    )
    solved_gap = emergency_gap_at_year(
        solved_result.emergency_debt_ledger,
        first_gap_year,
    )

    fields: dict[str, object] = {
        "solvedValue": solved_value,
        "solvedMetricValue": solved_gap,
        "metricPath": f"emergencyDebtLedger.years[{first_gap_year}].emergencyGap",
        "residual": solved_gap,
        "iterations": bisection.get("iterations", 0),
        "input": candidate_input,
        "result": solved_result.to_contract_dict(),
        "firstEmergencyGapYear": first_gap_year,
        "baselineEmergencyGap": baseline_gap,
        "solverKind": "reserveFirstShortfall",
    }
    if bisection.get("alreadyCleared"):
        fields["reason"] = ALREADY_CLEARED_REASON

    return RentalCapexSolverResult(ok=True, fields=fields)


def metric_path_expression(metric: str) -> str | None:
    path = METRIC_PATHS.get(metric)
    return ".".join(path) if path else None


def round_to_workbook_precision(value: float) -> float:
    if value == 0:
        return 0

    rounded = float(f"{value:.6f}")
    return 0 if rounded == 0 else rounded


def _metric_value(
    result: Mapping[str, object],
    metric: str,
) -> RentalCapexSolverResult:
    path = METRIC_PATHS.get(metric)
    metric_path = metric_path_expression(metric)
    if not path:
        return _solver_error(
            UNDEFINED_METRIC,
            f"Unsupported solver metric: {metric}",
        )

    value: object = result
    for key in path:
        value = value.get(key) if isinstance(value, Mapping) else None

    if not _is_finite_number(value):
        return _solver_error(
            NON_FINITE_RESULT,
            f"Solver metric produced a non-finite result: {metric}",
            {"metricPath": metric_path, "value": value},
        )

    return RentalCapexSolverResult(
        ok=True,
        fields={"metricPath": metric_path, "value": round_to_workbook_precision(value)},
    )


def _input_with_variable(
    base_input: Mapping[str, object],
    variable: str,
    value: float,
) -> dict[str, object] | None:
    if variable == "rent":
        return {**base_input, "actualGrossMonthlyRent": value}

    if variable == "purchasePriceWithDefaultDownPayment":
        return {**base_input, "purchasePrice": value, "downPayment": None}

    if variable == "purchasePriceWithFixedDownPayment":
        return {**base_input, "purchasePrice": value}

    if variable == "rehabBudget":
        return {**base_input, "immediateRehabMakeReady": value}

    if variable == "downPayment":
        return {**base_input, "downPayment": value}

    if variable == RESERVE_INCREASE_VARIABLE:
        return {**base_input, "monthlyReserveIncrease": value}

    return None


def _default_bounds(
    variable: str,
    base_input: Mapping[str, object],
) -> tuple[float, float] | None:
    if variable == "downPayment":
        return (0, base_input["purchasePrice"])

    if variable == RESERVE_INCREASE_VARIABLE:
        return (float(base_input.get("monthlyReserveIncrease") or 0.0), 10_000.0)

    if variable == "purchasePriceWithFixedDownPayment":
        lower_bound, upper_bound = DEFAULT_BOUNDS[variable]
        return (max(lower_bound, base_input["downPayment"]), upper_bound)

    return DEFAULT_BOUNDS.get(variable)


def _current_variable_value(input_data: Mapping[str, object], variable: str) -> float | None:
    if variable == "rent":
        return input_data["actualGrossMonthlyRent"]

    if variable in (
        "purchasePriceWithDefaultDownPayment",
        "purchasePriceWithFixedDownPayment",
    ):
        return input_data["purchasePrice"]

    if variable == "rehabBudget":
        return input_data["immediateRehabMakeReady"]

    if variable == "downPayment":
        return input_data["downPayment"]

    if variable == RESERVE_INCREASE_VARIABLE:
        return float(input_data.get("monthlyReserveIncrease") or 0.0)

    return None


def _successful_solution(
    solved_value: float,
    fields: Mapping[str, object],
    iterations: int,
) -> RentalCapexSolverResult:
    return RentalCapexSolverResult(
        ok=True,
        fields={
            "solvedValue": solved_value,
            "solvedMetricValue": fields["metricValue"],
            "metricPath": fields["metricPath"],
            "residual": fields["residual"],
            "iterations": iterations,
            "input": fields["input"],
            "result": fields["result"],
        },
    )


def _solver_error(
    code: str,
    message: str,
    details: Mapping[str, object] | None = None,
) -> RentalCapexSolverResult:
    return RentalCapexSolverResult(
        ok=False,
        fields={
            "code": code,
            "message": message,
            **dict(details or {}),
        },
    )


def _caught_error_contract(error: RentalCapexError) -> dict[str, object]:
    return {
        "error": {
            "code": error.code,
            "message": str(error),
            "details": json_safe_value(error.details),
        },
    }



def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )



def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _solver_request(
    request: RentalCapexSolverRequest | None,
) -> RentalCapexSolverRequest:
    if request is None:
        return RentalCapexSolverRequest()

    if isinstance(request, RentalCapexSolverRequest):
        return request

    raise TypeError("solve_rental_capex request must be RentalCapexSolverRequest.")
