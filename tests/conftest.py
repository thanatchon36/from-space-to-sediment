import pandas as pd
import pytest

from from_space_to_sediment import cli


@pytest.fixture(scope="session")
def selftest(tmp_path_factory):
    """Synthetic data set + one full run of verify_trace (the README self-test, `fs2s selftest`)."""
    d = tmp_path_factory.mktemp("synthetic")
    assert cli.main(["selftest", "--out", str(d)]) == 0
    return d / "out"


@pytest.fixture(scope="session")
def screened(selftest):
    return pd.read_csv(selftest / "01_candidates_screened_RESTRICTED.csv").set_index("site_id")
