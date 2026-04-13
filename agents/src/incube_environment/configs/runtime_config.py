import os
from pathlib import Path

import yaml

# When running in Docker, data is mounted at /data.
# When running locally, data is at <project_root>/data.
_DATA_DIR = os.environ.get(
    "DATA_DIR",
    str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data"),
)

MISSION_SPEC_PATH = Path(_DATA_DIR) / "mission_spec.yaml"

if MISSION_SPEC_PATH.exists():
    with open(MISSION_SPEC_PATH, "r") as f:
        prompt = f.read()
        mission_spec = yaml.safe_load(prompt)
else:
    mission_spec = {"Mission Plan": "Plan Something"}
    prompt = "{'Mission Plan': 'Plan something'}"
