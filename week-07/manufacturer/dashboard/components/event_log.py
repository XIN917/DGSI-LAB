"""Event log panel — timeline rows with colored type chips."""
import streamlit as st
from typing import Optional

_EVENT_COLORS = {
    "day_advanced":         ("#818CF8", "rgba(129,140,248,0.15)"),
    "demand_generated":     ("#94A3B8", "rgba(148,163,184,0.12)"),
    "demand_batch":         ("#94A3B8", "rgba(148,163,184,0.12)"),
    "order_released":       ("#4ADE80", "rgba(74,222,128,0.15)"),
    "order_cancelled":      ("#F87171", "rgba(248,113,113,0.15)"),
    "order_completed":      ("#4ADE80", "rgba(74,222,128,0.15)"),
    "order_created_manual": ("#60A5FA", "rgba(96,165,250,0.15)"),
    "material_consumed":    ("#FB923C", "rgba(251,146,60,0.15)"),
    "po_created":           ("#60A5FA", "rgba(96,165,250,0.15)"),
    "po_arrived":           ("#4ADE80", "rgba(74,222,128,0.15)"),
    "po_partial_delivery":  ("#FB923C", "rgba(251,146,60,0.15)"),
    "po_cancelled":         ("#F87171", "rgba(248,113,113,0.15)"),
    "inventory_snapshot":   ("#94A3B8", "rgba(148,163,184,0.12)"),
    "inventory_adjustment": ("#FB923C", "rgba(251,146,60,0.15)"),
}
_DEFAULT_COLOR = ("#94A3B8", "rgba(148,163,184,0.12)")


def _event_row_html(event: dict) -> str:
    color, bg = _EVENT_COLORS.get(event["event_type"], _DEFAULT_COLOR)
    date = (event.get("event_date") or "")[:10]
    detail = (event.get("details") or "")[:70]
    etype = event["event_type"]
    return (
        f'<div class="event-row">'
        f'<span class="event-date">{date}</span>'
        f'<span class="event-type-chip" style="color:{color};background:{bg}">{etype}</span>'
        f'<span class="event-detail">{detail}</span>'
        f'</div>'
    )


def render_event_log(get_fn, page_size: int = 25, event_type: Optional[str] = None) -> None:
    """Render the event log section.

    Args:
        get_fn: Callable(path, params=...) -> dict
        page_size: How many events to show
        event_type: Optional filter
    """
    st.subheader("Event Log")

    col_filter, col_limit = st.columns([3, 1])
    with col_filter:
        etype_input = st.text_input(
            "Filter by type",
            value=event_type or "",
            placeholder="e.g. order_released",
            label_visibility="collapsed",
            key="event_type_filter",
        )
    with col_limit:
        limit = st.number_input("Show", min_value=5, max_value=200, value=page_size, step=10,
                                label_visibility="collapsed", key="event_limit")

    try:
        params: dict = {"page_size": int(limit)}
        if etype_input:
            params["event_type"] = etype_input
        data = get_fn("/api/events", params=params)
        events = data.get("items", [])
        total = data.get("total", 0)
    except Exception as e:
        st.error(f"Event log unavailable: {e}")
        return

    if not events:
        st.markdown(
            '<p style="color:var(--fg-muted);font-size:12px;padding:8px 0">No events yet. Advance the simulation to generate events.</p>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<p style="color:var(--fg-muted);font-size:10px;margin-bottom:6px">'
        f'Showing {len(events)} of {total} events</p>',
        unsafe_allow_html=True,
    )

    rows_html = "".join(_event_row_html(e) for e in events)
    st.markdown(rows_html, unsafe_allow_html=True)
