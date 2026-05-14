from pathlib import Path
import json


def export_state(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2))


def import_state(path: Path) -> dict:
    return json.loads(path.read_text())
