import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "pipeline"
sys.path.insert(0, str(PIPELINE))


@pytest.fixture(scope="session")
def selftest(tmp_path_factory):
    """Synthetic data set + one full run of fs2s_verify_trace.py (the README self-test)."""
    d = tmp_path_factory.mktemp("synthetic")
    subprocess.run([sys.executable, str(PIPELINE / "make_synthetic_test.py"), str(d)], check=True,
                   capture_output=True)
    out = d / "out"
    subprocess.run(
        [sys.executable, str(PIPELINE / "fs2s_verify_trace.py"),
         "--candidates", d / "candidates.csv", "--factories", d / "diw_factories.csv",
         "--known", d / "known_sites.csv", "--negatives", d / "hard_negatives.csv",
         "--labels", d / "labels.csv", "--rivers", d / "rivers.geojson",
         "--stations", d / "stations.csv", "--matrix", "sediment", "--cores", d / "cores.csv",
         "--outdir", out, "--n-perm", "199"],
        check=True, capture_output=True,
    )
    return out


@pytest.fixture(scope="session")
def screened(selftest):
    return pd.read_csv(selftest / "01_candidates_screened_RESTRICTED.csv").set_index("site_id")
