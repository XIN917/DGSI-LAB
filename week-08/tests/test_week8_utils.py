from scenario_utils import deterministic_customer_demand, signal_for_day
from turn_engine import main


def test_signal_for_day_multiplies_overlapping_modifiers():
    scenario = {
        "events": [
            {"start_day": 1, "end_day": 3, "demand_modifier": 2.0, "supply_modifier": 0.5},
            {"start_day": 2, "end_day": 4, "demand_modifier": 1.5, "lead_time_modifier": 2.0},
        ]
    }

    signal = signal_for_day(scenario, 2)

    assert signal.modifiers["demand_modifier"] == 3.0
    assert signal.modifiers["supply_modifier"] == 0.5
    assert signal.modifiers["lead_time_modifier"] == 2.0
    assert signal.modifiers["price_sensitivity"] == 1.0


def test_demand_generator_responds_to_price_and_scenario_pressure():
    low_pressure = deterministic_customer_demand(
        sku="P3D-Classic",
        base_daily_units=10,
        retail_price=1800,
        reference_price=1500,
        demand_modifier=1.0,
        price_sensitivity=1.0,
        seed=42,
    )
    high_pressure = deterministic_customer_demand(
        sku="P3D-Classic",
        base_daily_units=10,
        retail_price=1500,
        reference_price=1500,
        demand_modifier=2.0,
        price_sensitivity=1.0,
        seed=42,
    )

    assert high_pressure > low_pressure


def test_turn_engine_rejects_non_positive_days(capsys):
    assert main(["turn_engine.py", "config/sim.json", "scenarios/calm-market.json", "0"]) == 2
    assert "days must be positive" in capsys.readouterr().err


def test_turn_engine_rejects_non_integer_days(capsys):
    assert main(["turn_engine.py", "config/sim.json", "scenarios/calm-market.json", "abc"]) == 2
    assert "days must be an integer" in capsys.readouterr().err
