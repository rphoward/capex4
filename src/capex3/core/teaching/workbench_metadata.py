"""Journey, workbench, and solver UI metadata for HTTP workbench payloads."""

from __future__ import annotations

from copy import deepcopy

from .cash_flow_stability_evidence import CASH_FLOW_STABILITY_EVIDENCE_CONCEPT
from .evidence_presentation import presentation_for_layer

JOURNEY_STAGES = [
    {
        "id": "listing",
        "title": "Listing Check",
        "description": (
            "Start with facts you can usually collect from a listing, tax record, "
            "or quick owner conversation."
        ),
        "fields": [
            "propertyAddress",
            "subregion",
            "propertyProfile",
            "purchasePrice",
            "actualGrossMonthlyRent",
            "annualPropertyTaxes",
        ],
    },
    {
        "id": "walkthrough",
        "title": "Walkthrough",
        "description": (
            "Use the property visit to replace generic repair assumptions with what "
            "you can actually see."
        ),
        "fields": [
            "effectiveAgeYears",
            "capexInflationRate",
            "cleaningMaintenanceAnnual",
            "legalProfessionalAnnual",
            "advertisingLeasingAnnual",
            "immediateRehabMakeReady",
        ],
    },
    {
        "id": "loan",
        "title": "Loan Terms",
        "description": (
            "Refine the financing assumptions after a lender conversation or a more "
            "realistic debt quote."
        ),
        "fields": [
            "downPayment",
            "loanInterestRate",
            "loanTermYears",
            "reserveAccountApy",
            "emergencyLoanApr",
            "emergencyLoanTermYears",
            "estimatedClosingCostsPercent",
            "hoaFeesMonthly",
            "monthlyUtilitiesLandlordPaid",
            "annualInsurancePremium",
            "propertyManagementFeePercent",
            "actualClosingCostsOverride",
        ],
    },
    {
        "id": "decision",
        "title": "Decision Packet",
        "description": (
            "Check the longer-term assumptions and ask threshold questions before "
            "chasing the deal further."
        ),
        "fields": [
            "appreciationRate",
            "costOfSaleRate",
            "moneyMarketApy",
            "conservativeIraApy",
            "minimumTrueMonthlyCashFlow",
        ],
    },
]

INPUT_FIELD_CONTROLS = {
    "propertyAddress": {
        "label": "Property label or address",
        "kind": "text",
        "span": "full",
        "hint": "A name you can recognize while comparing deals.",
    },
    "subregion": {
        "label": "Area",
        "kind": "select",
        "optionsSource": "subregions",
        "hint": "Drives local rent, vacancy, and repair-cost assumptions.",
    },
    "propertyProfile": {
        "label": "Property type",
        "kind": "select",
        "optionsSource": "profiles",
        "hint": "Sets researched size and repair defaults.",
    },
    "purchasePrice": {
        "label": "Purchase price",
        "kind": "currency",
        "hint": "The listing or offer price before financing.",
    },
    "actualGrossMonthlyRent": {
        "label": "Expected monthly rent",
        "kind": "currency",
        "hint": "Gross rent before vacancy, expenses, repair fund, and debt.",
    },
    "annualPropertyTaxes": {
        "label": "Annual property taxes",
        "kind": "currency",
        "hint": "Yearly tax bill converted to a monthly cost.",
    },
    "hoaFeesMonthly": {
        "label": "Monthly HOA",
        "kind": "currency",
        "hint": "Recurring association fees paid each month.",
    },
    "annualInsurancePremium": {
        "label": "Annual insurance",
        "kind": "currency",
        "hint": "Yearly insurance premium converted to a monthly cost.",
    },
    "monthlyUtilitiesLandlordPaid": {
        "label": "Monthly landlord-paid utilities",
        "kind": "currency",
        "hint": "Utilities you expect to cover instead of the tenant.",
    },
    "propertyManagementFeePercent": {
        "label": "Management fee",
        "kind": "rate",
        "hint": "Percent of usable income reserved for management.",
    },
    "cleaningMaintenanceAnnual": {
        "label": "Annual cleaning and maintenance",
        "kind": "currency",
        "hint": "Recurring annual upkeep outside the long-term repair fund.",
    },
    "legalProfessionalAnnual": {
        "label": "Annual legal and professional",
        "kind": "currency",
        "hint": "Recurring annual professional costs.",
    },
    "advertisingLeasingAnnual": {
        "label": "Annual advertising and leasing",
        "kind": "currency",
        "hint": "Recurring annual cost to lease or re-lease the property.",
    },
    "immediateRehabMakeReady": {
        "label": "Rough rehab or make-ready",
        "kind": "currency",
        "hint": "Cash needed up front to get the property ready.",
    },
    "effectiveAgeYears": {
        "label": "Overall effective age",
        "kind": "number",
        "hint": "How old or worn the property feels for future-repair planning.",
    },
    "capexInflationRate": {
        "label": "Repair-cost inflation",
        "kind": "rate",
        "hint": "Annual growth assumption for future replacement costs.",
    },
    "reserveAccountApy": {
        "label": "Repair fund APY",
        "kind": "rate",
        "hint": "Interest earned by money set aside for future repairs.",
    },
    "downPayment": {
        "label": "Down payment",
        "kind": "currency",
        "hint": "Cash paid up front against the purchase price.",
    },
    "loanInterestRate": {
        "label": "Loan interest rate",
        "kind": "rate",
        "hint": "Annual mortgage interest rate.",
    },
    "loanTermYears": {
        "label": "Loan term",
        "kind": "number",
        "hint": "Mortgage length in years.",
    },
    "emergencyLoanApr": {
        "label": "Emergency loan APR",
        "kind": "rate",
        "hint": (
            "Annual rate for post-close emergency borrowing when the repair fund "
            "cannot cover a gap — not your mortgage rate."
        ),
    },
    "emergencyLoanTermYears": {
        "label": "Emergency loan term",
        "kind": "number",
        "hint": (
            "Payment horizon in years when emergency debt is refinanced into one "
            "monthly payment."
        ),
    },
    "estimatedClosingCostsPercent": {
        "label": "Estimated closing cost rate",
        "kind": "rate",
        "hint": "Percent estimate used when no closing-cost override is entered.",
    },
    "actualClosingCostsOverride": {
        "label": "Closing cost override",
        "kind": "currency",
        "hint": "Optional known dollar amount for closing costs.",
    },
    "appreciationRate": {
        "label": "Home appreciation rate",
        "kind": "rate",
        "hint": "Annual property-value growth used in the 10-year view.",
    },
    "costOfSaleRate": {
        "label": "Cost to sell",
        "kind": "rate",
        "hint": "Selling-cost percent used in the 10-year exit view.",
    },
    "moneyMarketApy": {
        "label": "Money market APY",
        "kind": "rate",
        "hint": "Calmer alternative used in the 10-year comparison.",
    },
    "conservativeIraApy": {
        "label": "Conservative IRA APY",
        "kind": "rate",
        "hint": "Another long-term alternative used for comparison.",
    },
    "minimumTrueMonthlyCashFlow": {
        "label": "Minimum true monthly cash flow",
        "kind": "currency",
        "hint": (
            "Lowest monthly cash flow you will accept after reserves and debt. "
            "Used with shock-adjusted cash flow for the survival rule — does not "
            "change the displayed cash-flow number."
        ),
    },
}

def _metric_strip_navigation_item(
    field: str,
    layer: str,
    cta: str,
) -> dict[str, str]:
    presentation = presentation_for_layer(layer)
    return {
        "field": field,
        "layer": layer,
        "cta": cta,
        "focus": presentation.get("primaryReward", ""),
    }


METRIC_STRIP_NAVIGATION = [
    _metric_strip_navigation_item(
        "trueMonthlyCashFlow",
        "cashFlow",
        "See the breakdown",
    ),
    _metric_strip_navigation_item(
        "totalMonthlyCapexReserve",
        "repairDrivers",
        "See what drives it",
    ),
    _metric_strip_navigation_item(
        "breakevenGrossRent",
        "whatWorks",
        "What would work?",
    ),
]

_METRIC_STRIP_LAYER_BY_FIELD = {
    item["field"]: item["layer"] for item in METRIC_STRIP_NAVIGATION
}


def _metric_evidence_layer(field: str, default: str) -> str:
    return _METRIC_STRIP_LAYER_BY_FIELD.get(field, default)


EVIDENCE_CONCEPTS = [
    {
        "id": "tenYear",
        "title": "10-Year Story",
        "concept": "ten-year story",
        "description": (
            "Compare the rental path against calmer alternatives over 10 years."
        ),
        "shortLabel": "10",
    },
    {
        "id": "cashFlow",
        "title": "Monthly Cash Flow Breakdown",
        "concept": "monthly cash-flow breakdown",
        "description": (
            "Follow the money from expected rent to true monthly cash flow after "
            "repair reserves and debt."
        ),
        "shortLabel": "$",
    },
    {
        "id": "repairDrivers",
        "title": "Repair Drivers",
        "concept": "repair drivers",
        "description": (
            "See which property items create the monthly repair fund, why they "
            "matter, and whether they came from defaults or walkthrough overrides."
        ),
        "shortLabel": "R",
    },
    {
        "id": "repairFund",
        "title": "Repair Fund",
        "concept": "repair fund story",
        "description": (
            "Compare a live repair reserve balance against the same repair events "
            "arriving as no-reserve surprise costs."
        ),
        "shortLabel": "F",
    },
    deepcopy(CASH_FLOW_STABILITY_EVIDENCE_CONCEPT),
    {
        "id": "whatWorks",
        "title": "What Would Work?",
        "concept": "what-would-work threshold questions",
        "description": (
            "Explore threshold questions under current assumptions — not "
            "recommendations."
        ),
        "shortLabel": "?",
    },
]

STAGE_EVIDENCE_MAPPING = {
    "decision": "whatWorks",
    "listing": "tenYear",
    "loan": "cashFlow",
    "walkthrough": "cashFlowStability",
}

SOLVER_VARIABLES = [
    {
        "id": "rent",
        "label": "Rent",
        "previewLabel": "rent",
        "applyField": "actualGrossMonthlyRent",
        "valueKind": "moneyCents",
        "showInManualControls": True,
        "assumptionText": "Solved under the current input assumptions. Apply updates one input only.",
    },
    {
        "id": "purchasePriceWithDefaultDownPayment",
        "label": "Purchase Price",
        "previewLabel": "purchase price",
        "applyField": "purchasePrice",
        "valueKind": "moneyCents",
        "showInManualControls": True,
        "assumptionText": (
            "Solved with your default down-payment percent. "
            "Apply updates purchase price only."
        ),
    },
    {
        "id": "purchasePriceWithFixedDownPayment",
        "label": "Purchase Price",
        "previewLabel": "purchase price",
        "applyField": "purchasePrice",
        "valueKind": "moneyCents",
        "showInManualControls": False,
        "assumptionText": (
            "Solved with the current down payment held fixed. "
            "Apply updates purchase price only."
        ),
    },
    {
        "id": "downPayment",
        "label": "Down Payment",
        "previewLabel": "down payment",
        "applyField": "downPayment",
        "valueKind": "moneyCents",
        "showInManualControls": True,
        "assumptionText": "Solved under the current input assumptions. Apply updates one input only.",
    },
    {
        "id": "rehabBudget",
        "label": "Rehab Budget",
        "previewLabel": "rehab budget",
        "applyField": "immediateRehabMakeReady",
        "valueKind": "moneyCents",
        "showInManualControls": True,
        "assumptionText": "Solved under the current input assumptions. Apply updates one input only.",
    },
    {
        "id": "monthlyReserveIncrease",
        "label": "Monthly reserve increase",
        "previewLabel": "monthly reserve increase",
        "applyField": "monthlyReserveIncrease",
        "valueKind": "moneyCents",
        "showInManualControls": False,
        "assumptionText": (
            "Clears the first emergency repair gap at year 2 or later only. "
            "Apply updates monthlyReserveIncrease only — does not clear overlap warnings."
        ),
    },
]

SOLVER_METRICS = [
    {"id": "monthlyCashFlow", "label": "Monthly Cash Flow", "valueKind": "moneyCents"},
    {"id": "cashOnCashReturn", "label": "Cash-on-Cash Return", "valueKind": "percent"},
    {"id": "year10Roi", "label": "Year-10 ROI", "valueKind": "percent"},
    {"id": "year10AnnualizedRoi", "label": "Annualized ROI", "valueKind": "percent"},
    {
        "id": "firstEmergencyGap",
        "label": "First emergency gap",
        "valueKind": "money",
        "showInManualControls": False,
    },
]

METRIC_GUIDANCE = [
    (
        "trueMonthlyCashFlow",
        "True monthly cash flow",
        "moneyCents",
        _metric_evidence_layer("trueMonthlyCashFlow", "cashFlow"),
    ),
    (
        "totalMonthlyCapexReserve",
        "Monthly repair fund",
        "moneyCents",
        _metric_evidence_layer("totalMonthlyCapexReserve", "repairDrivers"),
    ),
    (
        "breakevenGrossRent",
        "Break-even rent",
        "moneyCents",
        _metric_evidence_layer("breakevenGrossRent", "whatWorks"),
    ),
    ("targetCapExReserve", "Target CapEx Reserve", "money", "cashFlow"),
    ("cashOnCashReturn", "Cash-on-Cash Return", "percent", "whatWorks"),
    ("year10Roi", "Year-10 ROI", "percent", "tenYear"),
    ("capRate", "Cap Rate", "percent", "cashFlow"),
    ("debtServiceCoverageRatio", "DSCR", "number", "cashFlow"),
    ("yearOneTotalReturnOnEquity", "Year 1 Total Return on Equity", "percent", "tenYear"),
    ("rentToValueRatio", "Rent-to-Value Ratio", "percent", "cashFlow"),
    ("marketRent", "Market Rent", "moneyCents", "tenYear"),
    ("vacancyRate", "Vacancy Rate", "percent", "cashFlow"),
    ("netOperatingIncomeMonthly", "Income Before Debt", "moneyCents", "cashFlow"),
    ("monthlyMortgagePI", "Loan Payment", "moneyCents", "cashFlow"),
    ("totalInitialInvestment", "Cash Needed Up Front", "money", "tenYear"),
    ("year10AnnualizedRoi", "Annualized ROI", "percent", "tenYear"),
]

METRIC_SOURCE_NOTES = {
    "trueMonthlyCashFlow": (
        "Dashboard underwriting snapshot. Deducts full monthly "
        "totalMonthlyCapexReserve every month—not the post-cap pro forma path. "
        "After the reserve cap fills, annual cash improvement appears in pro "
        "forma accumulated cash flow; see 10-Year Story."
    ),
    "year10Roi": "Excludes reserve returned at sale.",
}

EVIDENCE_METRIC_FIELDS = {
    "cashFlow": [
        "trueMonthlyCashFlow",
        "netOperatingIncomeMonthly",
        "monthlyMortgagePI",
        "targetCapExReserve",
        "debtServiceCoverageRatio",
        "rentToValueRatio",
    ],
    "repairDrivers": [
        "totalMonthlyCapexReserve",
        "netOperatingIncomeMonthly",
        "trueMonthlyCashFlow",
    ],
    "repairFund": [
        "totalMonthlyCapexReserve",
        "targetCapExReserve",
        "trueMonthlyCashFlow",
    ],
    "tenYear": [
        "yearOneTotalReturnOnEquity",
        "year10Roi",
        "year10AnnualizedRoi",
        "totalInitialInvestment",
    ],
    "whatWorks": [
        "trueMonthlyCashFlow",
        "cashOnCashReturn",
        "totalInitialInvestment",
        "breakevenGrossRent",
    ],
    "cashFlowStability": [
        "trueMonthlyCashFlow",
        "totalMonthlyCapexReserve",
        "shockAdjustedCashFlow",
        "overlapDetected",
    ],
}

CALCULATION_LINKAGE_FIELDS = [
    ("Dashboard!B3", "Subregion", "subregion", "input.subregion", "dashboard.subregion", "Subregion select"),
    (
        "Dashboard!B4",
        "Property profile",
        "propertyProfile",
        "input.propertyProfile",
        "dashboard.propertyProfile",
        "Profile select",
    ),
    (
        "10-Year Pro Forma!B2",
        "Purchase price",
        "purchasePrice",
        "input.purchasePrice",
        "dashboard.purchasePrice",
        "Purchase Price input",
    ),
    (
        "Dashboard!B6",
        "Gross monthly rent",
        "actualGrossMonthlyRent",
        "input.actualGrossMonthlyRent",
        "dashboard.actualGrossMonthlyRent",
        "Gross Monthly Rent input",
    ),
    (
        "Dashboard",
        "True monthly cash flow",
        "actualGrossMonthlyRent",
        "input.actualGrossMonthlyRent",
        "dashboard.trueMonthlyCashFlow",
        "Gross Monthly Rent input",
    ),
    (
        "Dashboard!B42",
        "Cash-on-cash return",
        "downPayment",
        "input.downPayment",
        "dashboard.cashOnCashReturn",
        "Down Payment input",
    ),
    (
        "10-Year Pro Forma",
        "Year 10 liquidation wealth",
        "appreciationRate",
        "input.appreciationRate",
        "proForma.10.realEstateLiquidationWealth",
        "Appreciation Rate input",
    ),
]
