"""Cash-flow stability evidence framing — planned reserve vs debt-shock paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

CASH_FLOW_STABILITY_LAYER_ID = "cashFlowStability"
CASH_FLOW_STABILITY_CONTRACT_SOURCE = "capex3.core.teaching"

PRIMARY_FRAMING_COPY = (
    "Not reserving does not remove the repair. It turns the repair into debt."
)

ALTERNATE_FRAMING_COPY = (
    "The deal does not fail when the repair happens. "
    "It fails when the repair arrives unfunded."
)

CASH_FLOW_STABILITY_EVIDENCE_CONCEPT = {
    "id": CASH_FLOW_STABILITY_LAYER_ID,
    "title": "Cash Flow Stability",
    "concept": "cash-flow stability",
    "description": (
        "Compare funding repairs through planned monthly reserves against "
        "absorbing the same events as emergency debt after a reserve shortfall."
    ),
    "shortLabel": "S",
}

CASH_FLOW_STABILITY_SOURCE_NOTE = (
    "App-only resilience evidence from emergencyDebtLedger and dashboard fields — "
    "not workbook-contract and not in the 17-case parity gate. "
    "repairReservePathTrace cross-reference is teaching-only."
)

PLANNED_RESERVE_PATH_TITLE = "Planned reserve path"
DEBT_SHOCK_PATH_TITLE = "Debt-shock path"

PathKind = Literal["planned", "debtShock", "both"]
FieldResolver = Literal["dotPath", "maxMonthlyPayment", "resultRef"]
ValueKind = Literal["moneyCents", "money", "percent", "number", "boolean", "list", "reference"]

TRACE_PLANNED_ROW_ROLES: tuple[str, ...] = (
    "plannedMonthlyReserve",
    "trueMonthlyCashFlow",
    "shockAdjustedCashFlow",
)

TRACE_DEBT_SHOCK_ROW_ROLES: tuple[str, ...] = (
    "peakEmergencyPayment",
    "outstandingPrincipal",
    "emergencyLoanApr",
    "emergencyLoanTermYears",
    "overlapDetected",
)


@dataclass(frozen=True)
class FieldRoleCatalogEntry:
    role: str
    path: str
    path_kind: PathKind
    label: str
    resolver: FieldResolver
    value_kind: ValueKind


FIELD_ROLE_CATALOG: tuple[FieldRoleCatalogEntry, ...] = (
    FieldRoleCatalogEntry(
        role="plannedMonthlyReserve",
        path="dashboard.totalMonthlyCapexReserve",
        path_kind="planned",
        label="Monthly reserve contribution (snapshot)",
        resolver="dotPath",
        value_kind="moneyCents",
    ),
    FieldRoleCatalogEntry(
        role="trueMonthlyCashFlow",
        path="dashboard.trueMonthlyCashFlow",
        path_kind="planned",
        label="True monthly cash flow (B40)",
        resolver="dotPath",
        value_kind="moneyCents",
    ),
    FieldRoleCatalogEntry(
        role="shockAdjustedCashFlow",
        path="shockAdjustedCashFlow",
        path_kind="both",
        label="Shock-adjusted cash flow (worst month)",
        resolver="dotPath",
        value_kind="moneyCents",
    ),
    FieldRoleCatalogEntry(
        role="dealSurvives",
        path="dealSurvives",
        path_kind="both",
        label="Deal survives repairs",
        resolver="dotPath",
        value_kind="boolean",
    ),
    FieldRoleCatalogEntry(
        role="peakEmergencyPayment",
        path="emergencyDebtLedger.refinanceEvents",
        path_kind="debtShock",
        label="Peak emergency debt payment",
        resolver="maxMonthlyPayment",
        value_kind="moneyCents",
    ),
    FieldRoleCatalogEntry(
        role="outstandingPrincipal",
        path="emergencyDebtLedger.outstandingPrincipal",
        path_kind="debtShock",
        label="Outstanding emergency principal (end of window)",
        resolver="dotPath",
        value_kind="money",
    ),
    FieldRoleCatalogEntry(
        role="emergencyLoanApr",
        path="emergencyDebtLedger.emergencyLoanApr",
        path_kind="debtShock",
        label="Emergency loan APR",
        resolver="dotPath",
        value_kind="percent",
    ),
    FieldRoleCatalogEntry(
        role="emergencyLoanTermYears",
        path="emergencyDebtLedger.emergencyLoanTermYears",
        path_kind="debtShock",
        label="Emergency loan term (years)",
        resolver="dotPath",
        value_kind="number",
    ),
    FieldRoleCatalogEntry(
        role="overlapDetected",
        path="overlapDetected",
        path_kind="debtShock",
        label="Stacked refinance overlap",
        resolver="dotPath",
        value_kind="boolean",
    ),
    FieldRoleCatalogEntry(
        role="overlapRefinanceYears",
        path="emergencyDebtLedger.overlapRefinanceYears",
        path_kind="debtShock",
        label="Overlap refinance years",
        resolver="dotPath",
        value_kind="list",
    ),
    FieldRoleCatalogEntry(
        role="repairTraceCrossReference",
        path="repairReservePathTrace",
        path_kind="planned",
        label="Repair fund timeline (teaching-only cross-reference)",
        resolver="resultRef",
        value_kind="reference",
    ),
)


class CashFlowStabilityEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class CashFlowStabilityFieldRole:
    role: str
    path: str
    path_kind: PathKind
    resolver: FieldResolver
    label: str
    value_kind: ValueKind
    value: object


@dataclass(frozen=True)
class CashFlowStabilityEvidenceContract:
    layer_id: str
    title: str
    concept: str
    description: str
    primary_framing_copy: str
    alternate_framing_copy: str
    planned_path_title: str
    debt_shock_path_title: str
    field_roles: Sequence[CashFlowStabilityFieldRole]
    contract_source: str
    source_note: str

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "layerId": self.layer_id,
            "title": self.title,
            "concept": self.concept,
            "description": self.description,
            "primaryFramingCopy": self.primary_framing_copy,
            "alternateFramingCopy": self.alternate_framing_copy,
            "plannedPathTitle": self.planned_path_title,
            "debtShockPathTitle": self.debt_shock_path_title,
            "fieldRoles": [
                _field_role_to_contract_dict(role) for role in self.field_roles
            ],
            "contractSource": self.contract_source,
            "sourceNote": self.source_note,
        }


def catalog_entry(role: str) -> FieldRoleCatalogEntry:
    for entry in FIELD_ROLE_CATALOG:
        if entry.role == role:
            return entry
    raise CashFlowStabilityEvidenceError(f"Unknown field role: {role}")


def describe_cash_flow_stability_evidence(
    result: Mapping[str, object],
) -> CashFlowStabilityEvidenceContract:
    _require_calculator_result(result)
    concept = CASH_FLOW_STABILITY_EVIDENCE_CONCEPT
    field_roles = tuple(
        CashFlowStabilityFieldRole(
            role=entry.role,
            path=entry.path,
            path_kind=entry.path_kind,
            resolver=entry.resolver,
            label=entry.label,
            value_kind=entry.value_kind,
            value=resolve_catalog_entry(result, entry),
        )
        for entry in FIELD_ROLE_CATALOG
    )
    return CashFlowStabilityEvidenceContract(
        layer_id=CASH_FLOW_STABILITY_LAYER_ID,
        title=str(concept["title"]),
        concept=str(concept["concept"]),
        description=str(concept["description"]),
        primary_framing_copy=PRIMARY_FRAMING_COPY,
        alternate_framing_copy=ALTERNATE_FRAMING_COPY,
        planned_path_title=PLANNED_RESERVE_PATH_TITLE,
        debt_shock_path_title=DEBT_SHOCK_PATH_TITLE,
        field_roles=field_roles,
        contract_source=CASH_FLOW_STABILITY_CONTRACT_SOURCE,
        source_note=CASH_FLOW_STABILITY_SOURCE_NOTE,
    )


def peak_emergency_payment_from_result(result: Mapping[str, object]) -> float:
    """Return the highest consolidated emergency payment from calculator output."""
    entry = catalog_entry("peakEmergencyPayment")
    value = resolve_catalog_entry(result, entry)
    return float(value or 0.0)


def build_trace_path_rows(
    result: Mapping[str, object],
    role_names: Sequence[str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for role_name in role_names:
        entry = catalog_entry(role_name)
        rows.append(
            {
                "role": entry.role,
                "label": entry.label,
                "value": resolve_catalog_entry(result, entry),
                "kind": entry.value_kind,
            }
        )
    return rows


def cash_flow_stability_evidence_to_contract(
    result: Mapping[str, object],
) -> dict[str, object]:
    return describe_cash_flow_stability_evidence(result).to_contract_dict()


def resolve_catalog_entry(
    result: Mapping[str, object],
    entry: FieldRoleCatalogEntry,
) -> object:
    if entry.resolver == "dotPath":
        return _resolve_dot_path(result, entry.path)
    if entry.resolver == "maxMonthlyPayment":
        return _resolve_max_monthly_payment(result, entry.path)
    if entry.resolver == "resultRef":
        return {"resultRef": entry.path}
    raise CashFlowStabilityEvidenceError(
        f"Unsupported field resolver: {entry.resolver}"
    )


def _field_role_to_contract_dict(role: CashFlowStabilityFieldRole) -> dict[str, object]:
    return {
        "role": role.role,
        "path": role.path,
        "pathKind": role.path_kind,
        "resolver": role.resolver,
        "label": role.label,
        "valueKind": role.value_kind,
        "value": role.value,
    }


def _require_calculator_result(result: Mapping[str, object]) -> None:
    if not isinstance(result, Mapping):
        raise CashFlowStabilityEvidenceError(
            "Cash-flow stability evidence requires a calculator result mapping."
        )
    required_keys = (
        "dashboard",
        "emergencyDebtLedger",
        "shockAdjustedCashFlow",
        "dealSurvives",
        "overlapDetected",
    )
    missing = [key for key in required_keys if key not in result]
    if missing:
        raise CashFlowStabilityEvidenceError(
            f"Calculator result missing required keys: {', '.join(missing)}"
        )


def _resolve_dot_path(result: Mapping[str, object], path: str) -> object:
    current: object = result
    for part in path.split("."):
        if not isinstance(current, Mapping):
            raise CashFlowStabilityEvidenceError(
                f"Cannot resolve path {path!r}: expected object at {part!r}."
            )
        if part not in current:
            raise CashFlowStabilityEvidenceError(
                f"Cannot resolve path {path!r}: missing key {part!r}."
            )
        current = current[part]
    return current


def _resolve_max_monthly_payment(result: Mapping[str, object], path: str) -> float:
    events = _resolve_dot_path(result, path)
    if not isinstance(events, list):
        raise CashFlowStabilityEvidenceError(
            f"Cannot resolve max monthly payment at {path!r}: expected a list."
        )
    payments = [
        float(event["monthlyPayment"])
        for event in events
        if isinstance(event, Mapping) and event.get("monthlyPayment") is not None
    ]
    return max(payments) if payments else 0.0
