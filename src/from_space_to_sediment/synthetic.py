"""Synthetic end-to-end test data (not real data) that exercises every branch of verify_trace:
licensed site, known seed, hard negative, registry mismatch, a site far from any channel,
paired upstream/downstream stations, reference stations, '<DL' values, reversed reach
geometries, labels for calibration and one dated core.

    fs2s synthetic --out tests/synthetic
    fs2s selftest                       # synthetic data + verify_trace in one step
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString

X0, Y0 = Transformer.from_crs("EPSG:4326", "EPSG:32647", always_xy=True).transform(101.40, 13.90)
inv = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True)


def ll(x, y):
    """Local metres (relative to the origin) -> lon, lat."""
    return inv.transform(X0 + x, Y0 + y)


def generate(out: Path) -> Path:
    """Write the synthetic tables and rivers.geojson into out; returns out."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    # --- river network: main stem flows west; two tributaries ----------------------
    reaches = [  # id, next, local vertices (two are deliberately digitised upstream-ward)
        (1, 2, [(20000, 0), (15000, 200), (10000, 0)]),
        (2, 3, [(0, 0), (5000, -300), (10000, 0)]),                 # reversed
        (3, 0, [(0, 0), (-7000, -900), (-15000, -2000)]),
        (4, 2, [(12000, 9000), (11000, 4500), (10000, 0)]),         # tributary T1 (receives site S_A)
        (5, 3, [(0, 0), (1500, -4500), (2000, -9000)]),             # reversed; clean reference T2
    ]
    rows = []
    for rid, nxt, pts in reaches:
        rows.append({"HYRIV_ID": rid, "NEXT_DOWN": nxt,
                     "geometry": LineString([ll(x, y) for x, y in pts])})
    gpd.GeoDataFrame(rows, crs="EPSG:4326").to_file(out / "rivers.geojson", driver="GeoJSON")

    # --- candidates (as exported by the GEE script) --------------------------------
    cands = [  # site_id, x, y, score, activity, s_thermal, s_pond, first_built_year
        ("S_A", 11200, 6000, 0.86, 0.80, 0.9, 0.8, 2019),   # unregistered, upstream of D1
        ("S_B", 15000, 500, 0.71, 0.60, 0.6, 0.3, 2020),    # unregistered on main stem
        ("S_C", 5000, 400, 0.80, 0.70, 0.7, 0.5, 2018),     # licensed (category 105)
        ("S_D", -5000, -1000, 0.75, 0.60, 0.5, 0.5, 2018),  # previously reported
        ("S_E", 3000, -250, 0.65, 0.40, 0.6, 0.2, 2021),    # next to a rice mill
        ("S_F", 7000, 7500, 0.90, 0.90, 0.9, 0.9, 2022),    # far from any mapped channel
        ("S_G", -8000, -1300, 0.68, 0.50, 0.7, 0.6, 2023),  # near a cold-storage factory (mismatch)
        ("S_H", 17000, -600, 0.30, 0.20, 0.1, 0.1, 2024),   # low score
    ]
    c = []
    for sid, x, y, sc, act, th, pd_, fy in cands:
        lon, lat = ll(x, y)
        c.append({"site_id": sid, "lon": lon, "lat": lat, "area_m2": 4000, "screening_score": sc,
                  "activity_index": act, "s_struct": 0.8, "s_thermal": th, "s_ntl": 0.5, "s_pond": pd_,
                  "proxies": "struct;thermal;" + ("pond_colour;" if pd_ >= 0.5 else ""),
                  "first_built_year": fy, "flood_freq_max": 0.25 if sid == "S_F" else 0.02})
    # 40 filler sites (far from channels) whose verification labels drive the calibration test
    fill_rng = np.random.default_rng(3)
    fill_scores = fill_rng.uniform(0, 1, 40)
    for i, sc in enumerate(fill_scores):
        lon, lat = ll(26000 + 150 * i, 21000)
        c.append({"site_id": f"L{i:02d}", "lon": lon, "lat": lat, "area_m2": 2500,
                  "screening_score": round(float(sc), 3), "activity_index": 0.3, "s_struct": 0.6,
                  "s_thermal": 0.2, "s_ntl": 0.0, "s_pond": 0.2, "proxies": "struct;",
                  "first_built_year": 2021, "flood_freq_max": 0.0})
    pd.DataFrame(c).to_csv(out / "candidates.csv", index=False)

    # --- registry, known sites, hard negatives -------------------------------------
    fac = [("F001", "105(1)", 5150, 520), ("F002", "53(5) cold storage", -8150, -1200),
           ("F003", "106", 30000, 30000)]
    pd.DataFrame([{"fac_id": f, "fac_name": f"Factory {f}", "category": cat, "lon": ll(x, y)[0],
                   "lat": ll(x, y)[1], "status": "active"} for f, cat, x, y in fac]).to_csv(
        out / "diw_factories.csv", index=False)
    pd.DataFrame([{"ref_id": "K001", "lon": ll(-5100, -900)[0], "lat": ll(-5100, -900)[1],
                   "source_type": "news", "source_ref": "synthetic", "date_reported": "2021-05-01",
                   "precision_m": 300}]).to_csv(out / "known_sites.csv", index=False)
    pd.DataFrame([{"neg_id": "N001", "neg_type": "rice_mill", "lon": ll(3050, -200)[0],
                   "lat": ll(3050, -200)[1], "buffer_m": 300}]).to_csv(out / "hard_negatives.csv", index=False)

    # --- stations: two samples each; elevated markers below S_A / S_B ---------------
    bg = {"cu": 20, "pb": 15, "sn": 2.0, "sb": 0.8, "cd": 0.20, "ni": 25, "zn": 60, "al": 50000}
    st = [  # station_id, x, y, multiplier, is_reference
        ("U1", 18000, 100, 1.0, False), ("U2", 11800, 8000, 1.0, False),
        ("D1", 8000, -100, 5.0, False), ("D2", -6000, -800, 2.6, False), ("D3", -12000, -1600, 1.9, False),
        ("R1", 1900, -8000, 1.0, True), ("R2", 1500, -4500, 1.1, True), ("R3", 800, -2000, 0.9, True),
    ]
    rng = np.random.default_rng(1)
    rows = []
    for sid, x, y, mult, ref in st:
        lon, lat = ll(x, y)
        for k, date in enumerate(["2025-03-10", "2025-09-15"]):
            r = {"station_id": sid, "lon": lon, "lat": lat, "sample_date": date, "matrix": "sediment",
                 "unit": "mg/kg", "is_reference": ref}
            for m, v in bg.items():
                f = 1.0 if m in ("ni", "zn", "al") else mult
                r[m] = round(v * f * rng.lognormal(0, 0.08), 3)
            if sid == "R3" and k == 0:
                r["cd"] = "<0.1"                       # below detection limit -> DL/2
            rows.append(r)
    pd.DataFrame(rows).to_csv(out / "stations.csv", index=False)

    # --- verification labels (synthetic) and one dated core ------------------------
    lab_rng = np.random.default_rng(4)
    labels = (lab_rng.uniform(0, 1, 40) < fill_scores).astype(int)
    lab = pd.DataFrame({"site_id": [f"L{i:02d}" for i in range(40)], "verified": labels})
    lab = pd.concat([lab, pd.DataFrame({"site_id": ["S_A", "S_D"], "verified": [1, 1]})])
    lab.to_csv(out / "labels.csv", index=False)
    pd.DataFrame([{"station_id": "D1", "onset_year": 2020, "onset_year_sd": 1.5}]).to_csv(
        out / "cores.csv", index=False)
    return out
