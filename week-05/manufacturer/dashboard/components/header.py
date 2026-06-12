"""Dashboard header — day counter strip and advance-day button."""
import streamlit as st


def _day_strip_html(day: int, date: str, capacity: int, username: str, role: str) -> str:
    return f"""
<div class="day-strip">
  <div>
    <div class="app-title">DGSI Production Simulator</div>
    <div class="app-subtitle">3D Printer Factory &mdash; {username} ({role})</div>
  </div>
  <div style="text-align:center">
    <div class="day-label">Simulation Day</div>
    <div class="day-number">{day:04d}</div>
    <div class="day-date">{date}</div>
  </div>
  <div style="text-align:right">
    <div class="day-label">Capacity</div>
    <div class="day-number" style="font-size:20px">{capacity}</div>
    <div class="day-date">units / day</div>
  </div>
</div>"""


def render_header(get_fn, post_fn, user: dict) -> None:
    """Render the top header strip.

    Calls st.rerun() if the day was advanced.

    Args:
        get_fn: Callable(path) -> dict
        post_fn: Callable(path, **kwargs) -> dict
        user: dict with keys 'username', 'role'
    """
    username = user.get("username", "?")
    role = user.get("role", "?")

    # Fetch sim status
    try:
        status = get_fn("/api/simulation/status")
        day = status.get("current_day", 1)
        date = status.get("current_date", "—")
        capacity = status.get("capacity_per_day", 250)
    except Exception:
        day, date, capacity = 1, "—", 250

    # Top row: title strip + logout
    col_strip, col_actions = st.columns([5, 1])

    with col_strip:
        st.markdown(_day_strip_html(day, date, capacity, username, role), unsafe_allow_html=True)

    with col_actions:
        st.write("")  # vertical alignment spacer
        if st.button("Logout", use_container_width=True, key="header_logout"):
            st.session_state.clear()
            st.rerun()

    # Advance day — prominent, full-width in its own row
    advance_col, status_col = st.columns([2, 5])
    with advance_col:
        if st.button("NEXT SHIFT", type="primary", use_container_width=True, key="advance_day_btn"):
            with st.spinner("Running simulation day..."):
                result = post_fn("/api/simulation/advance")
            if result:
                ev_count = len(result.get("events_generated", []))
                st.session_state["last_advance"] = result
                st.success(
                    f"Day {result['previous_day']} → {result['new_day']} — {ev_count} events generated"
                )
                st.rerun()
    with status_col:
        last = st.session_state.get("last_advance")
        if last:
            ev = last.get("events_generated", [])
            demand = sum(1 for e in ev if e.get("type") == "demand_generated")
            produced = next(
                (e.get("produced_today", 0) for e in ev if e.get("type") == "production_summary"),
                0,
            )
            st.markdown(
                f'<p style="color:#64748B;font-size:11px;margin-top:18px">'
                f'Last shift: {demand} demand events &nbsp;|&nbsp; {produced} units produced'
                f'</p>',
                unsafe_allow_html=True,
            )
