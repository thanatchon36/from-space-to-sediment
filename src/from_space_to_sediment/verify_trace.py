"""
From Space to Sediment - Module 1 verification and Module 3 downstream linkage.

Input   candidate sites exported by fs2s_module1_screening.js (Google Earth Engine)
        plus local tables (DIW factory registry, known sites, stations, rivers).

Steps   1  Registry gap analysis: DIW factories of categories 101/105/106 within
           --license-buffer-m (default 500 m)  -> is_licensed
        2  Known-site exclusion: news / enforcement / NGO records within
           --known-buffer-m (default 1 km)      -> is_previously_reported
        3  Hard-negative filtering: rice and sugar mills, landfills, livestock farms
        4  Optional isotonic calibration of the screening score with verified labels
        5  Hydrological linkage on a vector river network (HydroRIVERS or
           MERIT-Basins): along-network distance d_ij from site i to station j
        6  Upstream e-waste loading index (paper, Eq. 2)
               L_j = sum_i p_i * a_i * exp(-d_ij / lambda)
           with lambda chosen by Spearman association with marker anomalies and a
           permutation test that accounts for choosing lambda
        7  Evidence criteria C1-C4 (paper, Section 8) and the table of
           "High-Probability Unregistered Candidate Sites"

Outputs RESTRICTED tables contain coordinates; the PUBLIC table is aggregated to a
        grid. All results are screening outputs, not findings of illegality.

Example
    fs2s verify \
        --candidates bangpakong_candidates.csv --factories diw_factories.csv \
        --known known_sites.csv --negatives hard_negatives.csv \
        --rivers HydroRIVERS_v10_as.shp --stations stations.csv --matrix sediment \
        --admin subdistricts.geojson --outdir out_bangpakong

"""
from __future__ import annotations

import argparse
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import stats
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge

LOG = logging.getLogger("fs2s")

CAT_PATTERN = re.compile(r"(?<!\d)(101|105|106)(?!\d)")   # DIW factory categories
MARKERS_ALL = ["cu", "pb", "sn", "sb", "cd", "ni", "zn", "pbde_total", "pcddf_teq"]
NORMALISERS = ("al", "fe")                                # for enrichment factors
RIVER_FORMATS = {"hydrorivers": ("HYRIV_ID", "NEXT_DOWN"),
                 "meritbasins": ("COMID", "NextDownID")}
TRUE_STRINGS = {"1", "true", "t", "yes", "y"}


# ============================================================================
# Generic I/O helpers
# ============================================================================
def read_table(path: str, required: list[str], name: str) -> pd.DataFrame:
    """Read a CSV, lower-case its column names and check required columns."""
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"[{name}] missing required column(s) {missing} in {path}")
    return df


def to_points(df: pd.DataFrame, crs: str, name: str) -> gpd.GeoDataFrame:
    """Build projected points from lon/lat columns (WGS 84), dropping bad rows."""
    df = df.copy()
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    bad = (df["lon"].isna() | df["lat"].isna()
           | ~df["lon"].between(95, 110) | ~df["lat"].between(4, 22))
    if bad.any():
        LOG.warning("[%s] dropped %d row(s) with missing or out-of-region coordinates",
                    name, int(bad.sum()))
    df = df.loc[~bad].reset_index(drop=True)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]),
                           crs="EPSG:4326")
    return gdf.to_crs(crs)


def parse_conc(value) -> float:
    """Parse a concentration. Values reported as '<DL' are set to DL/2."""
    if pd.isna(value):
        return np.nan
    text = str(value).strip().replace(",", "")
    if text.startswith("<"):
        try:
            return float(text[1:]) / 2.0
        except ValueError:
            return np.nan
    try:
        return float(text)
    except ValueError:
        return np.nan


def as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin(TRUE_STRINGS)


def col(df: pd.DataFrame, name: str, default=np.nan) -> pd.Series:
    """Column if present, otherwise a constant series."""
    if name in df.columns:
        return df[name]
    return pd.Series(default, index=df.index)


def nearest(left: gpd.GeoDataFrame, right: gpd.GeoDataFrame, cols: list[str]) -> pd.DataFrame:
    """Nearest right feature for every left row (ties resolved to the first)."""
    j = gpd.sjoin_nearest(left[["geometry"]], right[cols + ["geometry"]], how="left",
                          distance_col="_dist_m")
    return j[~j.index.duplicated(keep="first")]


def within_radius(left: gpd.GeoDataFrame, right: gpd.GeoDataFrame, radius, cols: list[str]) -> pd.DataFrame:
    """For every left point, the nearest right point lying within that right point's radius.
    Uses exact point-to-point distances; buffered polygons are only a coarse pre-filter,
    because polygonal buffers slightly under-cover the true circle."""
    out = pd.DataFrame(index=left.index, columns=cols + ["_dist_m"], dtype=object)
    if right.empty or left.empty:
        return out
    zones = right[cols + ["geometry"]].copy()
    zones["_r"] = np.broadcast_to(np.asarray(radius, dtype=float), (len(right),))
    zones["_rid"] = np.arange(len(right))
    zones["geometry"] = right.geometry.buffer(zones["_r"] * 1.01 + 1.0)
    j = gpd.sjoin(left[["geometry"]], zones, how="inner", predicate="within")
    if j.empty:
        return out
    ctr = right.geometry.iloc[j["_rid"].to_numpy()]
    d = left.geometry.loc[j.index].distance(gpd.GeoSeries(ctr.values, index=j.index, crs=left.crs), align=False)
    j = j.assign(_dist_m=d.to_numpy())
    j = j[j["_dist_m"] <= j["_r"]].sort_values("_dist_m")
    j = j[~j.index.duplicated(keep="first")]
    out.loc[j.index, cols + ["_dist_m"]] = j[cols + ["_dist_m"]].to_numpy()
    return out


# ============================================================================
# Step 0 - candidates
# ============================================================================
def load_candidates(path: str, crs: str) -> gpd.GeoDataFrame:
    df = read_table(path, ["site_id", "lon", "lat"], "candidates")
    df["site_id"] = df["site_id"].astype(str)
    if df["site_id"].duplicated().any():
        raise SystemExit("[candidates] site_id values must be unique")
    if "screening_score" not in df.columns:
        LOG.warning("[candidates] no screening_score column; using 0.5 for every site")
        df["screening_score"] = 0.5
    df["screening_score"] = pd.to_numeric(df["screening_score"], errors="coerce").fillna(0).clip(0, 1)
    if "activity_index" not in df.columns:
        df["activity_index"] = 1.0
    df["activity_index"] = pd.to_numeric(df["activity_index"], errors="coerce").fillna(0.1).clip(0.05, 1)
    return to_points(df, crs, "candidates")


# ============================================================================
# Step 1 - registry gap analysis (DIW factory registry)
# ============================================================================
def registry_gap(cands: gpd.GeoDataFrame, fac: gpd.GeoDataFrame, buffer_m: float) -> gpd.GeoDataFrame:
    fac = fac.copy()
    fac["fac_id"] = fac["fac_id"].astype(str)
    fac["category"] = fac["category"].astype(str)
    fac["is_target"] = fac["category"].map(lambda v: bool(CAT_PATTERN.search(v)))
    out = cands.copy()
    for label, sub in (("target", fac[fac["is_target"]]), ("other", fac[~fac["is_target"]])):
        if sub.empty:
            out[f"nearest_{label}_fac_m"] = np.nan
            out[f"nearest_{label}_fac_id"] = None
            out[f"nearest_{label}_fac_cat"] = None
            continue
        nn = nearest(out, sub, ["fac_id", "category"])
        out[f"nearest_{label}_fac_m"] = nn["_dist_m"].round(1)
        out[f"nearest_{label}_fac_id"] = nn["fac_id"]
        out[f"nearest_{label}_fac_cat"] = nn["category"]
    out["is_licensed"] = out["nearest_target_fac_m"].le(buffer_m)
    # a registered factory of ANOTHER category nearby: possible mis-classified licence
    out["licensed_other_category"] = out["nearest_other_fac_m"].le(buffer_m) & ~out["is_licensed"]
    return out


# ============================================================================
# Step 2 - known-site exclusion (news, enforcement, NGO, PCD records)
# ============================================================================
def known_exclusion(cands: gpd.GeoDataFrame, known: gpd.GeoDataFrame, buffer_m: float) -> gpd.GeoDataFrame:
    known = known.copy()
    if "ref_id" not in known.columns:
        known["ref_id"] = [f"K{i:04d}" for i in range(len(known))]
    known["ref_id"] = known["ref_id"].astype(str)
    if "source_type" not in known.columns:
        known["source_type"] = "unspecified"
    precision = pd.to_numeric(col(known, "precision_m"), errors="coerce").fillna(0.0)
    known["radius_m"] = np.maximum(buffer_m, precision.to_numpy())   # coarse geocodes widen the zone
    hit = within_radius(cands, known, known["radius_m"].to_numpy(), ["ref_id", "source_type"])
    out = cands.copy()
    out["is_previously_reported"] = hit["ref_id"].notna()
    out["known_ref_id"] = hit["ref_id"]
    out["known_source_type"] = hit["source_type"]
    out["nearest_known_m"] = nearest(cands, known, ["ref_id"])["_dist_m"].round(1)
    return out


# ============================================================================
# Step 3 - hard negatives (rice/sugar mills, landfills, livestock farms, ...)
# ============================================================================
def hard_negative_filter(cands: gpd.GeoDataFrame, neg: gpd.GeoDataFrame, buffer_m: float) -> gpd.GeoDataFrame:
    neg = neg.copy()
    if "neg_id" not in neg.columns:
        neg["neg_id"] = [f"N{i:04d}" for i in range(len(neg))]
    if "neg_type" not in neg.columns:
        neg["neg_type"] = "unspecified"
    radius = pd.to_numeric(col(neg, "buffer_m"), errors="coerce").fillna(buffer_m)
    hit = within_radius(cands, neg, radius.to_numpy(), ["neg_id", "neg_type"])
    out = cands.copy()
    out["is_hard_negative"] = hit["neg_id"].notna()
    out["hard_negative_type"] = hit["neg_type"]
    return out


def assign_status(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Priority: known seed > licensed 101/105/106 > hard negative > unregistered."""
    status = np.full(len(df), "unregistered_candidate", dtype=object)
    status[df["is_hard_negative"].fillna(False).to_numpy(bool)] = "hard_negative"
    status[df["is_licensed"].fillna(False).to_numpy(bool)] = "licensed_101_105_106"
    status[df["is_previously_reported"].fillna(False).to_numpy(bool)] = "known_seed"
    df["status"] = status
    strong_signal = (pd.to_numeric(col(df, "s_thermal", 0), errors="coerce").fillna(0).ge(0.5)
                     | pd.to_numeric(col(df, "s_pond", 0), errors="coerce").fillna(0).ge(0.5))
    df["registry_mismatch_review"] = ((df["status"] == "unregistered_candidate")
                                      & df["licensed_other_category"].fillna(False).astype(bool)
                                      & strong_signal)
    return df


# ============================================================================
# Step 4 - optional isotonic calibration (pool-adjacent-violators)
# ============================================================================
def pav_fit(scores: np.ndarray, labels: np.ndarray):
    order = np.argsort(scores, kind="mergesort")
    x, y = np.asarray(scores, float)[order], np.asarray(labels, float)[order]
    vals, wts, xmax = [], [], []
    for xi, yi in zip(x, y):
        vals.append(yi); wts.append(1.0); xmax.append(xi)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            w = wts[-2] + wts[-1]
            v = (vals[-2] * wts[-2] + vals[-1] * wts[-1]) / w
            vals[-2:], wts[-2:], xmax[-2:] = [v], [w], [xmax[-1]]
    return np.asarray(xmax), np.asarray(vals)


def pav_predict(model, s: np.ndarray) -> np.ndarray:
    xmax, vals = model
    idx = np.clip(np.searchsorted(xmax, s, side="left"), 0, len(vals) - 1)
    return vals[idx]


def calibrate(cands: gpd.GeoDataFrame, labels_path: str) -> gpd.GeoDataFrame:
    lab = read_table(labels_path, ["site_id", "verified"], "labels")
    lab["site_id"] = lab["site_id"].astype(str)
    lab["verified"] = pd.to_numeric(lab["verified"], errors="coerce")
    m = cands[["site_id", "screening_score"]].merge(lab[["site_id", "verified"]], on="site_id").dropna()
    if len(m) < 20 or m["verified"].nunique() < 2:
        LOG.warning("[labels] %d usable labels (need >= 20 with both classes); calibration skipped", len(m))
        return cands
    model = pav_fit(m["screening_score"].to_numpy(), m["verified"].to_numpy())
    cands["p_i"] = pav_predict(model, cands["screening_score"].to_numpy())
    cands["p_source"] = "isotonic calibration on verified labels"
    brier_raw = np.mean((m["screening_score"] - m["verified"]) ** 2)
    brier_cal = np.mean((pav_predict(model, m["screening_score"].to_numpy()) - m["verified"]) ** 2)
    LOG.info("[labels] isotonic calibration on %d labels; in-sample Brier %.3f -> %.3f "
             "(use cross-validation before reporting)", len(m), brier_raw, brier_cal)
    return cands


# ============================================================================
# Step 5 - river network and along-network distances
# ============================================================================
@dataclass
class Snap:
    rid: int          # reach id
    pos: float        # metres from the upstream end of the reach
    dist: float       # snapping distance in metres


def _as_line(geom):
    if isinstance(geom, MultiLineString):
        merged = linemerge(geom)
        if isinstance(merged, MultiLineString):
            merged = max(merged.geoms, key=lambda g: g.length)
        return merged
    return geom


class RiverNetwork:
    """Directed reach network (id -> next downstream id) with oriented geometries."""

    def __init__(self, gdf: gpd.GeoDataFrame, id_col: str, next_col: str, crs: str):
        missing = [c for c in (id_col, next_col) if c not in gdf.columns]
        if missing:
            raise SystemExit(f"[rivers] missing column(s) {missing}; set --river-format or --id-col/--next-col")
        g = gdf.to_crs(crs)[[id_col, next_col, "geometry"]].copy()
        g.columns = ["rid", "nxt", "geometry"]
        g["rid"] = pd.to_numeric(g["rid"], errors="coerce").astype("int64")
        g["nxt"] = pd.to_numeric(g["nxt"], errors="coerce").fillna(0).astype("int64")
        g["geometry"] = g.geometry.map(_as_line)
        g = g[g.geometry.notna() & ~g.geometry.is_empty & (g.geometry.geom_type == "LineString")]
        g = g.drop_duplicates("rid").reset_index(drop=True)
        self.g = gpd.GeoDataFrame(g, geometry="geometry", crs=crs)
        self.geom = dict(zip(self.g["rid"], self.g.geometry))
        self.length = {r: float(l) for r, l in zip(self.g["rid"], self.g.geometry.length)}
        self.nxt = dict(zip(self.g["rid"], self.g["nxt"]))
        self.flip = self._orientation()
        LOG.info("[rivers] %d reaches loaded", len(self.g))

    @classmethod
    def from_file(cls, path: str, bbox_ll, id_col: str, next_col: str, crs: str):
        gdf = gpd.read_file(path, bbox=bbox_ll)
        if gdf.empty:
            raise SystemExit(f"[rivers] no reaches inside bbox {bbox_ll} in {path}")
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        return cls(gdf, id_col, next_col, crs)

    def _orientation(self) -> dict:
        """True if a reach's coordinates run downstream -> upstream (needs flipping)."""
        ups = defaultdict(list)
        for r, n in self.nxt.items():
            if n in self.geom:
                ups[n].append(r)
        flip = {}
        for r, line in self.geom.items():
            a, b = Point(line.coords[0]), Point(line.coords[-1])
            n = self.nxt.get(r, 0)
            if n in self.geom:                      # downstream end touches the next reach
                ds_is_first = a.distance(self.geom[n]) < b.distance(self.geom[n])
            elif ups.get(r):                        # upstream end touches the tributaries
                da = min(a.distance(self.geom[u]) for u in ups[r])
                db = min(b.distance(self.geom[u]) for u in ups[r])
                ds_is_first = da > db
            else:                                   # isolated: assume digitised downstream
                ds_is_first = False
            flip[r] = ds_is_first
        return flip

    def snap(self, pts: gpd.GeoDataFrame, max_dist: float) -> dict:
        j = gpd.sjoin_nearest(pts[["geometry"]], self.g[["rid", "geometry"]], how="left",
                              max_distance=max_dist, distance_col="snap_dist_m")
        j = j[~j.index.duplicated(keep="first")]
        snaps = {}
        for idx, row in j.iterrows():
            if pd.isna(row["rid"]):
                snaps[idx] = None
                continue
            rid = int(row["rid"])
            s = self.geom[rid].project(pts.geometry.loc[idx])
            pos = self.length[rid] - s if self.flip[rid] else s
            snaps[idx] = Snap(rid, float(pos), float(row["snap_dist_m"]))
        return snaps

    def downstream_offsets(self, snap: Snap, max_m: float) -> dict:
        """Distance from the point to the UPSTREAM end of every reach on its downstream path.
        Distance to a point B on that path = offsets[B.rid] + B.pos (negative => B is upstream)."""
        out, cum, cur, seen = {}, -snap.pos, snap.rid, set()
        while cur in self.length and cur not in seen and cum <= max_m:
            out[cur] = cum
            seen.add(cur)
            cum += self.length[cur]
            cur = self.nxt.get(cur, 0)
        return out


def pair_distances(net: RiverNetwork, from_snaps: dict, to_snaps: dict, max_m: float) -> pd.DataFrame:
    """All (from, to, d) with 'to' downstream of 'from' along the network within max_m."""
    rows = []
    for fi, fs in from_snaps.items():
        if fs is None:
            continue
        off = net.downstream_offsets(fs, max_m)
        for ti, ts in to_snaps.items():
            if ts is None or ts.rid not in off:
                continue
            d = off[ts.rid] + ts.pos
            if 0.0 <= d <= max_m:
                rows.append((fi, ti, d))
    return pd.DataFrame(rows, columns=["from_idx", "to_idx", "d_m"])


# ============================================================================
# Step 6 - stations, marker anomalies, loading index and lambda selection
# ============================================================================
def load_stations(path: str, crs: str, matrix: str | None):
    df = read_table(path, ["station_id", "lon", "lat"], "stations")
    if matrix and "matrix" in df.columns:
        df = df[df["matrix"].astype(str).str.strip().str.lower() == matrix.lower()]
        if df.empty:
            raise SystemExit(f"[stations] no rows with matrix == {matrix!r}")
    present = [m for m in MARKERS_ALL + list(NORMALISERS) if m in df.columns]
    for m in present:
        df[m] = df[m].map(parse_conc)
    if "unit" in df.columns and df["unit"].nunique() > 1:
        LOG.warning("[stations] several units present (%s): harmonise units per marker first",
                    ", ".join(map(str, df["unit"].dropna().unique())))
    df["station_id"] = df["station_id"].astype(str)
    df["_ref"] = as_bool(df["is_reference"]) if "is_reference" in df.columns else False
    spec = {"lon": ("lon", "first"), "lat": ("lat", "first"),
            "n_samples": ("station_id", "size"), "is_reference": ("_ref", "max")}
    spec.update({m: (m, "median") for m in present})
    st = df.groupby("station_id").agg(**spec).reset_index()
    st["is_reference"] = st["is_reference"].astype(bool)
    markers = [m for m in present if m not in NORMALISERS]
    return to_points(st, crs, "stations"), markers


def marker_anomalies(st: gpd.GeoDataFrame, markers: list[str], z_thr: float, ef_thr: float,
                     min_log_sd: float = 0.1) -> gpd.GeoDataFrame:
    """Robust log z-scores against reference stations; enrichment factor and Igeo if Al/Fe given.
    min_log_sd floors the background spread (0.1 log10 units ~ +/-26 %) so that a few, very
    similar reference stations do not inflate z-scores."""
    st = st.copy()
    use_ref = int(st["is_reference"].sum()) >= 3
    ref = st[st["is_reference"]] if use_ref else st
    if not use_ref:
        LOG.warning("[stations] < 3 reference stations: background estimated from all stations "
                    "(conservative; anomalies will be under-detected)")
    norm = next((c for c in NORMALISERS if c in st.columns and st[c].notna().sum() >= 3), None)
    for m in markers:
        x = st[m].astype(float)
        r = ref[m].astype(float).dropna()
        r = r[r > 0]
        z = pd.Series(np.nan, index=st.index)
        st[f"bg_{m}"] = np.nan
        if len(r) >= 3:
            lr = np.log10(r.to_numpy())
            med = float(np.median(lr))
            sd = float(stats.median_abs_deviation(lr, scale="normal"))
            if not np.isfinite(sd) or sd <= 0:
                sd = float(np.std(lr, ddof=1)) if len(lr) > 1 else np.nan
            sd = max(sd, min_log_sd) if np.isfinite(sd) else min_log_sd
            if np.isfinite(sd) and sd > 0:
                z = (np.log10(x.where(x > 0)) - med) / sd
            st[f"bg_{m}"] = 10 ** med
        st[f"z_{m}"] = z
        anomalous = z.ge(z_thr)
        if norm:
            ratio_ref = (ref[m] / ref[norm]).replace([np.inf, -np.inf], np.nan).dropna()
            if len(ratio_ref) >= 3 and np.median(ratio_ref) > 0:
                st[f"ef_{m}"] = (x / st[norm]) / float(np.median(ratio_ref))
                anomalous = anomalous | st[f"ef_{m}"].ge(ef_thr)
        st[f"igeo_{m}"] = np.log2(x / (1.5 * st[f"bg_{m}"]))   # meaningful for sediments
        st[f"anom_{m}"] = anomalous.fillna(False).astype(bool)

    def a(m):
        return st[f"anom_{m}"] if f"anom_{m}" in st.columns else pd.Series(False, index=st.index)
    st["solder_signature"] = a("pb") & a("sn")
    st["plastic_signature"] = a("sb") | a("pbde_total")
    st["burning_signature"] = a("pcddf_teq")
    st["ewaste_specific"] = st["solder_signature"] | st["plastic_signature"] | st["burning_signature"]
    st["n_markers_anomalous"] = sum(a(m).astype(int) for m in markers) if markers else 0
    return st


def loading_index(pairs: pd.DataFrame, sites: gpd.GeoDataFrame, n_st: int, lam_m: float,
                  mask: np.ndarray | None = None) -> np.ndarray:
    """L_j = sum_i p_i a_i exp(-d_ij / lambda) over sites upstream of station j."""
    if pairs.empty:
        return np.zeros(n_st)
    i = pairs["from_idx"].to_numpy()
    w = sites["p_i"].to_numpy()[i] * sites["a_i"].to_numpy()[i] * np.exp(-pairs["d_m"].to_numpy() / lam_m)
    if mask is not None:
        w = w * mask[i]
    return np.bincount(pairs["to_idx"].to_numpy(), weights=w, minlength=n_st)


def _spearman(x: np.ndarray, y: np.ndarray):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 5 or np.unique(x[ok]).size < 2 or np.unique(y[ok]).size < 2:
        return np.nan, np.nan
    r = stats.spearmanr(x[ok], y[ok])
    return float(r[0]), float(r[1])


def select_lambda(pairs, sites, st, markers, lambdas_km, n_perm, rng, src_mask):
    n = len(st)
    Z = np.column_stack([st[f"z_{m}"].to_numpy(float) for m in markers]) if markers else np.empty((n, 0))
    Ls = {lam: loading_index(pairs, sites, n, lam * 1000.0, src_mask) for lam in lambdas_km}
    rows = []
    for lam, L in Ls.items():
        for k, m in enumerate(markers):
            rho, p = _spearman(L, Z[:, k])
            rows.append({"lambda_km": lam, "marker": m, "spearman_rho": rho, "p_value_uncorrected": p,
                         "n_stations": int(np.isfinite(Z[:, k]).sum())})
    tab = pd.DataFrame(rows)
    mean_rho = tab.groupby("lambda_km")["spearman_rho"].mean() if not tab.empty else pd.Series(dtype=float)
    if mean_rho.notna().any():
        best = float(mean_rho.idxmax())
    else:
        best = float(lambdas_km[len(lambdas_km) // 2])
        LOG.warning("[linkage] association not estimable (need >= 5 stations with values and "
                    "variation in L); lambda set to %.1f km", best)

    def max_mean_rho(Zp):
        vals = []
        for L in Ls.values():
            rs = [r for r in (_spearman(L, Zp[:, k])[0] for k in range(Zp.shape[1])) if np.isfinite(r)]
            if rs:
                vals.append(np.mean(rs))
        return max(vals) if vals else np.nan

    observed, p_perm = max_mean_rho(Z), np.nan
    if np.isfinite(observed) and n_perm > 0:
        null = np.array([max_mean_rho(Z[rng.permutation(n)]) for _ in range(n_perm)])
        null = null[np.isfinite(null)]
        p_perm = (1 + np.sum(null >= observed)) / (1 + len(null))
    tab["selected"] = tab["lambda_km"].eq(best) if not tab.empty else []
    return best, Ls[best], tab, observed, p_perm


# ============================================================================
# Step 7 - evidence criteria C1-C4 per site
# ============================================================================
def describe_anomalies(row: pd.Series, markers: list[str]) -> str:
    parts = []
    for m in markers:
        if bool(row.get(f"anom_{m}", False)):
            z, ef = row.get(f"z_{m}", np.nan), row.get(f"ef_{m}", np.nan)
            txt = f"{m.upper()}(z={z:.1f}" + (f", EF={ef:.1f}" if pd.notna(ef) else "") + ")"
            parts.append(txt)
    return "; ".join(parts) if parts else "none"


def site_evidence(sites, st, markers, down, up, L_best, lam_m, cores, args) -> pd.DataFrame:
    ratio_markers = [m for m in MARKERS_ALL if m in st.columns]
    down = down.sort_values("d_m")
    up = up.sort_values("d_m")
    down_g = {k: g for k, g in down.groupby("from_idx")}       # site -> downstream stations
    up_g = {k: g for k, g in up.groupby("to_idx")}              # site -> upstream stations
    recs = []
    for i, s in sites.iterrows():
        rec = {"site_idx": i}
        rec["C1_detection"] = bool(s["p_i"] >= args.tau)
        snap_ok = pd.notna(s.get("snap_dist_m")) and s["snap_dist_m"] <= args.snap_ok_m
        flood = pd.to_numeric(s.get("flood_freq_max", np.nan), errors="coerce")
        flood_ok = pd.notna(flood) and flood >= args.flood_thr
        rec["C2_connectivity"] = bool(snap_ok or flood_ok)
        rec["C2_note"] = ("channel within %.0f m" % s["snap_dist_m"] if snap_ok else
                          ("flood-connected (freq %.2f)" % flood if flood_ok else
                           "uncertain: no mapped channel nearby and no flood link"))
        g = down_g.get(i)
        rec["downstream_stations"] = ("; ".join(f"{st.loc[int(r.to_idx), 'station_id']} ({r.d_m/1000:.1f} km)"
                                                for r in g.head(5).itertuples()) if g is not None else "")
        C3, note, D = False, "no downstream station within reach", None
        if g is not None:
            D = int(g.iloc[0]["to_idx"]); dD = float(g.iloc[0]["d_m"])
            rD = st.loc[D]
            rec.update({"nearest_downstream_station": rD["station_id"], "d_downstream_km": round(dD / 1000, 2),
                        "markers_anomalous_downstream": describe_anomalies(rD, markers)})
            share = (s["p_i"] * s["a_i"] * np.exp(-dD / lam_m)) / L_best[D] if L_best[D] > 0 else np.nan
            rec["contribution_share_at_downstream"] = round(float(share), 3) if pd.notna(share) else np.nan
            gu = up_g.get(i)
            if gu is not None:
                U = int(gu.iloc[0]["from_idx"]); rU = st.loc[U]
                rec.update({"paired_upstream_station": rU["station_id"],
                            "d_upstream_km": round(float(gu.iloc[0]["d_m"]) / 1000, 2)})
                ratios = {m: rD[m] / rU[m] for m in ratio_markers
                          if pd.notna(rD[m]) and pd.notna(rU[m]) and rU[m] > 0}
                raised = [m for m, r in ratios.items() if r >= args.ratio_thr]
                specific = (("pb" in raised and "sn" in raised) or "sb" in raised
                            or "pbde_total" in raised or "pcddf_teq" in raised)
                C3 = len(raised) >= 2 and specific
                note = "D/U ratios: " + ", ".join(f"{m.upper()}={r:.2f}" for m, r in ratios.items())
            else:
                spec = bool(rD["ewaste_specific"]); n_an = int(rD["n_markers_anomalous"])
                note = (f"no paired upstream station; downstream vs background: {n_an} anomalous marker(s)"
                        + ("; e-waste-specific signature" if spec else ""))
                rec["C3_partial_vs_background"] = bool(n_an >= 2 and spec)
        rec["C3_geochemistry"] = bool(C3)
        rec["C3_note"] = note
        C4 = "not_evaluated"
        if cores is not None and D is not None and pd.notna(s.get("first_built_year", np.nan)):
            sid = st.loc[D, "station_id"]
            if sid in cores.index:
                onset, sd = cores.loc[sid, "onset_year"], cores.loc[sid, "onset_year_sd"]
                C4 = bool(onset >= float(s["first_built_year"]) - 2.0 * sd)
        rec["C4_chronology"] = C4
        c1, c2, c3, c4 = rec["C1_detection"], rec["C2_connectivity"], rec["C3_geochemistry"], C4 is True
        n_true = sum([c1, c2, c3, c4])
        rec["criteria_met"] = n_true
        if args.evidence_rule == "count":       # original rule: number of criteria met
            level = {4: "attributed", 3: "probable", 2: "possible"}.get(n_true, "candidate")
        else:                                   # strict rule (default): geochemistry required
            level = ("attributed" if (c1 and c2 and c3 and c4) else "probable" if (c1 and c2 and c3)
                     else "possible" if n_true >= 2 else "candidate")
        rec["evidence_level"] = level
        recs.append(rec)
    return pd.DataFrame(recs).set_index("site_idx")


# ============================================================================
# Admin labels, grids and outputs
# ============================================================================
def add_admin(cands: gpd.GeoDataFrame, admin_path: str | None) -> gpd.GeoDataFrame:
    if not admin_path:
        return cands
    adm = gpd.read_file(admin_path).to_crs(cands.crs)
    keep = [c for c in ("tam_th", "amp_th", "pro_th", "tam_en", "amp_en", "pro_en") if c in adm.columns]
    if not keep:
        LOG.warning("[admin] no tam_/amp_/pro_ columns found; admin labels skipped")
        return cands
    j = gpd.sjoin(cands[["geometry"]], adm[keep + ["geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    for c in keep:
        cands[c] = j[c]
    return cands


def grid_id(gdf: gpd.GeoDataFrame, km: float, prefix: str) -> pd.Series:
    x = (gdf.geometry.x // (km * 1000)).astype(int)
    y = (gdf.geometry.y // (km * 1000)).astype(int)
    return prefix + x.astype(str) + "_" + y.astype(str)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--candidates", required=True, help="CSV exported by the GEE screening script")
    p.add_argument("--factories", help="DIW factory registry CSV (fac_id, category, lon, lat)")
    p.add_argument("--known", help="previously reported sites CSV (ref_id, lon, lat, source_type, ...)")
    p.add_argument("--negatives", help="hard-negative locations CSV (neg_id, neg_type, lon, lat, buffer_m)")
    p.add_argument("--labels", help="verified labels CSV (site_id, verified 0/1) for calibration")
    p.add_argument("--rivers", help="HydroRIVERS / MERIT-Basins line file (shp, gpkg, geojson)")
    p.add_argument("--river-format", choices=["hydrorivers", "meritbasins", "custom"], default="hydrorivers")
    p.add_argument("--id-col"); p.add_argument("--next-col")
    p.add_argument("--stations", help="water/sediment quality CSV (station_id, lon, lat, markers ...)")
    p.add_argument("--matrix", help="use only rows with this matrix value, e.g. sediment or water")
    p.add_argument("--cores", help="dated cores CSV (station_id, onset_year, onset_year_sd)")
    p.add_argument("--admin", help="subdistrict polygons (e.g. OpenGISData-Thailand subdistricts.geojson)")
    p.add_argument("--outdir", default="fs2s_out")
    p.add_argument("--crs", default="EPSG:32647", help="metric CRS (UTM 47N covers the Bang Pakong basin)")
    p.add_argument("--license-buffer-m", type=float, default=500.0)
    p.add_argument("--known-buffer-m", type=float, default=1000.0)
    p.add_argument("--negative-buffer-m", type=float, default=300.0)
    p.add_argument("--snap-max-m", type=float, default=2000.0, help="max distance to snap to a reach")
    p.add_argument("--snap-ok-m", type=float, default=500.0, help="C2: channel within this distance")
    p.add_argument("--flood-thr", type=float, default=0.10, help="C2: wet-season flood frequency")
    p.add_argument("--max-link-km", type=float, default=50.0)
    p.add_argument("--lambdas-km", default="1,2,5,10,20,50")
    p.add_argument("--markers", default="cu,pb,sb,cd", help="markers used to choose lambda")
    p.add_argument("--tau", type=float, default=0.6, help="C1 threshold on p_i")
    p.add_argument("--z-thr", type=float, default=2.0)
    p.add_argument("--ef-thr", type=float, default=2.0)
    p.add_argument("--ratio-thr", type=float, default=1.5)
    p.add_argument("--evidence-rule", choices=["strict", "count"], default="strict",
                   help="strict: probable = C1+C2+C3, attributed = C1-C4 (default); "
                        "count: probable = any three criteria")
    p.add_argument("--min-log-sd", type=float, default=0.1,
                   help="floor of the background log10 spread used in z-scores")
    p.add_argument("--n-perm", type=int, default=999)
    p.add_argument("--public-grid-km", type=float, default=5.0)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(out / "run_log.txt", "w")])
    rng = np.random.default_rng(args.seed)

    # ---- candidates and verification layers --------------------------------
    cands = load_candidates(args.candidates, args.crs)
    LOG.info("[candidates] %d sites", len(cands))
    if args.factories:
        fac = to_points(read_table(args.factories, ["fac_id", "category", "lon", "lat"], "factories"),
                        args.crs, "factories")
        cands = registry_gap(cands, fac, args.license_buffer_m)
    else:
        LOG.warning("no --factories: registry gap analysis skipped (every site counts as unmatched)")
        cands["is_licensed"], cands["licensed_other_category"] = False, False
        cands["nearest_target_fac_m"] = np.nan
    if args.known:
        known = to_points(read_table(args.known, ["lon", "lat"], "known"), args.crs, "known")
        cands = known_exclusion(cands, known, args.known_buffer_m)
    else:
        LOG.warning("no --known: 'never reported' cannot be checked; all sites flagged unchecked")
        cands["is_previously_reported"], cands["nearest_known_m"] = False, np.nan
    if args.negatives:
        neg = to_points(read_table(args.negatives, ["lon", "lat"], "negatives"), args.crs, "negatives")
        cands = hard_negative_filter(cands, neg, args.negative_buffer_m)
    else:
        cands["is_hard_negative"], cands["hard_negative_type"] = False, None
    cands = assign_status(cands)

    cands["p_i"] = cands["screening_score"]
    cands["p_source"] = "screening score (uncalibrated)"
    if args.labels:
        cands = calibrate(cands, args.labels)
    cands["a_i"] = cands["activity_index"]
    cands = add_admin(cands, args.admin)
    cands["grid_1km"] = grid_id(cands, 1, "G1_")

    # ---- hydrological and geochemical linkage -------------------------------
    lam_m, L_best, evidence, st = np.nan, None, None, None
    if args.rivers and args.stations:
        st, markers_present = load_stations(args.stations, args.crs, args.matrix)
        st = marker_anomalies(st, markers_present, args.z_thr, args.ef_thr, args.min_log_sd)
        markers = [m.strip().lower() for m in args.markers.split(",") if m.strip().lower() in markers_present]
        if not markers:
            LOG.warning("[stations] none of --markers present; using all markers found")
            markers = markers_present
        lon = np.r_[cands["lon"].to_numpy(), st["lon"].to_numpy()]
        lat = np.r_[cands["lat"].to_numpy(), st["lat"].to_numpy()]
        bbox = (lon.min() - 0.3, lat.min() - 0.3, lon.max() + 0.3, lat.max() + 0.3)
        id_col, next_col = (args.id_col, args.next_col) if args.river_format == "custom" else RIVER_FORMATS[args.river_format]
        net = RiverNetwork.from_file(args.rivers, bbox, id_col, next_col, args.crs)
        site_snaps = net.snap(cands, args.snap_max_m)
        stn_snaps = net.snap(st, args.snap_max_m)
        cands["reach_id"] = [site_snaps[i].rid if site_snaps[i] else np.nan for i in cands.index]
        cands["snap_dist_m"] = [round(site_snaps[i].dist, 1) if site_snaps[i] else np.nan for i in cands.index]
        st["reach_id"] = [stn_snaps[i].rid if stn_snaps[i] else np.nan for i in st.index]
        st["snap_dist_m"] = [round(stn_snaps[i].dist, 1) if stn_snaps[i] else np.nan for i in st.index]
        LOG.info("[rivers] snapped %d/%d sites and %d/%d stations within %.0f m",
                 cands["reach_id"].notna().sum(), len(cands), st["reach_id"].notna().sum(), len(st), args.snap_max_m)

        max_m = args.max_link_km * 1000.0
        down = pair_distances(net, site_snaps, stn_snaps, max_m)     # site -> downstream station
        up = pair_distances(net, stn_snaps, site_snaps, max_m)       # station -> downstream site
        LOG.info("[linkage] %d site->station downstream links within %.0f km", len(down), args.max_link_km)

        # All e-waste-related candidates act as sources (unregistered, licensed and known);
        # hard negatives do not. A second index isolates the unregistered sources.
        src_mask = (~cands["is_hard_negative"].fillna(False).astype(bool)).to_numpy(float)
        unreg_mask = (cands["status"] == "unregistered_candidate").to_numpy(float)
        lambdas = [float(v) for v in args.lambdas_km.split(",")]
        lam_km, L_best, tab, obs, p_perm = select_lambda(down, cands, st, markers, lambdas,
                                                         args.n_perm, rng, src_mask)
        lam_m = lam_km * 1000.0
        tab.to_csv(out / "05_lambda_search.csv", index=False)
        st["L_j_all_sources"] = L_best
        st["L_j_unregistered"] = loading_index(down, cands, len(st), lam_m, unreg_mask)
        st["lambda_km"] = lam_km
        LOG.info("[linkage] lambda = %.1f km; max mean Spearman rho = %s; permutation p = %s "
                 "(exploratory; fit the SSN model of Eq. 3 for inference)", lam_km,
                 f"{obs:.2f}" if np.isfinite(obs) else "n/a", f"{p_perm:.3f}" if np.isfinite(p_perm) else "n/a")
        st.drop(columns="geometry").to_csv(out / "04_station_loading.csv", index=False)

        links = down.rename(columns={"from_idx": "site_idx", "to_idx": "stn_idx"}).copy()
        links["site_id"] = cands["site_id"].to_numpy()[links["site_idx"]]
        links["station_id"] = st["station_id"].to_numpy()[links["stn_idx"]]
        links["d_km"] = (links["d_m"] / 1000).round(3)
        w = cands["p_i"].to_numpy()[links["site_idx"]] * cands["a_i"].to_numpy()[links["site_idx"]] \
            * np.exp(-links["d_m"].to_numpy() / lam_m) * src_mask[links["site_idx"]]
        links["weight"] = w
        Lj = L_best[links["stn_idx"].to_numpy()]
        links["share_of_L_j"] = np.where(Lj > 0, w / np.where(Lj > 0, Lj, 1), np.nan)
        links[["site_id", "station_id", "d_km", "weight", "share_of_L_j"]].to_csv(
            out / "06_site_station_links_RESTRICTED.csv", index=False)

        cores = None
        if args.cores:
            cores = read_table(args.cores, ["station_id", "onset_year", "onset_year_sd"], "cores")
            cores["station_id"] = cores["station_id"].astype(str)
            cores = cores.set_index("station_id")
        evidence = site_evidence(cands, st, markers_present, down, up, L_best, lam_m, cores, args)
        cands = cands.join(evidence)
    else:
        LOG.warning("no --rivers/--stations: hydrological and geochemical linkage skipped")
        for c in ("C1_detection", "C2_connectivity", "C3_geochemistry"):
            cands[c] = False
        cands["C1_detection"] = cands["p_i"] >= args.tau
        cands["C4_chronology"], cands["evidence_level"] = "not_evaluated", "candidate"

    # ---- outputs -----------------------------------------------------------
    cands["proxies_detected"] = col(cands, "proxies", "").fillna("").astype(str).str.strip(";")
    cands["license_check"] = np.where(
        cands["is_licensed"], "registered 101/105/106 within %.0f m" % args.license_buffer_m,
        np.where(cands["licensed_other_category"], "no 101/105/106 match; other-category factory nearby",
                 "no 101/105/106 match within %.0f m" % args.license_buffer_m))
    cands["media_check"] = np.where(
        cands["is_previously_reported"], "previously reported (" + col(cands, "known_ref_id", "").astype(str) + ")",
        "no record within %.0f m in supplied list" % args.known_buffer_m if args.known else "NOT CHECKED")
    flat = cands.drop(columns="geometry")
    flat.to_csv(out / "01_candidates_screened_RESTRICTED.csv", index=False)
    flat[flat["status"] == "known_seed"].to_csv(out / "02_known_seeds_RESTRICTED.csv", index=False)

    hp = cands[(cands["status"] == "unregistered_candidate") & (cands["p_i"] >= args.tau)].copy()
    final_cols = [c for c in [
        "site_id", "tam_th", "amp_th", "pro_th", "grid_1km", "lat", "lon", "area_m2",
        "p_i", "p_source", "screening_score", "proxies_detected", "s_struct", "s_thermal", "s_ntl", "s_pond",
        "first_built_year", "license_check", "nearest_target_fac_m", "registry_mismatch_review",
        "media_check", "nearest_known_m", "snap_dist_m", "flood_freq_max", "nearest_downstream_station",
        "d_downstream_km", "downstream_stations", "markers_anomalous_downstream",
        "contribution_share_at_downstream", "paired_upstream_station", "C1_detection", "C2_connectivity",
        "C2_note", "C3_geochemistry", "C3_note", "C3_partial_vs_background", "C4_chronology",
        "evidence_level"] if c in hp.columns]
    order = {"attributed": 0, "probable": 1, "possible": 2, "candidate": 3}
    hp = hp.assign(_o=hp["evidence_level"].map(order)).sort_values(["_o", "p_i"], ascending=[True, False])
    hp[final_cols].to_csv(out / "03_high_probability_unregistered_candidates_RESTRICTED.csv", index=False)
    hp[final_cols + ["geometry"]].to_crs("EPSG:4326").to_file(
        out / "03_high_probability_unregistered_candidates_RESTRICTED.geojson", driver="GeoJSON")

    # Public product: counts per coarse grid cell, no coordinates or identifiers.
    pub = cands[cands["status"] == "unregistered_candidate"].copy()
    pub["grid_public"] = grid_id(pub, args.public_grid_km, f"G{args.public_grid_km:g}km_")
    pub["high_probability"] = pub["p_i"] >= args.tau
    summary = pub.groupby("grid_public").agg(
        n_unregistered_candidates=("site_id", "size"),
        n_high_probability=("high_probability", "sum"),
        mean_p=("p_i", "mean")).round(3).reset_index()
    summary.to_csv(out / "07_public_grid_summary.csv", index=False)

    LOG.info("[summary] status counts: %s", flat["status"].value_counts().to_dict())
    LOG.info("[summary] high-probability unregistered candidates (p_i >= %.2f): %d; evidence levels: %s",
             args.tau, len(hp), hp["evidence_level"].value_counts().to_dict())
    LOG.info("[summary] outputs written to %s. Treat results as candidates for verification, "
             "not as findings of illegality.", out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
