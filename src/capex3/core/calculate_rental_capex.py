import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from capex3.core.deal_inputs import RentalCapexDealInputRequest, is_blank, normalize_input
from capex3.core.emergency_debt_ledger import (
    evaluate_deal_survival,
    evaluate_emergency_debt_ledger,
    evaluate_shock_adjusted_cash_flow,
)
from capex3.core.errors import LOOKUP_ERROR, RentalCapexError, VALIDATION_ERROR
from capex3.core.financial import cumulative_principal, pmt
from capex3.core.repair_reserve_path_trace import compute_repair_reserve_path_trace
from capex3.core.reserve_first_shortfall_solver import (
    find_first_emergency_gap_year,
    find_first_raw_shortfall_year,
)
from capex3.core.workbook_assumptions import model_spec_record


@dataclass(frozen=True)
class RentalCapexCalculationRequest:
    deal_input: RentalCapexDealInputRequest = field(
        default_factory=RentalCapexDealInputRequest
    )

    @classmethod
    def from_contract_dict(
        cls,
        input_data: Mapping[str, object] | None = None,
    ) -> "RentalCapexCalculationRequest":
        return cls(deal_input=RentalCapexDealInputRequest.from_contract_dict(input_data))

    def to_input_dict(self) -> dict[str, object]:
        return self.deal_input.to_input_dict()


@dataclass(frozen=True)
class RentalCapexCalculationResult:
    input: Mapping[str, object]
    dashboard: Mapping[str, object]
    sinking_fund_rows: Sequence[Mapping[str, object]]
    repair_reserve_path_trace: Mapping[str, object]
    pro_forma: Sequence[Mapping[str, object]]
    audit: Mapping[str, object]
    emergency_debt_ledger: Mapping[str, object]
    shock_survival: Mapping[str, object]

    def to_contract_dict(self) -> dict[str, object]:
        ledger = dict(self.emergency_debt_ledger)
        return {
            "input": dict(self.input),
            "dashboard": dict(self.dashboard),
            "sinkingFundRows": [dict(row) for row in self.sinking_fund_rows],
            "repairReservePathTrace": dict(self.repair_reserve_path_trace),
            "proForma": [dict(row) for row in self.pro_forma],
            "audit": dict(self.audit),
            "emergencyDebtLedger": ledger,
            "overlapDetected": ledger["overlapDetected"],
            "shockAdjustedCashFlow": self.shock_survival["shockAdjustedCashFlow"],
            "dealSurvives": self.shock_survival["dealSurvives"],
            "shockSurvival": dict(self.shock_survival),
            "firstEmergencyGapYear": find_first_emergency_gap_year(ledger),
            "firstRawShortfallYear": find_first_raw_shortfall_year(ledger),
        }


def calculate_rental_capex(
    request: RentalCapexCalculationRequest | None = None,
    *,
    model_spec: Mapping[str, object],
) -> RentalCapexCalculationResult:
    request = _calculation_request(request)
    resolved_model_spec = model_spec_record(model_spec)
    normalized = normalize_input(request.to_input_dict(), resolved_model_spec)
    lookups = _lookup_assumptions(normalized, resolved_model_spec)
    sinking_fund = _compute_sinking_fund(normalized, resolved_model_spec, lookups)
    loan_amount = normalized["purchasePrice"] - normalized["downPayment"]

    if loan_amount < 0:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "loanAmount must not be negative.",
            {"loanAmount": loan_amount},
        )

    effective_gross_income_monthly = (
        normalized["actualGrossMonthlyRent"] * (1 - lookups["vacancyRate"])
    )
    total_monthly_fixed_expenses = (
        normalized["annualPropertyTaxes"] / 12
        + normalized["annualInsurancePremium"] / 12
        + normalized["monthlyUtilitiesLandlordPaid"]
        + normalized["propertyManagementFeePercent"]
        * effective_gross_income_monthly
        + normalized["cleaningMaintenanceAnnual"] / 12
        + normalized["legalProfessionalAnnual"] / 12
        + normalized["advertisingLeasingAnnual"] / 12
        + normalized["hoaFeesMonthly"]
    )
    net_operating_income_monthly = (
        effective_gross_income_monthly
        - total_monthly_fixed_expenses
        - sinking_fund["totalMonthlyCapexReserve"]
    )
    cap_rate = (
        math.nan
        if normalized["purchasePrice"] == 0
        else (net_operating_income_monthly * 12) / normalized["purchasePrice"]
    )
    monthly_mortgage_pi = pmt(
        normalized["loanInterestRate"] / 12,
        normalized["loanTermYears"] * 12,
        -loan_amount,
        0,
        0,
    )
    true_monthly_cash_flow = net_operating_income_monthly - monthly_mortgage_pi
    closing_costs = (
        normalized["actualClosingCostsOverride"]
        if normalized["actualClosingCostsOverride"] > 0
        else normalized["purchasePrice"] * normalized["estimatedClosingCostsPercent"]
    )
    total_initial_investment = (
        normalized["downPayment"]
        + closing_costs
        + normalized["immediateRehabMakeReady"]
    )
    cash_on_cash_return = (
        math.nan
        if total_initial_investment == 0
        else (true_monthly_cash_flow * 12) / total_initial_investment
    )
    target_capex_reserve = sinking_fund["totalMonthlyCapexReserve"] * 12 * 2.5
    debt_service_coverage_ratio = (
        math.nan
        if monthly_mortgage_pi == 0
        else net_operating_income_monthly / monthly_mortgage_pi
    )
    first_year_principal = cumulative_principal(
        normalized["loanInterestRate"] / 12,
        normalized["loanTermYears"] * 12,
        loan_amount,
        1,
        12,
        0,
    )
    year_one_total_return_on_equity = (
        math.nan
        if total_initial_investment == 0
        else (true_monthly_cash_flow * 12 - first_year_principal)
        / total_initial_investment
    )
    gross_rent_breakeven_denominator = 1 - lookups["vacancyRate"]
    breakeven_gross_rent = (
        math.nan
        if gross_rent_breakeven_denominator == 0
        else (
            monthly_mortgage_pi
            + total_monthly_fixed_expenses
            + sinking_fund["totalMonthlyCapexReserve"]
        )
        / gross_rent_breakeven_denominator
    )
    rent_to_value_ratio = (
        math.nan
        if normalized["purchasePrice"] == 0
        else normalized["actualGrossMonthlyRent"] / normalized["purchasePrice"]
    )

    dashboard = {
        "propertyAddress": normalized["propertyAddress"],
        "subregion": normalized["subregion"],
        "propertyProfile": normalized["propertyProfile"],
        "purchasePrice": normalized["purchasePrice"],
        "downPayment": normalized["downPayment"],
        "loanAmount": loan_amount,
        "actualGrossMonthlyRent": normalized["actualGrossMonthlyRent"],
        "marketRent": lookups["marketRent"],
        "vacancyRate": lookups["vacancyRate"],
        "effectiveGrossIncomeMonthly": effective_gross_income_monthly,
        "targetCapExReserve": target_capex_reserve,
        "totalMonthlyFixedExpenses": total_monthly_fixed_expenses,
        "totalMonthlyCapexReserve": sinking_fund["totalMonthlyCapexReserve"],
        "netOperatingIncomeMonthly": net_operating_income_monthly,
        "capRate": cap_rate,
        "monthlyMortgagePI": monthly_mortgage_pi,
        "trueMonthlyCashFlow": true_monthly_cash_flow,
        "closingCosts": closing_costs,
        "totalInitialInvestment": total_initial_investment,
        "cashOnCashReturn": cash_on_cash_return,
        "debtServiceCoverageRatio": debt_service_coverage_ratio,
        "yearOneTotalReturnOnEquity": year_one_total_return_on_equity,
        "breakevenGrossRent": breakeven_gross_rent,
        "rentToValueRatio": rent_to_value_ratio,
    }

    pro_forma = _compute_pro_forma(normalized, dashboard)
    year10 = pro_forma[10]
    year10_roi = (
        math.nan
        if total_initial_investment == 0
        else (
            year10["netProceeds"]
            + year10["accumulatedTrueCashFlow"]
            - total_initial_investment
        )
        / total_initial_investment
    )
    year10_growth_base = 1 + year10_roi
    year10_annualized_roi = (
        math.nan
        if year10_growth_base < 0
        else year10_growth_base ** (1 / 10) - 1
    )

    dashboard["futurePropertyValueYear10"] = year10["futurePropertyValue"]
    dashboard["remainingLoanBalanceYear10"] = year10["remainingLoanBalance"]
    dashboard["costOfSaleYear10"] = year10["costOfSale"]
    dashboard["netProceedsYear10"] = year10["netProceeds"]
    dashboard["year10Roi"] = year10_roi
    dashboard["year10AnnualizedRoi"] = year10_annualized_roi

    repair_reserve_path_trace = compute_repair_reserve_path_trace(
        normalized,
        dashboard,
        sinking_fund["sinkingFundRows"],
    )
    emergency_debt_ledger = evaluate_emergency_debt_ledger(
        repair_reserve_path_trace["years"],
        emergency_loan_apr=normalized["emergencyLoanApr"],
        emergency_loan_term_years=normalized["emergencyLoanTermYears"],
        immediate_rehab_make_ready=normalized["immediateRehabMakeReady"],
    )
    true_monthly_cash_flow = float(dashboard["trueMonthlyCashFlow"])
    shock_evaluation = evaluate_shock_adjusted_cash_flow(
        true_monthly_cash_flow,
        emergency_debt_ledger,
    )
    minimum_true_monthly_cash_flow = float(
        normalized["minimumTrueMonthlyCashFlow"]
    )
    shock_survival = {
        **shock_evaluation,
        "minimumTrueMonthlyCashFlow": minimum_true_monthly_cash_flow,
        "dealSurvives": evaluate_deal_survival(
            float(shock_evaluation["shockAdjustedCashFlow"]),
            true_monthly_cash_flow,
            minimum_true_monthly_cash_flow,
        ),
    }

    return RentalCapexCalculationResult(
        input=normalized,
        dashboard=dashboard,
        sinking_fund_rows=sinking_fund["sinkingFundRows"],
        repair_reserve_path_trace=repair_reserve_path_trace,
        pro_forma=pro_forma,
        audit={
            "activeOverridesCount": sinking_fund["activeOverridesCount"],
            "totalMonthlyCapexReserve": sinking_fund["totalMonthlyCapexReserve"],
            "dashboardCapexReserve": dashboard["totalMonthlyCapexReserve"],
            "year10Roi": year10_roi,
        },
        emergency_debt_ledger=emergency_debt_ledger,
        shock_survival=shock_survival,
    )


def normalize_rental_capex_input(
    request: RentalCapexCalculationRequest | None = None,
    *,
    model_spec: Mapping[str, object],
) -> dict[str, object]:
    return normalize_input(
        _calculation_request(request).to_input_dict(),
        model_spec_record(model_spec),
    )


def _calculation_request(
    request: RentalCapexCalculationRequest | None,
) -> RentalCapexCalculationRequest:
    if request is None:
        return RentalCapexCalculationRequest()

    if isinstance(request, RentalCapexCalculationRequest):
        return request

    raise TypeError("calculate_rental_capex request must be RentalCapexCalculationRequest.")


def _lookup_assumptions(
    input_data: Mapping[str, object],
    model_spec: Mapping[str, object],
) -> dict[str, object]:
    assumptions = model_spec["assumptions"]
    rent_vacancy_baselines = assumptions["rentVacancyBaselines"]
    rent_vacancy = rent_vacancy_baselines.get(input_data["subregion"])

    if not rent_vacancy:
        raise RentalCapexError(
            LOOKUP_ERROR,
            "Unknown subregion.",
            {"subregion": input_data["subregion"]},
        )

    if input_data["propertyProfile"] not in rent_vacancy:
        raise RentalCapexError(
            LOOKUP_ERROR,
            "Unknown property profile for rent lookup.",
            {"propertyProfile": input_data["propertyProfile"]},
        )

    try:
        profile_index = assumptions["profiles"].index(input_data["propertyProfile"])
    except ValueError as error:
        raise RentalCapexError(
            LOOKUP_ERROR,
            "Unknown property profile for quantity lookup.",
            {"propertyProfile": input_data["propertyProfile"]},
        ) from error

    return {
        "marketRent": rent_vacancy[input_data["propertyProfile"]],
        "vacancyRate": rent_vacancy["vacancyRate"],
        "profileIndex": profile_index,
    }


def _compute_sinking_fund(
    input_data: Mapping[str, object],
    model_spec: Mapping[str, object],
    lookups: Mapping[str, object],
) -> dict[str, object]:
    active_overrides_count = 0
    components = model_spec["assumptions"]["components"]
    known_components = {component["name"] for component in components}

    for component_name in dict(input_data.get("componentOverrides") or {}):
        if component_name not in known_components:
            raise RentalCapexError(
                LOOKUP_ERROR,
                "Unknown CapEx component override.",
                {"component": component_name},
            )

    sinking_fund_rows = []

    for component in components:
        default_quantity = component["quantities"][lookups["profileIndex"]]
        override = dict(input_data.get("componentOverrides") or {}).get(
            component["name"],
            {},
        )
        quantity_override_active = (
            not is_blank(override.get("quantity"))
            and override.get("quantity") != default_quantity
        )
        age_override_active = (
            not is_blank(override.get("age"))
            and override.get("age") != input_data["effectiveAgeYears"]
        )

        effective_quantity = (
            override.get("quantity") if quantity_override_active else default_quantity
        )
        effective_age = (
            override.get("age") if age_override_active else input_data["effectiveAgeYears"]
        )
        remaining_life = max(component["lifespan"] - effective_age, 1)
        local_unit_cost = _get_local_unit_cost(component, input_data["subregion"])
        future_cost = (
            local_unit_cost
            * effective_quantity
            * (1 + input_data["capexInflationRate"]) ** remaining_life
        )
        monthly_reserve = pmt(
            input_data["reserveAccountApy"] / 12,
            remaining_life * 12,
            0,
            -future_cost,
            0,
        )
        override_status = (
            "OVERRIDE ACTIVE"
            if quantity_override_active or age_override_active
            else ""
        )

        if override_status:
            active_overrides_count += 1

        sinking_fund_rows.append(
            {
                "component": component["name"],
                "localUnitCost": local_unit_cost,
                "defaultQuantity": default_quantity,
                "effectiveQuantity": effective_quantity,
                "swpaLifespan": component["lifespan"],
                "defaultAge": input_data["effectiveAgeYears"],
                "effectiveAge": effective_age,
                "remainingLife": remaining_life,
                "futureCost": future_cost,
                "monthlyReserve": monthly_reserve,
                "overrideStatus": override_status,
            }
        )

    total_monthly_capex_reserve = sum(row["monthlyReserve"] for row in sinking_fund_rows)

    return {
        "activeOverridesCount": active_overrides_count,
        "sinkingFundRows": sinking_fund_rows,
        "totalMonthlyCapexReserve": total_monthly_capex_reserve,
    }


def _compute_pro_forma(
    input_data: Mapping[str, object],
    dashboard: Mapping[str, object],
) -> list[dict[str, object]]:
    annual_cash_flow = dashboard["trueMonthlyCashFlow"] * 12
    annual_capex_reserve = dashboard["totalMonthlyCapexReserve"] * 12
    loan_term_months = input_data["loanTermYears"] * 12
    monthly_loan_rate = input_data["loanInterestRate"] / 12
    pro_forma = []
    accumulated_capex_reserve = 0
    accumulated_true_cash_flow = 0

    for year in range(0, 11):
        money_market_comparison = (
            dashboard["totalInitialInvestment"]
            * (1 + input_data["moneyMarketApy"]) ** year
        )
        conservative_ira_comparison = (
            dashboard["totalInitialInvestment"]
            * (1 + input_data["conservativeIraApy"]) ** year
        )

        if year == 0:
            pro_forma.append(
                {
                    "year": year,
                    "annualCapexContribution": 0,
                    "accumulatedCapexReserve": 0,
                    "accumulatedTrueCashFlow": 0,
                    "realEstateLiquidationWealth": dashboard[
                        "totalInitialInvestment"
                    ],
                    "moneyMarketComparison": dashboard["totalInitialInvestment"],
                    "conservativeIraComparison": dashboard[
                        "totalInitialInvestment"
                    ],
                }
            )
            continue

        annual_capex_contribution = (
            annual_capex_reserve
            if accumulated_capex_reserve < dashboard["targetCapExReserve"]
            else 0
        )
        accumulated_capex_reserve = min(
            dashboard["targetCapExReserve"],
            accumulated_capex_reserve * (1 + input_data["reserveAccountApy"])
            + annual_capex_contribution,
        )
        accumulated_true_cash_flow += annual_cash_flow + (
            annual_capex_reserve if annual_capex_contribution == 0 else 0
        )

        elapsed_months = year * 12
        future_property_value = (
            input_data["purchasePrice"] * (1 + input_data["appreciationRate"]) ** year
        )
        remaining_loan_balance = (
            0
            if elapsed_months >= loan_term_months
            else dashboard["loanAmount"]
            + cumulative_principal(
                monthly_loan_rate,
                loan_term_months,
                dashboard["loanAmount"],
                1,
                elapsed_months,
                0,
            )
        )
        cost_of_sale = future_property_value * input_data["costOfSaleRate"]
        net_proceeds = future_property_value - remaining_loan_balance - cost_of_sale

        pro_forma.append(
            {
                "year": year,
                "annualCapexContribution": annual_capex_contribution,
                "accumulatedCapexReserve": accumulated_capex_reserve,
                "accumulatedTrueCashFlow": accumulated_true_cash_flow,
                "realEstateLiquidationWealth": (
                    accumulated_true_cash_flow
                    + net_proceeds
                    + (accumulated_capex_reserve if year == 10 else 0)
                ),
                "moneyMarketComparison": money_market_comparison,
                "conservativeIraComparison": conservative_ira_comparison,
                "futurePropertyValue": future_property_value,
                "remainingLoanBalance": remaining_loan_balance,
                "costOfSale": cost_of_sale,
                "netProceeds": net_proceeds,
            }
        )

    return pro_forma


def _get_local_unit_cost(component: Mapping[str, object], subregion: str) -> float:
    adjustment = dict(component.get("regionalAdjustments") or {}).get(subregion, 0)
    return component["centralCost"] * (1 + adjustment)
