"""Unit tests for dashboard.derive — the single source of truth for computed
tier fields shared by the live (collector) and archive (app) paths."""
from dashboard import derive


def test_in_transit_excludes_terminal_and_waiting():
    pos = [
        {"status": "delivered", "quantity": 10},          # terminal — excluded
        {"status": "cancelled", "quantity": 99},          # terminal — excluded
        {"status": "waiting_materials", "quantity": 7},   # stalled — excluded
        {"status": "pending", "quantity": 5},             # moving
        {"status": "shipped", "quantity": 3},             # moving
        {"status": None, "quantity": 2},                  # unknown — counted as moving
    ]
    assert derive.retailer_in_transit(pos) == 10  # 5 + 3 + 2


def test_stalled_counts_only_waiting_materials():
    pos = [
        {"status": "waiting_materials", "quantity": 7},
        {"status": "waiting_materials", "quantity": 13},
        {"status": "pending", "quantity": 5},
        {"status": "delivered", "quantity": 100},
    ]
    assert derive.retailer_stalled(pos) == 20


def test_in_transit_and_stalled_are_disjoint():
    pos = [{"status": "waiting_materials", "quantity": 4},
           {"status": "pending", "quantity": 6}]
    assert derive.retailer_in_transit(pos) == 6
    assert derive.retailer_stalled(pos) == 4


def test_count_backordered():
    orders = [{"status": "backordered"}, {"status": "fulfilled"},
              {"status": "backordered"}, {"status": "pending"}]
    assert derive.count_backordered(orders) == 2


def test_dedup_parts_drops_finished_names():
    parts = {"P3D-Classic": 9, "frame_kit": 20, "hotend": 5}
    assert derive.dedup_parts(parts, {"P3D-Classic", "P3D-Pro"}) == {"frame_kit": 20, "hotend": 5}


def test_empty_and_none_inputs():
    assert derive.retailer_in_transit(None) == 0
    assert derive.retailer_stalled([]) == 0
    assert derive.count_backordered(None) == 0
    assert derive.dedup_parts(None, set()) == {}


def test_missing_quantity_key_treated_as_zero():
    assert derive.retailer_in_transit([{"status": "pending"}]) == 0
