"""Streamlit dashboard launcher."""

import subprocess
import sys


def run_ui():
    """Launch the Streamlit UI."""
    subprocess.call(
        [sys.executable, "-m", "streamlit", "run", "ui/dashboard.py"]
    )


if __name__ == "__main__":
    run_ui()
