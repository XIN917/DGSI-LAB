import sys
from pathlib import Path

WEEK8_DIR = Path(__file__).resolve().parents[1]
if str(WEEK8_DIR) not in sys.path:
    sys.path.insert(0, str(WEEK8_DIR))
