import math
from typing import Mapping, Sequence


def compute_repair_reserve_path_trace(
    input_data: Mapping[str, object],
    dashboard: Mapping[str, object],
    sinking_fund_rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    monthly_bump = float(input_data.get("monthlyReserveIncrease") or 0.0)
    base_monthly_contribution = float(dashboard["totalMonthlyCapexReserve"])
    monthly_contribution = base_monthly_contribution + monthly_bump
    base_annual_contribution = base_monthly_contribution * 12
    bump_annual_contribution = monthly_bump * 12
    target_reserve = dashboard["targetCapExReserve"]
    annual_apy = input_data["reserveAccountApy"]
    events_by_year: dict[int, list[dict[str, object]]] = {
        year: [] for year in range(11)
    }

    for row in sinking_fund_rows:
        remaining_life = row["remainingLife"]
        event_year = int(math.ceil(remaining_life))
        if event_year < 1 or event_year > 10:
            continue
        event = {
            "year": event_year,
            "component": row["component"],
            "label": repair_event_label(str(row["component"])),
            "amount": row["futureCost"],
            "remainingLife": remaining_life,
        }
        events_by_year[event_year].append(event)

    yearly_rows: list[dict[str, object]] = []
    balance = 0.0
    cumulative_no_reserve_cost = 0.0
    largest_event: dict[str, object] | None = None
    total_event_cost = 0.0
    minimum_balance = 0.0

    for year in range(0, 11):
        year_events = events_by_year[year]
        repair_cost = sum(event["amount"] for event in year_events)
        starting_balance = balance
        interest_earned = starting_balance * annual_apy
        base_contribution = (
            base_annual_contribution
            if base_annual_contribution > 0 and starting_balance < target_reserve
            else 0.0
        )
        contribution = base_contribution + bump_annual_contribution
        balance_before_repairs = min(
            target_reserve,
            starting_balance + interest_earned + base_contribution,
        ) + bump_annual_contribution
        ending_balance = balance_before_repairs - repair_cost
        balance = ending_balance

        cumulative_no_reserve_cost += repair_cost
        total_event_cost += repair_cost
        minimum_balance = min(minimum_balance, ending_balance)
        for event in year_events:
            if largest_event is None or event["amount"] > largest_event["amount"]:
                largest_event = event

        yearly_rows.append(
            {
                "year": year,
                "startingBalance": starting_balance,
                "annualContribution": contribution,
                "interestEarned": interest_earned,
                "balanceBeforeRepairs": balance_before_repairs,
                "repairCost": repair_cost,
                "endingBalance": ending_balance,
                "noReserveSurpriseCost": cumulative_no_reserve_cost,
                "events": year_events,
                "status": repair_reserve_year_status(
                    year_events,
                    balance_before_repairs,
                    ending_balance,
                ),
            }
        )

    event_markers = [
        {
            **dict(event),
            "endingBalance": yearly_rows[event["year"]]["endingBalance"],
            "noReserveSurpriseCost": yearly_rows[event["year"]][
                "noReserveSurpriseCost"
            ],
        }
        for events in events_by_year.values()
        for event in events
    ]
    return {
        "id": "repairReservePathTrace",
        "years": yearly_rows,
        "eventMarkers": event_markers,
        "totalEventCost": total_event_cost,
        "largestEvent": dict(largest_event) if largest_event else None,
        "minimumBalance": minimum_balance,
        "annualContribution": base_annual_contribution + bump_annual_contribution,
        "monthlyContribution": monthly_contribution,
        "monthlyReserveIncrease": monthly_bump,
        "targetReserve": target_reserve,
        "reserveAccountApy": annual_apy,
        "capexInflationRate": input_data["capexInflationRate"],
    }


def repair_event_label(component_name: str) -> str:
    label = component_name.split(":", 1)[-1].strip()
    label = label.split("(", 1)[0].strip()
    return label or component_name


def repair_reserve_year_status(
    events: Sequence[Mapping[str, object]],
    balance_before_repairs: float,
    ending_balance: float,
) -> str:
    if ending_balance < 0:
        return "shortfall"
    if events and ending_balance <= max(1.0, balance_before_repairs * 0.02):
        return "depleted"
    if events:
        return "repair-paid"
    return "building"
