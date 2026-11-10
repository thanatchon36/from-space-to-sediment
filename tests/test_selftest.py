"""End-to-end run on the synthetic data set: every branch named in the README ends where it should."""
import pandas as pd


def test_true_source_is_attributed(screened):
    row = screened.loc["S_A"]
    assert row["status"] == "unregistered_candidate"
    assert row["evidence_level"] == "attributed"


def test_registry_and_record_checks(screened):
    assert screened.loc["S_C", "status"] == "licensed_101_105_106"
    assert screened.loc["S_D", "status"] == "known_seed"
    assert screened.loc["S_E", "status"] == "hard_negative"
    assert bool(screened.loc["S_G", "registry_mismatch_review"])


def test_only_unregistered_sites_reach_attributed(screened):
    attributed = screened[screened["evidence_level"] == "attributed"]
    assert set(attributed["status"]) == {"unregistered_candidate"}


def test_lambda_search_selects_one_scale(selftest):
    tab = pd.read_csv(selftest / "05_lambda_search.csv")
    assert tab.loc[tab["selected"], "lambda_km"].nunique() == 1


def test_public_outputs_hold_no_coordinates(selftest):
    """Exact site locations go only into *_RESTRICTED* files (README, Responsible use).
    04_station_loading.csv keeps station coordinates: sampling points, not suspected sites."""
    for f in selftest.glob("*.csv"):
        if "_RESTRICTED" in f.name or f.name == "04_station_loading.csv":
            continue
        cols = {c.lower() for c in pd.read_csv(f, nrows=0).columns}
        assert not cols & {"lon", "lat", "longitude", "latitude", "geometry"}, f.name
    assert not [f for f in selftest.glob("*.geojson") if "_RESTRICTED" not in f.name]
