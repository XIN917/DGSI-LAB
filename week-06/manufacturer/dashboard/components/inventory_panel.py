"""Inventory panel — bin-level fill bar visualization."""
import streamlit as st


def _bin_color(pct: float) -> tuple[str, str]:
    """Return (fill_hex, badge_class) based on stock percentage."""
    if pct < 0.20:
        return "#EF4444", "badge-critical"
    if pct < 0.50:
        return "#F59E0B", "badge-low"
    return "#22C55E", "badge-ok"


def _badge_text(pct: float) -> str:
    if pct < 0.20:
        return "CRIT"
    if pct < 0.50:
        return "LOW"
    return "OK"


def _warehouse_bar_html(usage_pct: float) -> str:
    capped = min(usage_pct, 100.0)
    color = "#EF4444" if usage_pct > 90 else "#F59E0B" if usage_pct > 70 else "#22C55E"
    return f"""
<div class="warehouse-header">
  <span class="warehouse-label">Warehouse Capacity</span>
  <span class="warehouse-pct">{usage_pct:.1f}%</span>
</div>
<div class="warehouse-track">
  <div class="warehouse-fill" style="width:{capped:.1f}%;background:{color}"></div>
</div>"""


def _bin_row_html(item: dict) -> str:
    # Use the max_capacity from the database/API
    max_cap = float(item.get("max_capacity", 250.0))
    qty = float(item["quantity"])
    avail = float(item["available"])
    
    # Percentage for the visual bar (how full is this "bin" compared to its capacity)
    visual_pct = min(avail / max_cap, 1.0)
    
    # Color logic and badge based on capacity
    # Critical if < 20% of capacity, Low if < 50%
    fill_color, badge_class = _bin_color(visual_pct)
    badge = _badge_text(visual_pct)
    
    bar_width = f"{max(visual_pct * 100, 1):.1f}%"
    name = item["product_name"].replace("_", " ")
    return f"""
<div class="bin-row">
  <span class="bin-name" title="{item['product_name']}">{name}</span>
  <div class="bin-track">
    <div class="bin-fill" style="width:{bar_width};background:{fill_color}"></div>
  </div>
  <span class="bin-avail">{avail:.0f}</span>
  <span class="bin-total">/{max_cap:.0f}</span>
  <span class="bin-badge {badge_class}">{badge}</span>
</div>"""


def render_inventory_panel(get_fn, post_fn) -> None:
    """Render the inventory panel.

    Args:
        get_fn: Callable(path) -> dict  — authenticated API GET
        post_fn: Callable(path, **kwargs) -> dict  — authenticated API POST
    """
    st.subheader("Inventory")

    try:
        inv_data = get_fn("/api/inventory")
    except Exception as e:
        st.error(f"Inventory unavailable: {e}")
        return

    usage_pct = float(inv_data.get("usage_pct", 0))
    items = sorted(inv_data.get("items", []), key=lambda x: x["product_name"])

    # Warehouse capacity bar
    st.markdown(_warehouse_bar_html(usage_pct), unsafe_allow_html=True)

    # Bin rows
    rows_html = '<div class="bins-container">'
    for item in items:
        rows_html += _bin_row_html(item)
    rows_html += "</div>"
    st.markdown(rows_html, unsafe_allow_html=True)

    # Manual adjust (in expander, preserves existing API)
    with st.expander("Adjust inventory", expanded=False):
        product_names = [i["product_name"] for i in items]
        with st.form("adjust_inv_form"):
            product = st.selectbox("Product", product_names, key="adj_product")
            new_qty = st.number_input("New quantity", min_value=0, value=100, step=10)
            reason = st.text_input("Reason (optional)")
            submitted = st.form_submit_button("Apply")
        if submitted:
            result = post_fn(
                "/api/inventory/adjust",
                json={"product_name": product, "new_quantity": new_qty, "reason": reason or None},
            )
            if result:
                st.success(f"{product} → {new_qty}")
                st.rerun()
