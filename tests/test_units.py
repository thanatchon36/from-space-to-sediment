import geopandas as gpd
import numpy as np
from shapely.geometry import LineString

import fs2s_verify_trace as fv


def test_parse_conc_handles_detection_limits():
    assert fv.parse_conc("<0.4") == 0.2
    assert fv.parse_conc("1,250") == 1250.0
    assert fv.parse_conc("12.5") == 12.5
    assert np.isnan(fv.parse_conc("n.d."))
    assert np.isnan(fv.parse_conc(None))


def _network():
    # reach 1 flows into 2, 2 into 3 (outlet); reach 2 is digitised upstream-ward on purpose
    reaches = [
        (1, 2, [(2000, 0), (1000, 0)]),
        (2, 3, [(0, 0), (1000, 0)]),
        (3, 0, [(0, 0), (-1000, 0)]),
    ]
    gdf = gpd.GeoDataFrame(
        {"HYRIV_ID": [r[0] for r in reaches], "NEXT_DOWN": [r[1] for r in reaches]},
        geometry=[LineString(r[2]) for r in reaches], crs="EPSG:32647",
    )
    return fv.RiverNetwork(gdf, "HYRIV_ID", "NEXT_DOWN", "EPSG:32647")


def test_reversed_reach_is_detected():
    net = _network()
    assert net.flip == {1: False, 2: True, 3: False}


def test_along_network_distance_runs_downstream_only():
    net = _network()
    up = fv.Snap(1, 500.0, 0.0)     # 500 m below the head of reach 1
    down = fv.Snap(3, 250.0, 0.0)   # 250 m into reach 3
    pairs = fv.pair_distances(net, {"a": up}, {"b": down}, 10_000)
    assert pairs["d_m"].tolist() == [500.0 + 1000.0 + 250.0]
    assert fv.pair_distances(net, {"b": down}, {"a": up}, 10_000).empty
