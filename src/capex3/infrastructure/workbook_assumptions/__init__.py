import json
from importlib import resources
from pathlib import Path
from typing import Mapping, Sequence

from capex3.core.workbook_assumptions import (
    ComponentCostSource,
    ComponentQuantitySource,
    WorkbookModelSpec,
    WorkbookSourceData,
    compose_workbook_model_spec,
)


DATA_PACKAGE = "capex3.infrastructure.workbook_assumptions.data"
DATA_DIR = Path(__file__).resolve().parent / "data"


def load_workbook_model_spec() -> WorkbookModelSpec:
    sources = {
        "defaultDealInputs": _load_source_json("default-deal-inputs.json"),
        "rentVacancyBaselines": _load_source_json("rent-vacancy-baselines.json"),
        "quantityDefaults": _load_source_json("quantity-defaults.json"),
        "capexComponentCosts": _load_source_json("capex-component-costs.json"),
        "componentLifespans": _load_source_json("component-lifespans.json"),
    }
    return compose_workbook_model_spec_from_sources(sources)


def load_workbook_model_spec_record() -> dict[str, object]:
    return load_workbook_model_spec().to_model_spec()


def compose_workbook_model_spec_from_sources(
    sources: Mapping[str, Mapping[str, object]],
) -> WorkbookModelSpec:
    return compose_workbook_model_spec(workbook_source_data_from_sources(sources))


def workbook_source_data_from_sources(
    sources: Mapping[str, Mapping[str, object]],
) -> WorkbookSourceData:
    default_deal_inputs = _require_record(
        sources.get("defaultDealInputs"),
        "default deal inputs source must be an object.",
    )
    rent_vacancy_source = _require_record(
        sources.get("rentVacancyBaselines"),
        "rent and vacancy baselines source must be an object.",
    )
    quantity_source = _require_record(
        sources.get("quantityDefaults"),
        "quantity defaults source must be an object.",
    )
    cost_source = _require_record(
        sources.get("capexComponentCosts"),
        "capex component costs must include components.",
    )
    lifespan_source = _require_record(
        sources.get("componentLifespans"),
        "component lifespans must include lifespans.",
    )

    inputs = _require_record(
        default_deal_inputs.get("inputs"),
        "default deal inputs must include inputs.",
    )
    profiles = _require_sequence(
        rent_vacancy_source.get("profiles"),
        "rent and vacancy baselines must include profiles.",
    )
    subregions = _require_sequence(
        rent_vacancy_source.get("subregions"),
        "rent and vacancy baselines must include subregions.",
    )
    rent_vacancy_baselines = _require_record(
        rent_vacancy_source.get("rentVacancyBaselines"),
        "rent and vacancy baselines must include rentVacancyBaselines.",
    )
    quantity_profiles = _require_sequence(
        quantity_source.get("profiles"),
        "quantity defaults must include profiles.",
    )

    if list(quantity_profiles) != list(profiles):
        raise ValueError("quantity default profiles must match rent and vacancy profiles.")

    source_workbook = default_deal_inputs.get("sourceWorkbook")
    if not isinstance(source_workbook, str) or not source_workbook:
        raise ValueError("sourceWorkbook is required.")

    return WorkbookSourceData(
        source_workbook=source_workbook,
        inputs=dict(inputs),
        profiles=tuple(str(profile) for profile in profiles),
        subregions=tuple(str(subregion) for subregion in subregions),
        rent_vacancy_baselines=dict(rent_vacancy_baselines),
        component_costs=_component_cost_sources(cost_source),
        component_quantities=_component_quantity_sources(quantity_source),
        component_lifespans=_component_lifespan_sources(lifespan_source),
    )


def _component_cost_sources(
    cost_source: Mapping[str, object],
) -> tuple[ComponentCostSource, ...]:
    cost_components = _require_sequence(
        cost_source.get("components"),
        "capex component costs must include components.",
    )

    components: list[ComponentCostSource] = []
    for component in cost_components:
        component_record = _require_record(component, "component must be an object.")
        component_name = str(component_record.get("name"))
        components.append(
            ComponentCostSource(
                name=component_name,
                central_cost=float(component_record.get("centralCost")),
                regional_adjustments=dict(
                    _require_record(
                        component_record.get("regionalAdjustments"),
                        f"{component_name} must include regional adjustments.",
                    )
                ),
                regional_cost_formula=bool(component_record.get("regionalCostFormula")),
            )
        )

    return tuple(components)


def _component_quantity_sources(
    quantity_source: Mapping[str, object],
) -> dict[str, ComponentQuantitySource]:
    quantity_rows = _require_sequence(
        quantity_source.get("componentQuantities"),
        "quantity defaults must include componentQuantities.",
    )

    quantity_sources: dict[str, ComponentQuantitySource] = {}
    for row in quantity_rows:
        quantity_record = _require_record(row, "quantity default row must be an object.")
        component_name = str(quantity_record.get("component"))
        quantities = _require_sequence(
            quantity_record.get("quantities"),
            f"quantity defaults for {component_name} must include quantities.",
        )
        quantity_sources[component_name] = ComponentQuantitySource(
            name=component_name,
            quantities=tuple(float(quantity) for quantity in quantities),
        )

    return quantity_sources


def _component_lifespan_sources(
    lifespan_source: Mapping[str, object],
) -> dict[str, float]:
    lifespan_rows = _require_sequence(
        lifespan_source.get("lifespans"),
        "component lifespans must include lifespans.",
    )

    return {
        str(row["name"]): float(row["lifespan"])
        for row in lifespan_rows
        if isinstance(row, Mapping) and "name" in row
    }


def _load_source_json(file_name: str) -> Mapping[str, object]:
    source = resources.files(DATA_PACKAGE).joinpath(file_name)
    with source.open("r", encoding="utf8") as source_file:
        return json.load(source_file)


def _require_record(value: object, message: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(message)
    return value


def _require_sequence(value: object, message: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(message)
    return value
