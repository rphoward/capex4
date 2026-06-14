from copy import deepcopy
from dataclasses import dataclass, field
from typing import Mapping

from .errors import RentalCapexError, VALIDATION_ERROR
from .financial import _assert_finite_number as _assert_finite


NUMERIC_INPUT_FIELDS = (
    "purchasePrice",
    "actualGrossMonthlyRent",
    "annualPropertyTaxes",
    "hoaFeesMonthly",
    "effectiveAgeYears",
    "moneyMarketApy",
    "conservativeIraApy",
    "appreciationRate",
    "costOfSaleRate",
    "loanInterestRate",
    "loanTermYears",
    "estimatedClosingCostsPercent",
    "actualClosingCostsOverride",
    "immediateRehabMakeReady",
    "capexInflationRate",
    "reserveAccountApy",
    "emergencyLoanApr",
    "emergencyLoanTermYears",
    "annualInsurancePremium",
    "monthlyUtilitiesLandlordPaid",
    "propertyManagementFeePercent",
    "cleaningMaintenanceAnnual",
    "legalProfessionalAnnual",
    "advertisingLeasingAnnual",
    "minimumTrueMonthlyCashFlow",
    "monthlyReserveIncrease",
)

RATE_FIELDS = (
    "moneyMarketApy",
    "conservativeIraApy",
    "appreciationRate",
    "costOfSaleRate",
    "loanInterestRate",
    "estimatedClosingCostsPercent",
    "capexInflationRate",
    "reserveAccountApy",
    "emergencyLoanApr",
    "propertyManagementFeePercent",
)


INPUT_FIELD_TO_ATTRIBUTE = {
    "propertyAddress": "property_address",
    "subregion": "subregion",
    "propertyProfile": "property_profile",
    "purchasePrice": "purchase_price",
    "downPayment": "down_payment",
    "downPaymentPercentWhenBlank": "down_payment_percent_when_blank",
    "actualGrossMonthlyRent": "actual_gross_monthly_rent",
    "annualPropertyTaxes": "annual_property_taxes",
    "hoaFeesMonthly": "hoa_fees_monthly",
    "effectiveAgeYears": "effective_age_years",
    "moneyMarketApy": "money_market_apy",
    "conservativeIraApy": "conservative_ira_apy",
    "appreciationRate": "appreciation_rate",
    "costOfSaleRate": "cost_of_sale_rate",
    "loanInterestRate": "loan_interest_rate",
    "loanTermYears": "loan_term_years",
    "estimatedClosingCostsPercent": "estimated_closing_costs_percent",
    "actualClosingCostsOverride": "actual_closing_costs_override",
    "immediateRehabMakeReady": "immediate_rehab_make_ready",
    "capexInflationRate": "capex_inflation_rate",
    "reserveAccountApy": "reserve_account_apy",
    "emergencyLoanApr": "emergency_loan_apr",
    "emergencyLoanTermYears": "emergency_loan_term_years",
    "annualInsurancePremium": "annual_insurance_premium",
    "monthlyUtilitiesLandlordPaid": "monthly_utilities_landlord_paid",
    "propertyManagementFeePercent": "property_management_fee_percent",
    "cleaningMaintenanceAnnual": "cleaning_maintenance_annual",
    "legalProfessionalAnnual": "legal_professional_annual",
    "advertisingLeasingAnnual": "advertising_leasing_annual",
    "minimumTrueMonthlyCashFlow": "minimum_true_monthly_cash_flow",
    "monthlyReserveIncrease": "monthly_reserve_increase",
    "componentOverrides": "component_overrides",
}


@dataclass(frozen=True)
class RentalCapexComponentOverrideRequest:
    quantity: float | int | str | None = None
    age: float | int | str | None = None
    provided_fields: frozenset[str] = field(default_factory=frozenset, repr=False)

    @classmethod
    def from_contract_dict(
        cls,
        override: Mapping[str, object],
    ) -> "RentalCapexComponentOverrideRequest":
        if not isinstance(override, Mapping):
            raise RentalCapexError(
                VALIDATION_ERROR,
                "Component override request must be an object.",
                {"override": override},
            )

        allowed_fields = {"quantity", "age"}
        unknown_fields = sorted(set(override) - allowed_fields)
        if unknown_fields:
            raise RentalCapexError(
                VALIDATION_ERROR,
                "Component override request includes unknown fields.",
                {"fields": unknown_fields},
            )

        for field_name in allowed_fields:
            if field_name in override:
                _assert_not_boolean_number(override.get(field_name), field_name)

        return cls(
            quantity=override.get("quantity"),
            age=override.get("age"),
            provided_fields=frozenset(override),
        )

    def to_input_dict(self) -> dict[str, object]:
        return {
            field_name: getattr(self, field_name)
            for field_name in ("quantity", "age")
            if field_name in self.provided_fields
        }


@dataclass(frozen=True)
class RentalCapexDealInputRequest:
    property_address: str | None = None
    subregion: str | None = None
    property_profile: str | None = None
    purchase_price: float | int | None = None
    down_payment: float | int | str | None = None
    down_payment_percent_when_blank: float | int | None = None
    actual_gross_monthly_rent: float | int | None = None
    annual_property_taxes: float | int | None = None
    hoa_fees_monthly: float | int | None = None
    effective_age_years: float | int | None = None
    money_market_apy: float | int | None = None
    conservative_ira_apy: float | int | None = None
    appreciation_rate: float | int | None = None
    cost_of_sale_rate: float | int | None = None
    loan_interest_rate: float | int | None = None
    loan_term_years: float | int | None = None
    estimated_closing_costs_percent: float | int | None = None
    actual_closing_costs_override: float | int | None = None
    immediate_rehab_make_ready: float | int | None = None
    capex_inflation_rate: float | int | None = None
    reserve_account_apy: float | int | None = None
    emergency_loan_apr: float | int | None = None
    emergency_loan_term_years: float | int | None = None
    annual_insurance_premium: float | int | None = None
    monthly_utilities_landlord_paid: float | int | None = None
    property_management_fee_percent: float | int | None = None
    cleaning_maintenance_annual: float | int | None = None
    legal_professional_annual: float | int | None = None
    advertising_leasing_annual: float | int | None = None
    minimum_true_monthly_cash_flow: float | int | None = None
    monthly_reserve_increase: float | int | None = None
    component_overrides: Mapping[str, RentalCapexComponentOverrideRequest] = field(
        default_factory=dict
    )
    provided_fields: frozenset[str] = field(default_factory=frozenset, repr=False)

    @classmethod
    def from_contract_dict(
        cls,
        input_data: Mapping[str, object] | None = None,
    ) -> "RentalCapexDealInputRequest":
        if input_data is None:
            return cls()

        if not isinstance(input_data, Mapping):
            raise RentalCapexError(
                VALIDATION_ERROR,
                "Calculator input request must be an object.",
                {"input": input_data},
            )

        unknown_fields = sorted(set(input_data) - set(INPUT_FIELD_TO_ATTRIBUTE))
        if unknown_fields:
            raise RentalCapexError(
                VALIDATION_ERROR,
                "Calculator input request includes unknown fields.",
                {"fields": unknown_fields},
            )

        kwargs = {}
        for field_name, attribute_name in INPUT_FIELD_TO_ATTRIBUTE.items():
            if field_name not in input_data:
                continue

            if field_name == "componentOverrides":
                kwargs[attribute_name] = _component_override_records(
                    input_data.get(field_name)
                )
                continue

            value = input_data.get(field_name)
            if field_name in NUMERIC_INPUT_FIELDS or field_name == "downPayment":
                _assert_not_boolean_number(value, field_name)

            kwargs[attribute_name] = value

        return cls(**kwargs, provided_fields=frozenset(input_data))

    def to_input_dict(self) -> dict[str, object]:
        input_dict: dict[str, object] = {}

        for field_name, attribute_name in INPUT_FIELD_TO_ATTRIBUTE.items():
            if field_name not in self.provided_fields:
                continue

            value = getattr(self, attribute_name)
            if field_name == "componentOverrides":
                value = {
                    component: override.to_input_dict()
                    for component, override in dict(value).items()
                }

            input_dict[field_name] = value

        return input_dict


def is_blank(value: object) -> bool:
    return value is None or value == ""


def assert_model_spec(model_spec: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(model_spec, Mapping):
        raise RentalCapexError(
            VALIDATION_ERROR,
            "modelSpec is required to run the calculation engine.",
        )

    if not isinstance(model_spec.get("inputs"), Mapping) or not isinstance(
        model_spec.get("assumptions"), Mapping
    ):
        raise RentalCapexError(
            VALIDATION_ERROR,
            "modelSpec must include inputs and assumptions.",
        )

    return model_spec


def normalize_input(
    input_data: Mapping[str, object] | None,
    model_spec: Mapping[str, object],
) -> dict[str, object]:
    model_spec = assert_model_spec(model_spec)
    defaults = deepcopy(dict(model_spec["inputs"]))
    input_record = deepcopy(dict(input_data or {}))
    input_has_down_payment = "downPayment" in input_record

    normalized = {
        **defaults,
        **input_record,
        "componentOverrides": {
            **deepcopy(dict(defaults.get("componentOverrides") or {})),
            **deepcopy(dict(input_record.get("componentOverrides") or {})),
        },
    }

    if input_has_down_payment:
        normalized["downPayment"] = (
            normalized["purchasePrice"] * normalized["downPaymentPercentWhenBlank"]
            if is_blank(input_record.get("downPayment"))
            else input_record.get("downPayment")
        )
    elif is_blank(defaults.get("downPayment")):
        normalized["downPayment"] = (
            normalized["purchasePrice"] * normalized["downPaymentPercentWhenBlank"]
        )
    else:
        normalized["downPayment"] = defaults.get("downPayment")

    if "monthlyReserveIncrease" not in normalized:
        normalized["monthlyReserveIncrease"] = 0.0

    validate_input(normalized)
    return normalized


def validate_input(input_data: Mapping[str, object]) -> None:
    for field in NUMERIC_INPUT_FIELDS:
        _assert_finite(input_data.get(field), field)

    if not is_blank(input_data.get("downPayment")):
        _assert_finite(input_data.get("downPayment"), "downPayment")

    for component, override in dict(input_data.get("componentOverrides") or {}).items():
        if not isinstance(override, Mapping):
            raise RentalCapexError(
                VALIDATION_ERROR,
                "Component override must be an object.",
                {"component": component, "override": override},
            )

        if not is_blank(override.get("quantity")):
            _assert_finite(override.get("quantity"), f"{component}.quantity")

        if not is_blank(override.get("age")):
            _assert_finite(override.get("age"), f"{component}.age")

    for field in RATE_FIELDS:
        if input_data[field] <= -1:
            raise RentalCapexError(
                VALIDATION_ERROR,
                f"{field} must be greater than -100%.",
                {"field": field, "value": input_data[field]},
            )

    if input_data["purchasePrice"] < 0:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "purchasePrice must not be negative.",
            {"field": "purchasePrice", "value": input_data["purchasePrice"]},
        )

    if input_data["loanTermYears"] <= 0:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "loanTermYears must be greater than zero.",
            {"field": "loanTermYears", "value": input_data["loanTermYears"]},
        )

    if input_data["emergencyLoanTermYears"] <= 0:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "emergencyLoanTermYears must be greater than zero.",
            {
                "field": "emergencyLoanTermYears",
                "value": input_data["emergencyLoanTermYears"],
            },
        )

    if input_data["downPayment"] > input_data["purchasePrice"]:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "downPayment must not exceed purchasePrice.",
            {
                "downPayment": input_data["downPayment"],
                "purchasePrice": input_data["purchasePrice"],
            },
        )

    if input_data["minimumTrueMonthlyCashFlow"] < 0:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "minimumTrueMonthlyCashFlow must not be negative.",
            {
                "field": "minimumTrueMonthlyCashFlow",
                "value": input_data["minimumTrueMonthlyCashFlow"],
            },
        )

    if input_data["monthlyReserveIncrease"] < 0:
        raise RentalCapexError(
            VALIDATION_ERROR,
            "monthlyReserveIncrease must not be negative.",
            {
                "field": "monthlyReserveIncrease",
                "value": input_data["monthlyReserveIncrease"],
            },
        )


def _assert_not_boolean_number(value: object, field: str) -> None:
    if isinstance(value, bool):
        raise RentalCapexError(
            VALIDATION_ERROR,
            f"{field} must be a finite number.",
            {"field": field, "value": value},
        )


def _component_override_records(
    component_overrides: object,
) -> dict[str, RentalCapexComponentOverrideRequest]:
    if not isinstance(component_overrides, Mapping):
        raise RentalCapexError(
            VALIDATION_ERROR,
            "componentOverrides request must be an object.",
            {"componentOverrides": component_overrides},
        )

    return {
        str(component): RentalCapexComponentOverrideRequest.from_contract_dict(override)
        for component, override in component_overrides.items()
    }


DealInputs = RentalCapexDealInputRequest
