"""Actions panel — new order / new PO forms + pending PO list."""
import json
import streamlit as st


def _po_list_html(pos: list) -> str:
    if not pos:
        return '<p style="color:#475569;font-size:11px">No pending POs.</p>'
    rows = []
    for po in pos[:8]:
        due = (po.get("expected_delivery") or "")[:10]
        status_color = "#F59E0B" if po["status"] == "partial" else "#3B82F6"
        rows.append(
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:5px 0;border-bottom:1px solid rgba(51,65,85,0.3);'
            f'font-size:11px;">'
            f'<span style="color:#94A3B8;font-family:\'Fira Code\',monospace">#{po["id"]:04d}</span>'
            f'<span style="color:#CBD5E1;flex:1;margin:0 8px">{po["product_name"]}</span>'
            f'<span style="color:#64748B;font-family:\'Fira Code\',monospace">'
            f'{po["quantity_ordered"]:.0f}</span>'
            f'<span style="color:{status_color};margin-left:8px;font-size:9px;'
            f'font-weight:700">{po["status"].upper()}</span>'
            f'<span style="color:#334155;margin-left:8px">{due}</span>'
            f'</div>'
        )
    return "".join(rows)


def render_actions_panel(get_fn, post_fn) -> None:
    """Render the right actions panel.

    Args:
        get_fn: Callable(path) -> dict
        post_fn: Callable(path, **kwargs) -> dict
    """
    st.subheader("Actions")

    # ── New manufacturing order ──
    with st.expander("New Order", expanded=True):
        try:
            models_data = get_fn("/api/config/models")
            model_ids = [m["id"] for m in models_data]
        except Exception:
            model_ids = ["P3D-Classic", "P3D-Pro"]

        with st.form("new_order_form"):
            selected_model = st.selectbox("Model", model_ids)
            quantity = st.number_input("Qty", min_value=1, value=10, step=1)
            submitted = st.form_submit_button("Create Order", use_container_width=True)

        if submitted:
            result = post_fn(
                "/api/orders",
                json={"product_model": selected_model, "quantity": quantity},
            )
            if result:
                st.success(f"Order #{result['id']} created")
                st.rerun()

    # ── New purchase order ──
    with st.expander("New Purchase Order", expanded=False):
        try:
            config_data = get_fn("/api/config")
            suppliers = config_data.get("suppliers", [])
            supplier_map = {s["name"]: s for s in suppliers}
        except Exception:
            suppliers, supplier_map = [], {}

        if not suppliers:
            st.markdown('<p style="color:#475569;font-size:11px">No suppliers configured.</p>',
                        unsafe_allow_html=True)
        else:
            # We move selectboxes OUTSIDE the form to enable reactivity (dependent dropdowns)
            supplier_name = st.selectbox("Supplier", list(supplier_map.keys()))
            supplier = supplier_map.get(supplier_name, {})
            product_options = [p["product_name"] for p in supplier.get("products", [])]
            selected_product = st.selectbox("Product", product_options) if product_options else None
            
            # Now the form only handles the quantity and submission
            with st.form("new_po_form"):
                po_qty = st.number_input("Qty", min_value=1, value=100, step=10)

                # Live pricing preview
                if selected_product:
                    matching = [p for p in supplier.get("products", [])
                                if p["product_name"] == selected_product]
                    if matching:
                        prod = matching[0]
                        tiers = prod.get("discount_tiers", [])
                        applicable = [t for t in sorted(tiers, key=lambda x: x["min_qty"])
                                      if po_qty >= t["min_qty"]]
                        discount = applicable[-1]["discount_pct"] if applicable else 0
                        unit = prod["base_unit_cost"] * (1 - discount / 100)
                        total = unit * po_qty
                        st.markdown(
                            f'<div style="background:rgba(245,158,11,0.08);border:1px solid '
                            f'rgba(245,158,11,0.2);border-radius:4px;padding:8px;font-size:11px;'
                            f'font-family:\'Fira Code\',monospace;margin:4px 0">'
                            f'${unit:.2f}/unit &nbsp;({discount}% off) &nbsp;&rarr; &nbsp;'
                            f'<strong style="color:#F59E0B">${total:,.2f}</strong></div>',
                            unsafe_allow_html=True,
                        )

                submit_po = st.form_submit_button("Place Order", use_container_width=True)

            if submit_po and selected_product:
                result = post_fn(
                    "/api/purchase-orders",
                    json={
                        "supplier_id": supplier["id"],
                        "product_name": selected_product,
                        "quantity": po_qty,
                    },
                )
                if result:
                    st.success(f"PO #{result['id']} — due {result['expected_delivery'][:10]}")
                    st.rerun()

    # ── Pending POs ──
    st.subheader("Purchase Orders")
    try:
        all_pos = get_fn("/api/purchase-orders")
        pending_pos = [p for p in all_pos if p["status"] in ("pending", "partial")]
    except Exception:
        pending_pos = []

    st.markdown(_po_list_html(pending_pos), unsafe_allow_html=True)

    # ── Import / Export ──
    st.divider()
    with st.expander("Import / Export", expanded=False):
        col_exp, col_imp = st.columns(2)
        with col_exp:
            if st.button("Export State", use_container_width=True):
                try:
                    state = get_fn("/api/export/full-state")
                    st.download_button(
                        "Download JSON",
                        data=json.dumps(state, indent=2),
                        file_name="simulation_state.json",
                        mime="application/json",
                    )
                except Exception as e:
                    st.error(f"Export failed: {e}")
        with col_imp:
            uploaded = st.file_uploader("Import JSON", type=["json"], label_visibility="collapsed")
            if uploaded and st.button("Import", use_container_width=True):
                data = json.load(uploaded)
                result = post_fn("/api/import/full-state", json=data)
                if result:
                    st.success("Imported")
                    st.rerun()
