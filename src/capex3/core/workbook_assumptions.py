from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ComponentCostSource:
    name: str
    central_cost: float
    regional_adjustments: Mapping[str, float]
    regional_cost_formula: bool


@dataclass(frozen=True)
class ComponentQuantitySource:
    name: str
    quantities: Sequence[float]


@dataclass(frozen=True)
class WorkbookSourceData:
    source_workbook: str
    inputs: Mapping[str, object]
    profiles: Sequence[str]
    subregions: Sequence[str]
    rent_vacancy_baselines: Mapping[str, Mapping[str, float]]
    component_costs: Sequence[ComponentCostSource]
    component_quantities: Mapping[str, ComponentQuantitySource]
    component_lifespans: Mapping[str, float]


@dataclass(frozen=True)
class CapExComponent:
    name: str
    central_cost: float
    regional_adjustments: Mapping[str, float]
    quantities: Sequence[float]
    lifespan: float
    regional_cost_formula: bool

    def to_model_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "centralCost": self.central_cost,
            "regionalAdjustments": deepcopy(dict(self.regional_adjustments)),
            "quantities": list(self.quantities),
            "lifespan": self.lifespan,
            "regionalCostFormula": self.regional_cost_formula,
        }


@dataclass(frozen=True)
class WorkbookAssumptions:
    profiles: Sequence[str]
    subregions: Sequence[str]
    rent_vacancy_baselines: Mapping[str, Mapping[str, float]]
    components: Sequence[CapExComponent]

    def to_model_record(self) -> dict[str, object]:
        return {
            "profiles": list(self.profiles),
            "subregions": list(self.subregions),
            "rentVacancyBaselines": deepcopy(dict(self.rent_vacancy_baselines)),
            "components": [component.to_model_record() for component in self.components],
        }


@dataclass(frozen=True)
class WorkbookModelSpec:
    source_workbook: str
    inputs: Mapping[str, object]
    assumptions: WorkbookAssumptions

    def to_model_spec(self) -> dict[str, object]:
        return {
            "sourceWorkbook": self.source_workbook,
            "inputs": deepcopy(dict(self.inputs)),
            "assumptions": self.assumptions.to_model_record(),
        }


def compose_workbook_model_spec(source_data: WorkbookSourceData) -> WorkbookModelSpec:
    if not isinstance(source_data, WorkbookSourceData):
        raise TypeError("source_data must be a WorkbookSourceData.")

    if source_data.inputs.get("subregion") not in source_data.subregions:
        raise ValueError("default deal inputs subregion must exist in baselines.")

    if source_data.inputs.get("propertyProfile") not in source_data.profiles:
        raise ValueError("default deal inputs property profile must exist in baselines.")

    assumptions = WorkbookAssumptions(
        profiles=tuple(source_data.profiles),
        subregions=tuple(source_data.subregions),
        rent_vacancy_baselines=deepcopy(dict(source_data.rent_vacancy_baselines)),
        components=_compose_components(source_data),
    )

    return WorkbookModelSpec(
        source_workbook=source_data.source_workbook,
        inputs=deepcopy(dict(source_data.inputs)),
        assumptions=assumptions,
    )


def model_spec_record(model_spec: WorkbookModelSpec | Mapping[str, object]) -> dict:
    if isinstance(model_spec, WorkbookModelSpec):
        return model_spec.to_model_spec()

    if isinstance(model_spec, Mapping):
        return deepcopy(dict(model_spec))

    raise TypeError("model_spec must be a WorkbookModelSpec or mapping.")


def _compose_components(source_data: WorkbookSourceData) -> tuple[CapExComponent, ...]:
    components: list[CapExComponent] = []
    profile_count = len(source_data.profiles)

    for component in source_data.component_costs:
        lifespan = source_data.component_lifespans.get(component.name)
        quantity_source = source_data.component_quantities.get(component.name)

        if lifespan is None:
            raise ValueError(f"Missing lifespan for {component.name}.")

        if quantity_source is None:
            raise ValueError(f"Missing quantity defaults for {component.name}.")

        if len(quantity_source.quantities) != profile_count:
            raise ValueError(
                f"{component.name} quantity defaults must match profile count."
            )

        components.append(
            CapExComponent(
                name=component.name,
                central_cost=component.central_cost,
                regional_adjustments=deepcopy(dict(component.regional_adjustments)),
                quantities=tuple(quantity_source.quantities),
                lifespan=lifespan,
                regional_cost_formula=component.regional_cost_formula,
            )
        )

    return tuple(components)
