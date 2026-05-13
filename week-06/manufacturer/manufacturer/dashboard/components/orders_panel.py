"""Manufacturing orders panel — compact rows with status badges."""
import streamlit as st


_STATUS_CSS_CLASS = {
    "pending": "status-pending",
    "released": "status-released",
    "waiting_materials": "status-waiting_materials",
    "completed": "status-completed",
    "cancelled": "status-cancelled",
    "failed": "status-failed",
}


def _counts_html(all_orders: list) -> str:
    pending = sum(1 for o in all_orders if o["status"] == "pending")
    released = sum(1 for o in all_orders if o["status"] == "released")
    waiting = sum(1 for o in all_orders if o["status"] == "waiting_materials")
    completed = sum(1 for o in all_orders if o["status"] == "completed")
    chips = [
        (pending, "#F59E0B", "PENDING"),
        (released, "#3B82F6", "RELEASED"),
        (waiting, "#EF4444", "WAITING"),
        (completed, "#22C55E", "DONE"),
    ]
    inner = "".join(
        f'<div class="order-count-chip">'
        f'<span class="count-number" style="color:{color}">{n}</span>'
        f'<span class="count-label">{label}</span>'
        f'</div>'
        for n, color, label in chips
    )
    return f'<div class="order-counts">{inner}</div>'


def _order_row_html(order: dict) -> str:
    qty = float(order["quantity_needed"])
    produced = float(order["quantity_produced"])
    prog_pct = (produced / max(qty, 1)) * 100
    status_class = _STATUS_CSS_CLASS.get(order["status"], "status-cancelled")
    return f"""
<div class="order-row">
  <span class="order-id">#{order['id']:04d}</span>
  <span class="order-model">{order['product_model']}</span>
  <span class="order-qty">{qty:.0f}</span>
  <div class="order-prog-track">
    <div class="order-prog-fill" style="width:{prog_pct:.0f}%"></div>
  </div>
  <span class="order-status {status_class}">{order['status']}</span>
</div>"""


def render_orders_panel(get_fn, post_fn) -> None:
    """Render the manufacturing orders panel.

    Args:
        get_fn: Callable(path) -> dict
        post_fn: Callable(path, **kwargs) -> dict
    """
    st.subheader("Orders")

    try:
        all_orders = get_fn("/api/orders")
    except Exception as e:
        st.error(f"Orders unavailable: {e}")
        return

    # Count strip
    st.markdown(_counts_html(all_orders), unsafe_allow_html=True)

    # Filter
    status_filter = st.selectbox(
        "Filter",
        ["all", "pending", "released", "waiting_materials", "completed", "cancelled"],
        key="order_status_filter",
        label_visibility="collapsed",
    )

    orders = (
        all_orders if status_filter == "all"
        else [o for o in all_orders if o["status"] == status_filter]
    )

    if not orders:
        st.markdown(
            '<p style="color:#475569;font-size:12px;padding:16px 0">No orders match this filter.</p>',
            unsafe_allow_html=True,
        )
        return

    for order in orders[:30]:
        st.markdown(_order_row_html(order), unsafe_allow_html=True)

        # Action buttons for actionable orders only
        if order["status"] == "pending":
            c1, c2 = st.columns(2)
            if c1.button("Release", key=f"rel_{order['id']}", use_container_width=True):
                result = post_fn(f"/api/orders/{order['id']}/release")
                if result:
                    st.success("Released")
                    st.rerun()
            if c2.button("Cancel", key=f"can_{order['id']}", use_container_width=True):
                result = post_fn(f"/api/orders/{order['id']}/cancel")
                if result:
                    st.rerun()
