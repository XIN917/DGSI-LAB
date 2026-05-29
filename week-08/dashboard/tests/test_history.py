import sqlite3
from pathlib import Path
from dashboard.history import read_provider_history


def _make_provider_db(path: Path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE metrics (id INTEGER PRIMARY KEY, sim_day INTEGER, product_id INTEGER, "
                 "product_name TEXT, stock_quantity INTEGER, price_tier1 REAL, orders_pending INTEGER, "
                 "orders_shipped INTEGER, orders_delivered INTEGER)")
    rows = [(1, 1, 1, "chip", 150, 12.0, 0, 0, 0),
            (2, 2, 1, "chip", 120, 12.0, 1, 0, 0),
            (3, 1, 2, "frame", 80, 30.0, 0, 0, 0)]
    conn.executemany("INSERT INTO metrics VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


def test_read_provider_history_series_and_peak(tmp_path):
    db = tmp_path / "provider.db"
    _make_provider_db(db)

    hist = read_provider_history(db)

    assert hist["series"]["stock"]["chip"] == [[1, 150], [2, 120]]
    assert hist["series"]["price"]["chip"] == [[1, 12.0], [2, 12.0]]
    assert hist["peak"]["chip"] == 150
    assert hist["peak"]["frame"] == 80


def test_read_provider_history_missing_db_is_graceful(tmp_path):
    hist = read_provider_history(tmp_path / "nope.db")
    assert hist == {"series": {}, "peak": {}}
