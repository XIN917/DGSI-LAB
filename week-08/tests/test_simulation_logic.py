import pytest
from turn_engine import todays_signal

def test_todays_signal_multiplicative_modifiers():
    scenario = {
        "events": [
            {
                "name": "Event A",
                "start_day": 1,
                "end_day": 5,
                "demand_modifier": 2.0,
                "supply_modifier": 0.5,
                "lead_time_modifier": 1.2
            },
            {
                "name": "Event B",
                "start_day": 3,
                "end_day": 7,
                "demand_modifier": 1.5,
                "supply_modifier": 0.8,
                "lead_time_modifier": 2.0
            }
        ]
    }
    
    # Day 2: Only Event A active
    signal_d2 = todays_signal(2, scenario)
    assert signal_d2["demand_modifier"] == 2.0
    assert signal_d2["supply_modifier"] == 0.5
    assert signal_d2["lead_time_modifier"] == 1.2
    assert len(signal_d2["events"]) == 1
    
    # Day 4: Both active (modifiers should multiply)
    signal_d4 = todays_signal(4, scenario)
    assert signal_d4["demand_modifier"] == 3.0  # 2.0 * 1.5
    assert signal_d4["supply_modifier"] == 0.4  # 0.5 * 0.8
    assert signal_d4["lead_time_modifier"] == 2.4  # 1.2 * 2.0
    assert len(signal_d4["events"]) == 2
    
    # Day 6: Only Event B active
    signal_d6 = todays_signal(6, scenario)
    assert signal_d6["demand_modifier"] == 1.5
    assert signal_d6["supply_modifier"] == 0.8
    assert signal_d6["lead_time_modifier"] == 2.0
    assert len(signal_d6["events"]) == 1

def test_todays_signal_price_sensitivity():
    scenario = {
        "events": [
            {
                "name": "Normal Event",
                "start_day": 1,
                "end_day": 2,
                "price_sensitivity": "normal"
            },
            {
                "name": "High Sensitivity Event",
                "start_day": 2,
                "end_day": 4,
                "price_sensitivity": "high"
            }
        ]
    }
    
    # Day 1: normal
    assert todays_signal(1, scenario)["price_sensitivity"] == "normal"
    
    # Day 2: both (high should take precedence if any is high)
    assert todays_signal(2, scenario)["price_sensitivity"] == "high"
    
    # Day 3: only high
    assert todays_signal(3, scenario)["price_sensitivity"] == "high"

def test_todays_signal_base_demand():
    scenario = {
        "base_demand": {"mean": 10, "variance": 5},
        "events": []
    }
    signal = todays_signal(1, scenario)
    assert signal["base_demand"] == {"mean": 10, "variance": 5}

    # Default if missing
    assert todays_signal(1, {})["base_demand"] == {"mean": 5, "variance": 2}
