"""Chart components for the dashboard."""

import streamlit as st
import matplotlib.pyplot as plt
from collections import defaultdict


def render_inventory_chart(inventory_data: list):
    """Render inventory levels chart."""
    if not inventory_data:
        st.info("No inventory data to display.")
        return

    fig, ax = plt.subplots(figsize=(8, 4))

    materials = [item.get("material_type", "Unknown") for item in inventory_data]
    quantities = [item.get("current_quantity", 0) for item in inventory_data]

    colors = ["#4CAF50" if q > 0 else "#FF5252" for q in quantities]

    ax.bar(materials, quantities, color=colors)
    ax.set_ylabel("Quantity")
    ax.set_title("Current Inventory Levels")
    ax.tick_params(axis="x", rotation=45)

    # Add value labels on bars
    for i, (mat, qty) in enumerate(zip(materials, quantities)):
        ax.text(i, qty + max(quantities) * 0.02, f"{qty:.0f}", ha="center", fontsize=9)

    st.pyplot(fig)


def render_shortage_chart(shortages: list):
    """Render shortage severity chart."""
    if not shortages:
        return

    fig, ax = plt.subplots(figsize=(8, 3))

    materials = [s.get("material", "Unknown")[:12] for s in shortages]
    shortfalls = [s.get("shortage", 0) for s in shortages]

    ax.barh(materials, shortfalls, color="#FF5252")
    ax.set_xlabel("Shortfall Quantity")
    ax.set_title("Material Shortages")

    # Add value labels
    for i, val in enumerate(shortfalls):
        ax.text(val + max(shortfalls) * 0.02, i, f"-{val:.0f}", va="center", fontsize=9)

    st.pyplot(fig)


def render_event_timeline(events: list, max_days: int = 30):
    """Render event timeline chart."""
    if not events:
        st.info("No events to display.")
        return

    # Limit to recent events
    recent_events = [e for e in events if e.get("day", 0) <= max_days][:50]

    if not recent_events:
        st.info("No recent events.")
        return

    fig, ax = plt.subplots(figsize=(10, 4))

    days = [e.get("day", 0) for e in recent_events]
    types = [e.get("event_type", "UNKNOWN") for e in recent_events]

    # Color by category
    category_colors = {
        "DEMAND": "#2196F3",
        "PRODUCTION": "#4CAF50",
        "PURCHASING": "#FF9800",
        "INVENTORY": "#9C27B0",
        "SYSTEM": "#607D8B",
    }

    colors = [category_colors.get(e.get("category", "SYSTEM"), "#607D8B") for e in recent_events]

    # Scatter plot of events
    y_positions = range(len(recent_events))
    ax.scatter(days, y_positions, c=colors, alpha=0.7, s=50)

    ax.set_xlabel("Day")
    ax.set_ylabel("Events")
    ax.set_title(f"Event Timeline (Last {max_days} Days)")
    ax.set_yticks([])

    # Custom legend
    legend_handles = []
    for cat, color in category_colors.items():
        legend_handles.append(plt.Line2D([0], [0], marker="o", color="w",
                                          markerfacecolor=color, markersize=8, label=cat))
    ax.legend(handles=legend_handles, loc="upper right", bbox_to_anchor=(1.2, 1))

    st.pyplot(fig)


def render_production_summary(completed_orders: list):
    """Render production summary chart."""
    if not completed_orders:
        st.info("No completed orders yet.")
        return

    # Group by model
    model_counts = defaultdict(int)
    for order in completed_orders:
        model = order.get("printer_model_id", "Unknown")
        model_counts[model] += order.get("quantity", 0)

    fig, ax = plt.subplots(figsize=(8, 4))

    models = list(model_counts.keys())
    totals = list(model_counts.values())

    colors = plt.cm.Set3(range(len(models)))

    ax.bar(models, totals, color=colors)
    ax.set_ylabel("Total Units Produced")
    ax.set_title("Production Output by Model")
    ax.tick_params(axis="x", rotation=45)

    # Add value labels
    for i, (model, total) in enumerate(zip(models, totals)):
        ax.text(i, total + max(totals) * 0.02, f"{total}", ha="center", fontsize=9)

    st.pyplot(fig)
