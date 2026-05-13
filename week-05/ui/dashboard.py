"""Main Streamlit dashboard."""

import streamlit as st
import requests
from ui.components.charts import render_inventory_chart, render_shortage_chart, render_event_timeline, render_production_summary

st.set_page_config(
    page_title="3D Printer Factory Simulator",
    page_icon="🖨️",
    layout="wide",
)

API_BASE = "http://localhost:8000/api"


def get_session() -> requests.Session:
    """Get a requests session for API calls."""
    return requests.Session()


def get_simulation_status(session: requests.Session) -> dict:
    """Get current simulation status."""
    try:
        resp = session.get(f"{API_BASE}/simulation/status")
        return resp.json() if resp.ok else {"current_day": 1, "running": False}
    except Exception:
        return {"current_day": 1, "running": False}


def advance_day(session: requests.Session) -> dict:
    """Advance simulation by one day."""
    try:
        resp = session.post(f"{API_BASE}/simulation/advance")
        return resp.json() if resp.ok else {}
    except Exception as e:
        return {"error": str(e)}


def reset_simulation(session: requests.Session) -> dict:
    """Reset simulation to day 1."""
    try:
        resp = session.post(f"{API_BASE}/simulation/reset")
        return resp.json() if resp.ok else {}
    except Exception as e:
        return {"error": str(e)}


def get_events(session: requests.Session, limit: int = 100) -> list:
    """Get recent events."""
    try:
        resp = session.get(f"{API_BASE}/events", params={"limit": limit})
        return resp.json() if resp.ok else []
    except Exception:
        return []


def get_orders(session: requests.Session) -> list:
    """Get all manufacturing orders."""
    try:
        resp = session.get(f"{API_BASE}/orders")
        return resp.json() if resp.ok else []
    except Exception:
        return []


def get_inventory(session: requests.Session) -> list:
    """Get current inventory levels."""
    try:
        resp = session.get(f"{API_BASE}/inventory")
        return resp.json() if resp.ok else []
    except Exception:
        return []


def get_suppliers(session: requests.Session) -> list:
    """Get all suppliers."""
    try:
        resp = session.get(f"{API_BASE}/purchase-orders/suppliers")
        return resp.json() if resp.ok else []
    except Exception:
        return []


def get_production_stats(session: requests.Session) -> dict:
    """Get production statistics."""
    try:
        resp = session.get(f"{API_BASE}/simulation/production-stats")
        return resp.json() if resp.ok else {}
    except Exception:
        return {}


def get_shortages(session: requests.Session) -> list:
    """Get current material shortages."""
    try:
        resp = session.get(f"{API_BASE}/simulation/shortages")
        return resp.json().get("shortages", []) if resp.ok else []
    except Exception:
        return []


def release_order(session: requests.Session, order_id: str, day: int) -> dict:
    """Release an order to production."""
    try:
        resp = session.put(f"{API_BASE}/orders/{order_id}/release", json={"released_day": day})
        return resp.json() if resp.ok else {"error": "Failed to release"}
    except Exception as e:
        return {"error": str(e)}


def cancel_order(session: requests.Session, order_id: str) -> dict:
    """Cancel a pending order."""
    try:
        resp = session.put(f"{API_BASE}/orders/{order_id}/cancel")
        return resp.json() if resp.ok else {"error": "Failed to cancel"}
    except Exception as e:
        return {"error": str(e)}


def render_header(session: requests.Session) -> tuple[int, bool]:
    """Render header with day display and controls. Returns (day, running)."""
    st.header("🖨️ 3D Printer Factory Simulator")

    col1, col2, col3 = st.columns([2, 1, 1])

    status = get_simulation_status(session)
    current_day = status.get("current_day", 1)
    running = status.get("running", False)

    with col1:
        st.metric("📅 Simulated Day", current_day)

    with col2:
        if st.button("▶️ Advance Day", use_container_width=True):
            result = advance_day(session)
            if "error" not in result:
                st.success(f"Advanced to day {result.get('new_day', current_day + 1)}")
                st.rerun()
            else:
                st.error(f"Error: {result.get('error')}")

    with col3:
        if st.button("↻ Reset", use_container_width=True):
            if st.session_state.get("confirm_reset"):
                reset_simulation(session)
                st.success("Simulation reset to day 1")
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("Click again to confirm")

    return current_day, running


def render_orders_panel(session: requests.Session, current_day: int):
    """Render orders panel with BOM breakdown."""
    st.subheader("📋 Orders Panel")

    orders = get_orders(session)
    pending_orders = [o for o in orders if o.get("status") == "PENDING"]
    released_orders = [o for o in orders if o.get("status") == "RELEASED"]
    completed_orders = [o for o in orders if o.get("status") == "COMPLETED"]

    st.caption(f"Pending: {len(pending_orders)} | Released: {len(released_orders)} | Completed: {len(completed_orders)}")

    if not pending_orders and not released_orders:
        st.info("No orders yet. Advance days to generate demand.")
        return

    # Pending orders
    if pending_orders:
        st.markdown("**Pending Orders**")
        for order in pending_orders:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{order['printer_model_id']}** x{order['quantity']}")
                    st.caption(f"Created day {order['created_day']}")
                with col2:
                    if st.button("Release", key=f"release_{order['id']}", use_container_width=True):
                        result = release_order(session, order["id"], current_day)
                        if result.get("success"):
                            st.success("Order released!")
                            st.rerun()
                        else:
                            errors = result.get("error", {})
                            if "shortages" in errors:
                                for mat, info in errors["shortages"].items():
                                    st.error(f"{mat}: need {info['required']}, have {info['available']}")
                            else:
                                st.error(errors.get("error", "Failed to release"))

    # Released orders (in progress)
    if released_orders:
        st.markdown("**In Production**")
        for order in released_orders[:5]:  # Show last 5
            st.caption(f"✅ {order['printer_model_id']} x{order['quantity']} (released day {order.get('released_day', '?')})")

    # Completed orders counter
    if completed_orders:
        st.metric("✅ Total Completed", len(completed_orders))


def render_inventory_panel(session: requests.Session, current_day: int):
    """Render inventory panel with shortage warnings."""
    st.subheader("💾 Inventory Panel")

    inventory = get_inventory(session)
    shortages = get_shortages(session)

    # Warehouse capacity
    cap_result = get_production_stats(session)
    daily_capacity = cap_result.get("daily_capacity", {})

    if inventory:
        st.markdown("**Current Stock**")
        for item in inventory:
            qty = item.get("current_quantity", 0)
            mat = item.get("material_type", "Unknown")
            st.write(f"{mat}: **{qty:.0f}**")

    # Shortage warnings
    if shortages:
        st.markdown("⚠️ **Shortages Detected**")
        for s in shortages:
            mat = s.get("material", "Unknown")
            needed = s.get("required", 0)
            have = s.get("available", 0)
            st.error(f"{mat}: need {needed:.0f}, have {have:.0f} (short by {s.get('shortage', 0):.0f})")
    else:
        st.success("✅ No material shortages")


def render_purchasing_panel(session: requests.Session, current_day: int):
    """Render purchasing panel for placing orders."""
    st.subheader("🛒 Purchasing Panel")

    suppliers = get_suppliers(session)

    if not suppliers:
        st.info("No suppliers configured.")
        return

    # Supplier selection
    supplier_ids = [s["id"] for s in suppliers]
    selected_supplier = st.selectbox("Supplier", supplier_ids, format_func=lambda x: next((s["name"] for s in suppliers if s["id"] == x), x))

    # Get products from selected supplier
    try:
        resp = session.get(f"{API_BASE}/purchase-orders/suppliers/{selected_supplier}/products")
        products = resp.json().get("products", []) if resp.ok else []
    except Exception:
        products = []

    if not products:
        st.info("No products available from this supplier.")
        return

    # Product selection
    product_map = {p["material_type"]: p for p in products}
    selected_material = st.selectbox("Material", list(product_map.keys()))

    if selected_material:
        product = product_map[selected_material]
        min_qty = product.get("min_order_qty", 10)
        price = product.get("price_per_unit", 0)

        st.caption(f"Min order: {min_qty} | Price: ${price:.2f}/unit | Packaging: {product.get('packaging', 'N/A')}")

        # Quantity input
        quantity = st.number_input("Quantity", min_value=min_qty, value=min_qty, step=min_qty)

        # Cost estimate
        total_cost = quantity * price
        st.metric("Estimated Cost", f"${total_cost:.2f}")

        # Expected delivery
        supplier_data = next((s for s in suppliers if s["id"] == selected_supplier), {})
        lead_time = supplier_data.get("lead_time_days", 3)
        expected_arrival = current_day + lead_time
        st.caption(f"Expected arrival: Day {expected_arrival} (lead time: {lead_time} days)")

        if st.button("📦 Create Purchase Order", use_container_width=True):
            import uuid
            po_id = f"po_{uuid.uuid4().hex[:8]}"

            try:
                resp = session.post(f"{API_BASE}/purchase-orders", json={
                    "id": po_id,
                    "supplier_id": selected_supplier,
                    "material_type": selected_material,
                    "quantity": quantity,
                    "order_day": current_day,
                    "expected_arrival": expected_arrival,
                })
                if resp.ok:
                    st.success(f"PO {po_id} created! Arrives day {expected_arrival}")
                    st.rerun()
                else:
                    st.error(f"Failed: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")


def render_production_panel(session: requests.Session, current_day: int):
    """Render production panel showing capacity usage."""
    st.subheader("🏭 Production Panel")

    stats = get_production_stats(session)

    col1, col2, col3 = st.columns(3)

    with col1:
        pending = stats.get("pending_orders", 0)
        st.metric("📋 Pending Orders", pending)

    with col2:
        released = stats.get("released_orders", 0)
        st.metric("⚙️ In Production", released)

    with col3:
        completed = stats.get("completed_today", 0)
        st.metric("✅ Completed Today", completed)

    # Capacity info
    st.markdown("**Daily Capacity**")
    daily_capacity = stats.get("daily_capacity", {})
    for model, capacity in daily_capacity.items():
        st.write(f"{model}: {capacity} units/day")

    # Queue quantity
    queue_qty = stats.get("queue_quantity", 0)
    if queue_qty > 0:
        st.caption(f"Total in queue: {queue_qty} units")


def main():
    """Main dashboard entry point."""
    session = get_session()

    # Header with controls
    current_day, running = render_header(session)

    st.divider()

    # Three column layout for panels
    col1, col2, col3 = st.columns(3)

    with col1:
        render_orders_panel(session, current_day)
        st.empty()  # Spacer
        render_production_panel(session, current_day)

    with col2:
        render_inventory_panel(session, current_day)

    with col3:
        render_purchasing_panel(session, current_day)

    # Charts section
    st.divider()
    st.subheader("📊 Charts & Analytics")

    inv_col1, inv_col2 = st.columns(2)

    with inv_col1:
        st.markdown("**Inventory Levels**")
        inventory = get_inventory(session)
        render_inventory_chart(inventory)

    with inv_col2:
        shortages = get_shortages(session)
        if shortages:
            st.markdown("**Shortages**")
            render_shortage_chart(shortages)

    # Event timeline
    events = get_events(session, limit=50)
    if events:
        st.markdown("**Recent Events**")
        render_event_timeline(events, max_days=min(current_day + 5, 30))

    # Production summary
    all_orders = get_orders(session)
    completed = [o for o in all_orders if o.get("status") == "COMPLETED"]
    if completed:
        st.markdown("**Production Summary**")
        render_production_summary(completed)


if __name__ == "__main__":
    main()
