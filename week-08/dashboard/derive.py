"""Canonical supply-chain derivations.

Single source of truth for every *computed* tier field shown on the dashboard.
Both the live path (`collector.py`, fed by HTTP JSON) and the archive path
(`app.py`, fed by SQLite rows) call these — so the two views can never drift
apart again. Inputs are plain lists/dicts of order or part records; each record
only needs the keys named below (`status`, `quantity`, `name`).

Historically these were re-implemented independently in each path, which is what
produced the in-transit / stalled / backlog / duplicate-part mismatches.
"""

# Retailer purchase-order statuses (orders the retailer placed with the manufacturer)
PO_DELIVERED = "delivered"
PO_CANCELLED = "cancelled"
PO_WAITING = "waiting_materials"  # stuck at manufacturer for lack of materials
PO_TERMINAL = (PO_DELIVERED, PO_CANCELLED)

# Customer-order statuses (orders end customers placed with the retailer)
CO_BACKORDERED = "backordered"


def _status(rec: dict) -> str:
    return rec.get("status") or ""


def _qty(rec: dict) -> int:
    return rec.get("quantity") or 0


def retailer_in_transit(purchase_orders) -> int:
    """Units genuinely moving toward the retailer — placed/shipped, not yet delivered.

    Excludes ``waiting_materials`` (those are stalled, not in transit) and terminal states.
    """
    return sum(_qty(o) for o in (purchase_orders or [])
               if _status(o) not in PO_TERMINAL and _status(o) != PO_WAITING)


def retailer_stalled(purchase_orders) -> int:
    """Units the retailer ordered that are stuck at the manufacturer for lack of materials."""
    return sum(_qty(o) for o in (purchase_orders or []) if _status(o) == PO_WAITING)


def count_backordered(customer_orders) -> int:
    """Number of customer orders currently backordered at the retailer."""
    return sum(1 for o in (customer_orders or []) if _status(o) == CO_BACKORDERED)


def dedup_parts(parts: dict, finished_names) -> dict:
    """Drop part entries that share a name with a finished good.

    Finished SKUs (P3D-Classic / P3D-Pro) also appear as BOM keys in the
    manufacturer's ``parts_stock_json``; without this they render twice.
    """
    finished = set(finished_names)
    return {k: v for k, v in (parts or {}).items() if k not in finished}
