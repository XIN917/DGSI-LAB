"""Event Log viewing page for the simulation."""

import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="Event Logs | 3D Printer Factory Simulator",
    page_icon="📜",
    layout="wide",
)

API_BASE = "http://localhost:8000/api"


def get_events(limit: int = 500, day: int = None, category: str = None, event_type: str = None) -> list:
    """Get events with filtering."""
    params = {"limit": limit}
    if day:
        params["day"] = day
    if category and category != "All":
        params["category"] = category
    if event_type and event_type != "All":
        params["event_type"] = event_type

    try:
        resp = requests.get(f"{API_BASE}/events", params=params)
        return resp.json() if resp.ok else []
    except Exception as e:
        st.error(f"Failed to fetch events: {e}")
        return []


def main():
    """Main log viewer page."""
    st.title("📜 Event History")
    st.caption("Complete historical record of all simulation events.")

    # Sidebar filters
    st.sidebar.header("Filters")

    col1, col2, col3 = st.sidebar.columns([1, 1, 1])

    # Category filter
    categories = ["All", "SYSTEM", "DEMAND", "PRODUCTION", "PURCHASING", "INVENTORY"]
    selected_category = st.sidebar.selectbox("Category", categories)

    # Day filter
    selected_day = st.sidebar.number_input("Filter by Day (0 for all)", min_value=0, value=0)

    # Event type filter
    event_types = ["All", "ORDER_CREATED", "ORDER_RELEASED", "ORDER_COMPLETED", "PO_CREATED", "PO_DELIVERED", "INVENTORY_SHORTAGE", "DAY_ADVANCED", "SIMULATION_RESET"]
    selected_event_type = st.sidebar.selectbox("Event Type", event_types)

    # Limit filter
    limit = st.sidebar.slider("Max Events", min_value=10, max_value=1000, value=200)

    # Load events
    day_val = selected_day if selected_day > 0 else None
    events = get_events(limit=limit, day=day_val, category=selected_category, event_type=selected_event_type)

    if not events:
        st.info("No events match the selected filters.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(events)

    # Format the dataframe for display
    display_df = df[["day", "event_type", "category", "description"]].copy()
    display_df.columns = ["Day", "Event Type", "Category", "Description"]

    # Show data table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Day": st.column_config.NumberColumn(width="small"),
            "Event Type": st.column_config.TextColumn(width="medium"),
            "Category": st.column_config.TextColumn(width="small"),
            "Description": st.column_config.TextColumn(width="large"),
        }
    )

    # Detailed view
    st.divider()
    st.subheader("Event Details")
    selected_event_idx = st.selectbox("Select an event to view full details:", range(len(events)), format_func=lambda i: f"Day {events[i]['day']} - {events[i]['event_type']}: {events[i]['description'][:50]}...")

    if selected_event_idx is not None:
        event = events[selected_event_idx]
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write(f"**ID:** {event['id']}")
            st.write(f"**Day:** {event['day']}")
            st.write(f"**Timestamp:** {event['timestamp']:.4f}")
            st.write(f"**Category:** {event['category']}")
            st.write(f"**Type:** {event['event_type']}")
        with col2:
            st.write("**Description:**")
            st.write(event["description"])
            if event.get("details"):
                st.write("**Details:**")
                st.json(event["details"])


if __name__ == "__main__":
    main()
