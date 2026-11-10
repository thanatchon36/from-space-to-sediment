"""Validation of verify_trace (paper, Section 9).

  Part A  network checks on the REAL Bang Pakong network (HydroRIVERS v1.0 extract):
          orientation inference, along-network distances vs an independent reference.
  Part B  Monte Carlo simulation: SYNTHETIC sites, factories, records and stations are
          generated on the real network topology; the pipeline is run unchanged and its
          outputs are compared with the known truth. No real site data are used, and no
          synthetic site locations are reported or mapped.

    fs2s network                        # Part A -> results/sim_out
    fs2s sim --scenario 0 --reps 150    # Part B, one scenario (0-3)
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

from . import verify_trace as fv
from .config import RESULTS_DIR, RIVERS_JSON

CRS = "EPSG:32647"
BP_MAIN = 41340295
B = {"cu": 20.0, "pb": 15.0, "sn": 2.0, "sb": 0.8, "cd": 0.20, "ni": 25.0, "zn": 60.0}
KAPPA = {"cu": 3.0, "pb": 4.0, "sn": 5.0, "sb": 5.0, "cd": 1.5, "ni": 0.3, "zn": 0.8}   # e-waste
GAMMA = {"cu": 3.0, "pb": 0.3, "sn": 0.0, "sb": 0.0, "cd": 3.0, "ni": 2.0, "zn": 2.0}   # confounder
LAMBDAS = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
ARGS = argparse.Namespace(tau=0.6, snap_ok_m=500.0, flood_thr=0.10, ratio_thr=1.5, evidence_rule="count")


def load_network(rivers_json=RIVERS_JSON):
    d = json.load(open(rivers_json))
    rec = [{"HYRIV_ID": r["id"], "NEXT_DOWN": r["down"], "q": r["q"], "len_km": r["len"],
            "geometry": LineString(r["c"])} for r in d["reaches"]
           if r["main"] == BP_MAIN and len(r["c"]) > 1]
    raw = gpd.GeoDataFrame(rec, crs="EPSG:4326")
    return raw, fv.RiverNetwork(raw, "HYRIV_ID", "NEXT_DOWN", CRS)


# ----------------------------------------------------------------------------- Part A
def network_checks(raw, net, rng, n_pairs=500):
    proj = raw.to_crs(CRS).set_index("HYRIV_ID")
    # (1) HydroRIVERS extract is digitised upstream -> downstream: flip must be False.
    agree = np.mean([not net.flip[r] for r in net.length])
    # (2) geometric length vs attribute length (simplified geometry is shorter)
    ratio = np.array([net.length[r] / (proj.loc[r, "len_km"] * 1000) for r in net.length
                      if proj.loc[r, "len_km"] > 0])
    # (3) random point pairs: pipeline distance vs distance along the merged path line,
    #     built from RAW coordinate order (independent of the inferred orientation).
    rids = np.array(list(net.length))
    prob = np.array([net.length[r] for r in rids]); prob = prob / prob.sum()
    rows, t_pipe = [], 0.0
    while len(rows) < n_pairs:
        r1 = int(rng.choice(rids, p=prob)); s1 = rng.uniform(0, net.length[r1])
        path, cur = [], r1
        while cur in net.length:
            path.append(cur); cur = net.nxt.get(cur, 0)
        r2 = path[rng.integers(len(path))]; s2 = rng.uniform(0, net.length[r2])
        P, Q = net.geom[r1].interpolate(s1), net.geom[r2].interpolate(s2)
        t0 = time.perf_counter()
        snaps = net.snap(gpd.GeoDataFrame(geometry=[P, Q], crs=CRS), 5.0)
        off = net.downstream_offsets(snaps[0], 1e12)
        d = off[snaps[1].rid] + snaps[1].pos
        t_pipe += time.perf_counter() - t0
        coords = []
        for r in path[: path.index(r2) + 1]:
            c = list(net.geom[r].coords)
            if coords and np.allclose(coords[-1], c[0]):
                c = c[1:]
            coords += c
        line = LineString(coords)
        d_ref = line.project(Q) - line.project(P)
        if d_ref < 0 or d < 0:
            continue
        rows.append({"d_pipeline_km": d / 1000, "d_reference_km": d_ref / 1000})
    pairs = pd.DataFrame(rows)
    err = (pairs["d_pipeline_km"] - pairs["d_reference_km"]).abs() * 1000
    # distance from each reach midpoint to the outlet (for mapping)
    dmid = {}
    for r in net.length:
        off = net.downstream_offsets(fv.Snap(r, net.length[r] / 2, 0.0), 1e12)
        last = list(off)[-1]
        dmid[r] = (off[last] + net.length[last]) / 1000
    summary = {"n_reaches": len(net.length), "total_length_km": sum(net.length.values()) / 1000,
               "orientation_agreement": agree, "length_ratio_median": float(np.median(ratio)),
               "length_ratio_p05": float(np.percentile(ratio, 5)),
               "length_ratio_p95": float(np.percentile(ratio, 95)),
               "pairs": len(pairs), "abs_err_m_median": float(err.median()),
               "abs_err_m_max": float(err.max()), "ms_per_pair": 1000 * t_pipe / len(pairs),
               "max_dist_to_outlet_km": max(dmid.values())}
    return summary, pairs, dmid


# ----------------------------------------------------------------------------- Part B
def place(net, rng, n, offset_fn):
    rids = np.array(list(net.length))
    w = np.array([net.length[r] for r in rids]); w = w / w.sum()
    pts, offs = [], []
    for r in rng.choice(rids, size=n, p=w):
        line = net.geom[int(r)]; s = rng.uniform(0, line.length)
        p = line.interpolate(s)
        a, b = line.interpolate(max(s - 5, 0)), line.interpolate(min(s + 5, line.length))
        dx, dy = b.x - a.x, b.y - a.y; nrm = np.hypot(dx, dy) or 1.0
        off = offset_fn(); side = rng.choice([-1.0, 1.0])
        pts.append(Point(p.x - side * off * dy / nrm, p.y + side * off * dx / nrm)); offs.append(off)
    return pts, np.array(offs)


def around(rng, pts, idx, dmin, dmax):
    out = []
    for i in idx:
        r, th = rng.uniform(dmin, dmax), rng.uniform(0, 2 * np.pi)
        out.append(Point(pts[i].x + r * np.cos(th), pts[i].y + r * np.sin(th)))
    return out


def min_dist(points, others):
    if not others:
        return np.full(len(points), np.inf)
    a = np.array([[p.x, p.y] for p in points]); b = np.array([[q.x, q.y] for q in others])
    return np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(-1)).min(1)


def replicate(net, rng, lam_true_km, pi_source, n_sites=60, n_st=25, n_conf=3, n_perm=99):
    lam_true = lam_true_km * 1000.0
    # --- candidate sites -------------------------------------------------------------
    pts, _ = place(net, rng, n_sites,
                   lambda: rng.uniform(30, 700) if rng.uniform() < 0.7 else rng.uniform(700, 2500))
    src = rng.uniform(size=n_sites) < pi_source
    score = np.where(src, rng.beta(5, 2, n_sites), rng.beta(2, 4, n_sites))
    A = rng.uniform(0.4, 1.0, n_sites)
    act = np.where(src, np.clip(A + rng.normal(0, 0.15, n_sites), 0.05, 1), rng.uniform(0.05, 0.4, n_sites))
    year = rng.integers(2018, 2025, n_sites)
    cands = gpd.GeoDataFrame({"site_id": [f"S{i:03d}" for i in range(n_sites)],
                              "screening_score": score, "activity_index": act,
                              "s_thermal": np.where(src, 0.7, 0.3), "s_pond": np.where(src, 0.6, 0.2),
                              "first_built_year": year}, geometry=pts, crs=CRS)
    truth_snaps = net.snap(cands, 5000.0)
    snapd = np.array([s.dist if s else np.inf for s in truth_snaps.values()])
    flood = np.where(snapd > 600, rng.uniform(size=n_sites) < 0.3, False)
    cands["flood_freq_max"] = np.where(flood, rng.uniform(0.12, 0.5, n_sites), rng.uniform(0, 0.08, n_sites))
    connected = (snapd <= 600) | flood

    # --- verification layers with known truth ------------------------------------------
    ids = rng.permutation(n_sites)
    lic, decoy, other, known, known_far, neg = (ids[:9], ids[9:12], ids[12:15], ids[15:21],
                                                ids[21:24], ids[24:27])
    fpts = around(rng, pts, lic, 50, 400) + around(rng, pts, decoy, 560, 900) + around(rng, pts, other, 50, 400)
    fcat = ["105"] * len(lic) + ["106(2)"] * len(decoy) + ["53(5)"] * len(other)
    fac = gpd.GeoDataFrame({"fac_id": [f"F{i}" for i in range(len(fpts))], "category": fcat},
                           geometry=fpts, crs=CRS)
    kpts = around(rng, pts, known, 100, 900) + around(rng, pts, known_far, 1100, 1600)
    kn = gpd.GeoDataFrame({"ref_id": [f"K{i}" for i in range(len(kpts))], "source_type": "news"},
                          geometry=kpts, crs=CRS)
    npts = around(rng, pts, neg, 50, 250)
    ng = gpd.GeoDataFrame({"neg_id": [f"N{i}" for i in range(len(npts))], "neg_type": "rice_mill"},
                          geometry=npts, crs=CRS)
    tgt = [p for p, c in zip(fpts, fcat) if c != "53(5)"]
    oth = [p for p, c in zip(fpts, fcat) if c == "53(5)"]
    truth_lic = min_dist(pts, tgt) <= 500
    truth_oth = (min_dist(pts, oth) <= 500) & ~truth_lic
    truth_known = min_dist(pts, kpts) <= 1000
    truth_neg = min_dist(pts, npts) <= 300

    cands = fv.registry_gap(cands, fac, 500.0)
    cands = fv.known_exclusion(cands, kn, 1000.0)
    cands = fv.hard_negative_filter(cands, ng, 300.0)
    cands = fv.assign_status(cands)
    flags_ok = {"licensed": np.mean(cands["is_licensed"].to_numpy(bool) == truth_lic),
                "other_category": np.mean(cands["licensed_other_category"].to_numpy(bool) == truth_oth),
                "known": np.mean(cands["is_previously_reported"].to_numpy(bool) == truth_known),
                "hard_negative": np.mean(cands["is_hard_negative"].to_numpy(bool) == truth_neg)}
    cands["p_i"], cands["a_i"] = cands["screening_score"], cands["activity_index"]

    # --- stations and the true contamination field -------------------------------------
    spts, _ = place(net, rng, n_st, lambda: rng.uniform(0, 40))
    st = gpd.GeoDataFrame({"station_id": [f"ST{j:02d}" for j in range(n_st)]}, geometry=spts, crs=CRS)
    st_snaps = net.snap(st, 5000.0)
    tp = fv.pair_distances(net, truth_snaps, st_snaps, 200_000.0)
    T = np.zeros(n_st); contrib = np.zeros((n_sites, n_st))
    for r in tp.itertuples():
        if src[r.from_idx] and connected[r.from_idx]:
            v = A[r.from_idx] * np.exp(-r.d_m / lam_true)
            T[r.to_idx] += v; contrib[r.from_idx, r.to_idx] = v
    cpts, _ = place(net, rng, n_conf, lambda: rng.uniform(20, 300))
    conf = gpd.GeoDataFrame(geometry=cpts, crs=CRS)
    cp = fv.pair_distances(net, net.snap(conf, 5000.0), st_snaps, 200_000.0)
    Ac = rng.uniform(0.5, 1.5, n_conf); K = np.zeros(n_st)
    for r in cp.itertuples():
        K[r.to_idx] += Ac[r.from_idx] * np.exp(-r.d_m / lam_true)
    clean = np.where((T < 1e-3) & (K < 1e-3))[0]
    ref = rng.choice(clean, size=min(5, len(clean)), replace=False) if len(clean) >= 3 else np.argsort(T + K)[:3]
    st["is_reference"] = np.isin(np.arange(n_st), ref)
    for m in B:
        samples = [B[m] * np.exp(rng.normal(0, 0.25, n_st)) * (1 + KAPPA[m] * T + GAMMA[m] * K)
                   for _ in range(2)]
        st[m] = np.median(np.vstack(samples), axis=0)
    st["al"] = 50000 * np.exp(rng.normal(0, 0.1, n_st))
    st = fv.marker_anomalies(st, list(B), 2.0, 2.0, 0.1)
    cores = []
    for j in range(n_st):
        if T[j] >= 0.2:
            dom = int(np.argmax(contrib[:, j]))
            cores.append({"station_id": f"ST{j:02d}", "onset_year": year[dom] + round(rng.normal(0.5, 1.0)),
                          "onset_year_sd": 1.5})
    legacy = [j for j in np.where((T < 0.2) & (K >= 0.2))[0][:3]]
    cores += [{"station_id": f"ST{j:02d}", "onset_year": int(rng.integers(2005, 2017)), "onset_year_sd": 1.5}
              for j in legacy]
    cores = pd.DataFrame(cores, columns=["station_id", "onset_year", "onset_year_sd"]).set_index("station_id")

    # --- the pipeline, unchanged --------------------------------------------------------
    s_snaps, j_snaps = net.snap(cands, 2000.0), net.snap(st, 2000.0)
    cands["snap_dist_m"] = [s.dist if s else np.nan for s in s_snaps.values()]
    down = fv.pair_distances(net, s_snaps, j_snaps, 50_000.0)
    up = fv.pair_distances(net, j_snaps, s_snaps, 50_000.0)
    src_mask = (~cands["is_hard_negative"].astype(bool)).to_numpy(float)
    lam, L, _, obs, p_perm = fv.select_lambda(down, cands, st, ["cu", "pb", "sb", "cd"], LAMBDAS,
                                              n_perm, rng, src_mask)
    ev = fv.site_evidence(cands, st, list(B), down, up, L, lam * 1000.0, cores, ARGS)

    # --- evaluation on unregistered candidates -------------------------------------------
    unreg = (cands["status"] == "unregistered_candidate").to_numpy()
    true_pos = src & connected
    near = np.zeros(n_sites, bool)
    for r in down.itertuples():
        if r.d_m <= min(50_000.0, 3 * lam_true):
            near[r.from_idx] = True
    attributable = true_pos & near
    lvl = ev["criteria_met"].to_numpy()
    c3 = ev["C3_geochemistry"].to_numpy(bool)
    has_down = ev["downstream_stations"].fillna("").astype(str).str.len().to_numpy() > 0
    conf_only = np.zeros(n_sites, bool)       # non-sources whose nearest downstream station is
    for i, g in down.sort_values("d_m").groupby("from_idx"):   # confounder-dominated
        j = int(g.iloc[0]["to_idx"])
        conf_only[i] = (K[j] >= 0.2) and (T[j] < 0.05)
    out = {"lam_true": lam_true_km, "pi": pi_source, "lam_sel": lam, "obs_rho": obs, "p_perm": p_perm,
           **{f"flag_acc_{k}": v for k, v in flags_ok.items()},
           "n_unreg": int(unreg.sum()), "n_true_unreg": int((true_pos & unreg).sum()),
           "n_attributable_unreg": int((attributable & unreg).sum())}
    for name, thr in (("possible", 2), ("probable", 3), ("attributed", 4)):
        pred = unreg & (lvl >= thr)
        out[f"{name}_n"] = int(pred.sum())
        out[f"{name}_tp"] = int((pred & true_pos).sum())
        out[f"{name}_tp_attr"] = int((pred & attributable).sum())
    sel = unreg & has_down
    out["c3_tp"] = int((sel & c3 & true_pos).sum()); out["c3_pos"] = int((sel & true_pos).sum())
    out["c3_fp"] = int((sel & c3 & ~src).sum()); out["c3_neg"] = int((sel & ~src).sum())
    out["c3_fp_conf"] = int((sel & c3 & ~src & conf_only).sum())
    out["c3_neg_conf"] = int((sel & ~src & conf_only).sum())
    # same rule but requiring C3 for "probable" (sensitivity variant)
    c1 = ev["C1_detection"].to_numpy(bool); c2 = ev["C2_connectivity"].to_numpy(bool)
    req = unreg & c3 & ((c1.astype(int) + c2.astype(int) + c3.astype(int)) >= 3)
    out["probable_c3req_n"] = int(req.sum()); out["probable_c3req_tp"] = int((req & true_pos).sum())
    out["probable_c3req_tp_attr"] = int((req & attributable).sum())
    return out


def run(scenario: int = -1, reps: int = 150, n_perm: int = 99, out=RESULTS_DIR, rivers_json=RIVERS_JSON):
    """scenario -1: network checks; 0-3: Monte Carlo scenario (resumes from an existing results file)."""
    out = Path(out); out.mkdir(exist_ok=True, parents=True)
    raw, net = load_network(rivers_json)
    if scenario < 0:
        rng = np.random.default_rng(20261109)
        summary, pairs, dmid = network_checks(raw, net, rng)
        json.dump(summary, open(out / "network_checks.json", "w"), indent=2)
        pairs.to_csv(out / "network_pairs.csv", index=False)
        pd.Series(dmid, name="d_outlet_km").rename_axis("HYRIV_ID").to_csv(out / "reach_dist_outlet.csv")
        print("network checks:", json.dumps(summary, indent=1))
        return out / "network_checks.json"
    lam_true, pi = ((3.0, 0.25), (8.0, 0.25), (20.0, 0.25), (8.0, 0.0))[scenario]
    path = out / f"sim_results_s{scenario}.csv"
    rows = pd.read_csv(path).to_dict("records") if path.exists() else []   # resume
    t0 = time.time()
    for k in range(len(rows), reps):
        rng = np.random.default_rng([20261109, scenario, k])              # one stream per replicate
        rows.append(dict(rep=k, **replicate(net, rng, lam_true, pi, n_perm=n_perm)))
        if (k + 1) % 25 == 0:
            pd.DataFrame(rows).to_csv(path, index=False)
            print(f"scenario {scenario}: {k + 1}/{reps} ({time.time() - t0:.0f} s)", flush=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"scenario {scenario} finished", flush=True)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reps", type=int, default=150)
    ap.add_argument("--n-perm", type=int, default=99)
    ap.add_argument("--out", default=str(RESULTS_DIR))
    ap.add_argument("--rivers-json", default=str(RIVERS_JSON), help="path to the HydroRIVERS extract rivers.json")
    ap.add_argument("--scenario", type=int, default=-1, help="-1 = network checks only; 0-3 = scenario")
    a = ap.parse_args(argv)
    run(a.scenario, a.reps, a.n_perm, a.out, a.rivers_json)


if __name__ == "__main__":
    main()
