"""Scenario loading and deterministic demand helpers for Week 8 runs."""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


NUMERIC_MODIFIERS = {
    "demand_modifier",
    "lead_time_modifier",
    "supply_modifier",
    "price_sensitivity",
}


@dataclass(frozen=True)
class ScenarioSignal:
    day: int
    name: str
    modifiers: dict[str, float]
    notes: list[str]


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def signal_for_day(scenario: dict[str, Any], day: int) -> ScenarioSignal:
    """Merge all scenario events active on a day.

    Composition rule for overlapping events: numeric modifiers MULTIPLY
    (not max/min). Rationale: overlapping pressures should compound — e.g.
    a holiday peak (demand x1.9) that lands during supplier-congestion
    (supply x0.65) produces stronger combined pressure than either alone,
    which is what surfaces the bullwhip dynamic the week-8 spec asks for.
    Missing modifiers default to 1.0 so calm days remain neutral.
    """
    modifiers = {key: 1.0 for key in NUMERIC_MODIFIERS}
    notes: list[str] = []
    names: list[str] = []

    for event in scenario.get("events", []):
        start = int(event.get("start_day", event.get("day", 1)))
        end = int(event.get("end_day", start))
        if start <= day <= end:
            names.append(event.get("name", f"event-{start}-{end}"))
            notes.append(event.get("description", ""))
            for key in NUMERIC_MODIFIERS:
                if key in event:
                    modifiers[key] *= float(event[key])

    return ScenarioSignal(
        day=day,
        name=", ".join(names) if names else "baseline",
        modifiers=modifiers,
        notes=[note for note in notes if note],
    )


def deterministic_customer_demand(
    sku: str,
    base_daily_units: int,
    retail_price: float,
    reference_price: float,
    demand_modifier: float,
    price_sensitivity: float,
    seed: int,
) -> int:
    """Return reproducible customer demand for a SKU/day.

    Demand scales up with scenario pressure and down when price rises above the
    reference price. A small seeded jitter keeps the series realistic while
    preserving reproducibility.
    """
    rng = random.Random(seed)
    price_ratio = retail_price / reference_price if reference_price else 1.0
    price_effect = max(0.2, 1.0 - ((price_ratio - 1.0) * price_sensitivity))
    jitter = rng.uniform(0.85, 1.15)
    return max(0, int(math.ceil(base_daily_units * demand_modifier * price_effect * jitter)))
