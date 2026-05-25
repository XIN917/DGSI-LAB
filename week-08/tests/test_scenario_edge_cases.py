"""Edge-case tests for scenario signal composition.

The spec (week8.pdf Part 3) says overlapping events compose multiplicatively
and missing modifiers default to 1.0. The week-8 simulation will reproduce
the bullwhip only if these boundary cases are correct, so we pin them
explicitly here. Each test reads like a behavioral assertion the spec
makes about scenarios.
"""
from __future__ import annotations

import math

import pytest

from scenario_utils import signal_for_day


def test_empty_events_list_is_neutral_baseline():
    """A scenario with no events produces a `baseline` signal with every
    modifier at 1.0."""
    signal = signal_for_day({"events": []}, day=5)

    assert signal.name == "baseline"
    assert signal.modifiers == {
        "demand_modifier": 1.0,
        "supply_modifier": 1.0,
        "lead_time_modifier": 1.0,
        "price_sensitivity": 1.0,
    }
    assert signal.notes == []


def test_day_before_any_event_is_baseline():
    """A day that precedes every event's start_day must return baseline
    (no leak of future modifiers)."""
    scenario = {"events": [{"start_day": 10, "end_day": 12, "demand_modifier": 3.0}]}
    signal = signal_for_day(scenario, day=9)

    assert signal.name == "baseline"
    assert signal.modifiers["demand_modifier"] == 1.0


def test_day_after_all_events_is_baseline():
    """Same on the trailing side: day 100 after all events ended must be
    neutral, not the last event's residue."""
    scenario = {"events": [{"start_day": 1, "end_day": 3, "supply_modifier": 0.4}]}
    signal = signal_for_day(scenario, day=100)

    assert signal.modifiers["supply_modifier"] == 1.0


def test_single_day_event_only_fires_on_that_day():
    """start_day == end_day means a one-day event. The day before and
    after must be baseline."""
    scenario = {
        "events": [
            {"start_day": 7, "end_day": 7, "demand_modifier": 5.0, "name": "flash-sale"}
        ]
    }

    assert signal_for_day(scenario, day=6).modifiers["demand_modifier"] == 1.0
    on_day = signal_for_day(scenario, day=7)
    assert on_day.modifiers["demand_modifier"] == 5.0
    assert "flash-sale" in on_day.name
    assert signal_for_day(scenario, day=8).modifiers["demand_modifier"] == 1.0


def test_three_overlapping_events_compound_multiplicatively():
    """Three simultaneous events on day 5 must produce the product of
    their modifiers, not the max or the last-write-wins."""
    scenario = {
        "events": [
            {"start_day": 1, "end_day": 10, "demand_modifier": 2.0},
            {"start_day": 1, "end_day": 10, "demand_modifier": 1.5},
            {"start_day": 1, "end_day": 10, "demand_modifier": 1.25},
        ]
    }
    signal = signal_for_day(scenario, day=5)
    assert math.isclose(signal.modifiers["demand_modifier"], 2.0 * 1.5 * 1.25)


def test_event_with_partial_modifiers_only_compounds_what_it_specifies():
    """An event that sets only supply_modifier must leave the others at
    1.0 — it must not zero out unspecified modifiers."""
    scenario = {
        "events": [
            {"start_day": 1, "end_day": 5, "supply_modifier": 0.6},
            {"start_day": 1, "end_day": 5, "demand_modifier": 2.0},
        ]
    }
    signal = signal_for_day(scenario, day=3)

    assert signal.modifiers["supply_modifier"] == 0.6
    assert signal.modifiers["demand_modifier"] == 2.0
    assert signal.modifiers["lead_time_modifier"] == 1.0
    assert signal.modifiers["price_sensitivity"] == 1.0


def test_boundary_inclusive_start_and_end_days():
    """The event range is inclusive on both ends: start_day and end_day
    both fire the modifier."""
    scenario = {"events": [{"start_day": 3, "end_day": 5, "demand_modifier": 4.0}]}

    assert signal_for_day(scenario, day=2).modifiers["demand_modifier"] == 1.0
    assert signal_for_day(scenario, day=3).modifiers["demand_modifier"] == 4.0
    assert signal_for_day(scenario, day=4).modifiers["demand_modifier"] == 4.0
    assert signal_for_day(scenario, day=5).modifiers["demand_modifier"] == 4.0
    assert signal_for_day(scenario, day=6).modifiers["demand_modifier"] == 1.0


def test_event_without_end_day_collapses_to_single_day():
    """A malformed event with only `start_day` defaults `end_day` to the
    start, behaving as a one-day event rather than running forever."""
    scenario = {"events": [{"start_day": 4, "demand_modifier": 2.0}]}

    assert signal_for_day(scenario, day=4).modifiers["demand_modifier"] == 2.0
    assert signal_for_day(scenario, day=5).modifiers["demand_modifier"] == 1.0


def test_notes_concatenate_descriptions_of_active_events_only():
    """Active events contribute descriptions; inactive ones do not."""
    scenario = {
        "events": [
            {
                "start_day": 1,
                "end_day": 3,
                "name": "early",
                "description": "early phase",
                "demand_modifier": 1.2,
            },
            {
                "start_day": 5,
                "end_day": 8,
                "name": "late",
                "description": "late phase",
                "demand_modifier": 1.5,
            },
        ]
    }
    signal_mid = signal_for_day(scenario, day=2)
    signal_gap = signal_for_day(scenario, day=4)
    signal_late = signal_for_day(scenario, day=6)

    assert signal_mid.notes == ["early phase"]
    assert signal_gap.notes == []
    assert signal_late.notes == ["late phase"]


def test_extreme_compound_does_not_overflow():
    """Stress: 10 events each with a 0.5 supply modifier yields a very
    small but finite number. Verifies no overflow/underflow surprises."""
    scenario = {
        "events": [{"start_day": 1, "end_day": 1, "supply_modifier": 0.5} for _ in range(10)]
    }
    signal = signal_for_day(scenario, day=1)
    assert signal.modifiers["supply_modifier"] == pytest.approx(0.5 ** 10)
    assert signal.modifiers["supply_modifier"] > 0
