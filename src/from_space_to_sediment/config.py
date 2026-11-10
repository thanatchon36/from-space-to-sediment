"""Repository paths. Everything is resolved from the repository root, so commands work from any directory."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"                  # third-party map data (make data), not in git
RIVERS_JSON = DATA_DIR / "rivers.json"    # HydroRIVERS v1.0 extract from github.com/oadtz/waterways
RESULTS_DIR = ROOT / "results" / "sim_out"
PAPER_DIR = ROOT / "paper"
DOCS_DIR = ROOT / "docs"
SYNTHETIC_DIR = ROOT / "tests" / "synthetic"

REPO_URL = "https://github.com/thanatchon36/from-space-to-sediment"
PAPER_URL = "https://thanatchon36.github.io/from-space-to-sediment/paper/"
DATA_URL = "https://huggingface.co/datasets/thanatchon36/from-space-to-sediment"
