"""State Management page for the simulation (Export/Import)."""

import streamlit as st
import json
import requests
from io import BytesIO

st.set_page_config(
    page_title="State Management | 3D Printer Factory Simulator",
    page_icon="💾",
    layout="wide",
)

API_BASE = "http://localhost:8000/api"


def export_state():
    """Call API to export full simulation state."""
    try:
        resp = requests.get(f"{API_BASE}/simulation/export")
        if resp.ok:
            return resp.json()
        else:
            st.error(f"Export failed: {resp.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return None


def import_state(data):
    """Call API to import full simulation state."""
    try:
        resp = requests.post(f"{API_BASE}/simulation/import", json=data)
        if resp.ok:
            return True, resp.json().get("message", "Success")
        else:
            return False, resp.text
    except Exception as e:
        return False, str(e)


def main():
    """Main state management page."""
    st.title("💾 State Management")
    st.caption("Save and load the entire simulation state, including inventory, orders, and event history.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📤 Export State")
        st.write("Download the current simulation state as a JSON file.")

        if st.button("Generate Export", use_container_width=True):
            data = export_state()
            if data:
                json_str = json.dumps(data, indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_str,
                    file_name=f"sim_state_day_{data.get('simulation_state', {}).get('current_day', 0)}.json",
                    mime="application/json",
                    use_container_width=True
                )
                st.success("Export generated successfully!")

    with col2:
        st.subheader("📥 Import State")
        st.write("Upload a previously exported JSON file to restore the simulation state.")
        st.warning("⚠️ Warning: Importing will overwrite ALL current simulation data.")

        uploaded_file = st.file_uploader("Choose a JSON file", type="json")

        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                st.info(f"Loaded file for Day {data.get('simulation_state', {}).get('current_day', 'Unknown')}")

                if st.button("🔥 Perform Import", use_container_width=True):
                    success, message = import_state(data)
                    if success:
                        st.success("Import successful! Go back to the dashboard to see changes.")
                        if st.button("Refresh App"):
                            st.rerun()
                    else:
                        st.error(f"Import failed: {message}")
            except Exception as e:
                st.error(f"Error parsing JSON: {e}")


if __name__ == "__main__":
    main()
