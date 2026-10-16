import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR_ENVIRONMENT_VARIABLE = "RABU_DATA_DIR"


def get_data_dir() -> Path:
    configured_path = os.environ.get(DATA_DIR_ENVIRONMENT_VARIABLE)
    data_dir = Path(configured_path).expanduser() if configured_path else DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir.resolve()
