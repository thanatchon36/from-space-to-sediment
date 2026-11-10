"""Figure 1 - Study context map of Thailand (three panels + locator + legend)."""
import json
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, Patch, Polygon as MplPolygon
from matplotlib.lines import Line2D
from shapely.geometry import box, LineString, Point
from pyproj import CRS, Transformer

import figstyle as fs

fs.apply_style()
D = "data/"
CRS_TH = CRS.from_proj4("+proj=aea +lat_1=8 +lat_2=18 +lat_0=13 +lon_0=101 "
                        "+datum=WGS84 +units=m +no_defs")
TO = Transformer.from_crs("EPSG:4326", CRS_TH, always_xy=True)
HALO = [pe.withStroke(linewidth=1.9, foreground="white")]
HALO_W = [pe.withStroke(linewidth=1.9, foreground=fs.C_WATER)]


def P(lon, lat):
    return TO.transform(lon, lat)


# ------------------------------------------------------------------ data
countries = gpd.read_file(D + "ne_10m_admin_0_countries.geojson")
a3 = "ADM0_A3" if "ADM0_A3" in countries.columns else "adm0_a3"
countries = countries[countries.intersects(box(85, -12, 128, 32))].to_crs(CRS_TH)
thai = countries[countries[a3] == "THA"]

adm1 = gpd.read_file(D + "ne_10m_admin_1_states_provinces.geojson")
prov = adm1[adm1["adm0_a3"] == "THA"].to_crs(CRS_TH)
prov = prov.set_index("name")

EAST = ["Prachin Buri", "Chachoengsao", "Chon Buri", "Rayong"]
NE = ["Kalasin", "Buri Ram"]

dist = gpd.read_file(D + "og_districts.geojson")
DIST = {"2509": ("Si Mahosot", "E"), "2105": ("Ban Khai", "E"),
        "4618": ("Khong Chai", "N"), "3119": ("Ban Mai Chaiyaphot", "N")}
dsel = dist[dist["amp_code"].isin(DIST.keys())].to_crs(CRS_TH)
dsel["label"] = dsel["amp_code"].map(lambda c: DIST[c][0])
dsel["grp"] = dsel["amp_code"].map(lambda c: DIST[c][1])

rv = json.load(open(D + "rivers.json"))
recs = [{"id": r["id"], "main": r["main"], "q": r["q"], "up": r["up"],
         "geometry": LineString(r["c"])} for r in rv["reaches"] if len(r["c"]) > 1]
rivers = gpd.GeoDataFrame(recs, crs="EPSG:4326").to_crs(CRS_TH)
BP_MAIN = 41340295
rivers["bp"] = rivers["main"] == BP_MAIN

lakes = gpd.read_file(D + "ne_10m_lakes.geojson")
lakes = lakes[lakes.intersects(box(96, 5, 107, 21))].to_crs(CRS_TH)

c50 = gpd.read_file(D + "ne_50m_admin_0_countries.geojson")
blines = gpd.read_file(D + "ne_10m_admin_0_boundary_lines_land.geojson")
blines = blines[blines.intersects(box(90, 0, 112, 25))].to_crs(CRS_TH)
coast = gpd.read_file(D + "ne_10m_coastline.geojson")
coast = coast[coast.intersects(box(90, 0, 112, 25))].to_crs(CRS_TH)


def proj_bounds(lon0, lon1, lat0, lat1, n=60):
    lons = np.r_[np.linspace(lon0, lon1, n), np.full(n, lon1),
                 np.linspace(lon1, lon0, n), np.full(n, lon0)]
    lats = np.r_[np.full(n, lat0), np.linspace(lat0, lat1, n),
                 np.full(n, lat1), np.linspace(lat1, lat0, n)]
    x, y = TO.transform(lons, lats)
    return np.array(x), np.array(y)


# panel extents (projected metres)
ta = thai.total_bounds
EXT_A = (ta[0] - 75e3, ta[2] + 70e3, ta[1] - 55e3, ta[3] + 25e3)
GEO_B = (100.30, 102.45, 12.45, 14.62)
GEO_C = (102.25, 104.05, 14.98, 16.72)


def ext_from_geo(g):
    x, y = proj_bounds(*g)
    return (x.min(), x.max(), y.min(), y.max())


EXT_B, EXT_C = ext_from_geo(GEO_B), ext_from_geo(GEO_C)
asp = lambda e: (e[3] - e[2]) / (e[1] - e[0])

# ------------------------------------------------------------- layout
W = 6.5
lm, gap, rm, vgap = 0.36, 0.50, 0.06, 0.36
wb = (asp(EXT_A) * (W - lm - gap - rm) - vgap) / (asp(EXT_A) + asp(EXT_B) + asp(EXT_C))
wa = W - lm - gap - rm - wb
ha, hb, hc = wa * asp(EXT_A), wb * asp(EXT_B), wb * asp(EXT_C)
bottom_leg, lab_h, top = 0.62, 0.20, 0.06
H = bottom_leg + lab_h + ha + top
fig = plt.figure(figsize=(W, H))
y0 = (bottom_leg + lab_h) / H
axA = fig.add_axes([lm / W, y0, wa / W, ha / H])
axC = fig.add_axes([(lm + wa + gap) / W, y0, wb / W, hc / H])
axB = fig.add_axes([(lm + wa + gap) / W, y0 + (hc + vgap) / H, wb / W, hb / H])


def base(ax, ext, river_min_q, bp_min_q, river_scale):
    cb = box(ext[0] - 3e4, ext[2] - 3e4, ext[1] + 3e4, ext[3] + 3e4)

    def C(g):
        try:
            d = g.clip(cb)
        except Exception:
            g = g.copy(); g["geometry"] = g.geometry.make_valid(); d = g.clip(cb)
        return d[~d.is_empty]
    ax.set_facecolor(fs.C_WATER)
    C(countries[countries[a3] != "THA"]).plot(ax=ax, color=fs.C_LAND_OTHER,
                                           edgecolor="#B9B6AF", linewidth=0.35, zorder=1)
    C(thai).plot(ax=ax, color=fs.C_LAND_TH, edgecolor="none", zorder=1.5)
    pv = C(prov)
    cols = [fs.C_EAST if n in EAST else fs.C_NE if n in NE else fs.C_LAND_TH for n in pv.index]
    pv.plot(ax=ax, color=cols, edgecolor="#B5B2AA", linewidth=0.28, zorder=2)
    C(lakes).plot(ax=ax, color=fs.C_WATER, edgecolor=fs.C_RIVER, linewidth=0.25, zorder=2.5)
    r = rivers[(rivers.q >= river_min_q) & ~rivers.bp]
    r = r[r.intersects(cb)]
    lw = np.clip(river_scale[0] + river_scale[1] * np.log10(r.q / river_min_q), 0.2, 1.6)
    r.plot(ax=ax, color=fs.C_RIVER, linewidth=lw, zorder=3, capstyle="round")
    b = rivers[rivers.bp & (rivers.q >= bp_min_q)]
    b = b[b.intersects(cb)]
    lwb = np.clip(river_scale[0] + 0.15 + river_scale[1] * np.log10(b.q / bp_min_q), 0.3, 1.5)
    b.plot(ax=ax, color=fs.C_RIVER_D, linewidth=lwb, zorder=3.2, capstyle="round")
    C(coast).plot(ax=ax, color="#6F8394", linewidth=0.4, zorder=4)
    C(blines).plot(ax=ax, color="#FFFFFF", linewidth=1.6, zorder=4.1)
    C(blines).plot(ax=ax, color=fs.C_BORDER, linewidth=0.75, linestyle=(0, (4, 1.2, 1, 1.2)), zorder=4.2)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
    for s in ax.spines.values():
        s.set_linewidth(0.7); s.set_color("#333333")


def graticule(ax, ext, lons, lats, fmt, step_lw=0.3):
    for lo in lons:
        la = np.linspace(-5, 30, 400)
        x, y = TO.transform(np.full_like(la, lo), la)
        ax.plot(x, y, color=fs.C_GRID, lw=step_lw, ls=(0, (2, 2)), zorder=3.6, alpha=0.8)
        x, y = np.array(x), np.array(y)
        i = np.where(np.diff(np.sign(y - ext[2])))[0]
        if len(i):
            k = i[0]
            xb = x[k] + (ext[2] - y[k]) * (x[k + 1] - x[k]) / (y[k + 1] - y[k])
            if ext[0] < xb < ext[1]:
                ax.annotate(fmt(lo, "E"), (xb, ext[2]), xytext=(0, -2.5), textcoords="offset points",
                            ha="center", va="top", fontsize=6, color="#444444", annotation_clip=False)
    for la in lats:
        lo = np.linspace(85, 120, 400)
        x, y = TO.transform(lo, np.full_like(lo, la))
        ax.plot(x, y, color=fs.C_GRID, lw=step_lw, ls=(0, (2, 2)), zorder=3.6, alpha=0.8)
        x, y = np.array(x), np.array(y)
        i = np.where(np.diff(np.sign(x - ext[0])))[0]
        if len(i):
            k = i[0]
            yb = y[k] + (ext[0] - x[k]) * (y[k + 1] - y[k]) / (x[k + 1] - x[k])
            if ext[2] < yb < ext[3]:
                ax.annotate(fmt(la, "N"), (ext[0], yb), xytext=(-2.5, 0), textcoords="offset points",
                            ha="right", va="center", fontsize=6, color="#444444", annotation_clip=False)


def dms(v, h):
    d = int(np.floor(v)); m = int(round((v - d) * 60))
    return f"{d}\u00b0{m:02d}\u2032{h}" if m else f"{d}\u00b0{h}"


def scalebar(ax, lon, lat, segs_km, label_every=1, h_frac=0.006, ext=None, boxed=False):
    x0, y0 = P(lon, lat)
    hh = (ext[3] - ext[2]) * h_frac
    tot = segs_km[-1] * 1e3
    if boxed:
        ax.add_patch(Rectangle((x0 - 0.06 * tot, y0 - 4.2 * hh), tot * 1.22, 8.8 * hh,
                               facecolor="white", edgecolor="none", alpha=0.85, zorder=8))
    prev = 0
    for i, s in enumerate(segs_km):
        ax.add_patch(Rectangle((x0 + prev * 1e3, y0), (s - prev) * 1e3, hh,
                               facecolor="#222222" if i % 2 == 0 else "white",
                               edgecolor="#222222", linewidth=0.5, zorder=9))
        prev = s
    for s in [0] + list(segs_km):
        ax.text(x0 + s * 1e3, y0 + hh * 1.9, f"{s:g}", ha="center", va="bottom", fontsize=5.8, zorder=10)
    ax.text(x0 + tot + 0.04 * tot, y0 + hh * 0.5, "km", ha="left", va="center", fontsize=5.8, zorder=10)


def label(ax, lon, lat, s, **kw):
    x, y = P(lon, lat)
    kw.setdefault("fontsize", 6.5)
    kw.setdefault("ha", "center"); kw.setdefault("va", "center")
    kw.setdefault("path_effects", HALO)
    kw.setdefault("zorder", 12)
    return ax.text(x, y, s, **kw)


def leader(ax, frm, to, s, color, ha="left", va="center", fs_=6.2, weight="normal"):
    """frm: (lon,lat) anchor on feature; to: (lon,lat) label position."""
    x1, y1 = P(*frm); x2, y2 = P(*to)
    ax.plot([x1, x2], [y1, y2], color=color, lw=0.55, zorder=11,
            path_effects=[pe.withStroke(linewidth=1.6, foreground="white")])
    ax.plot([x1], [y1], marker="o", ms=1.6, color=color, zorder=11.5)
    return ax.text(x2, y2, s, ha=ha, va=va, fontsize=fs_, color=color, weight=weight,
                   path_effects=HALO, zorder=12)


# ------------------------------------------------------------ panel a
base(axA, EXT_A, river_min_q=150, bp_min_q=40, river_scale=(0.25, 0.45))
graticule(axA, EXT_A, [98, 100, 102, 104, 106], range(6, 21, 2), lambda v, h: f"{v}\u00b0{h}")
# example districts as markers
for _, r in dsel.iterrows():
    c = r.geometry.representative_point()
    axA.plot(c.x, c.y, marker="^" if r.grp == "E" else "o", ms=4.2,
             mfc=fs.C_EAST_D if r.grp == "E" else fs.C_NE_D, mec="white", mew=0.45, zorder=13)
# Bangkok
bx, by = P(100.5018, 13.7563)
axA.plot(bx, by, marker="*", ms=6.5, color="#111111", mec="white", mew=0.4, zorder=13)
axA.annotate("Bangkok", (bx, by), xytext=(-5, 4), textcoords="offset points", ha="right",
             va="bottom", fontsize=6.5, path_effects=HALO, zorder=12)
# extents of b and c
for g, letter, off in [(GEO_B, "b", (101.42, 12.18)), (GEO_C, "c", (104.33, 16.5))]:
    x, y = proj_bounds(*g)
    axA.plot(np.r_[x, x[0]], np.r_[y, y[0]], color="#111111", lw=0.75, zorder=14)
    label(axA, off[0], off[1], letter, fontsize=7.5, weight="bold")
# country / sea labels
ck = dict(fontsize=6.3, color="#8A877F", path_effects=[pe.withStroke(linewidth=1.6, foreground=fs.C_LAND_OTHER)])
label(axA, 97.22, 16.55, "M Y A N M A R", rotation=90, **ck)
label(axA, 102.15, 19.55, "L A O S", **ck)
label(axA, 104.75, 13.1, "C A M B O D I A", **ck)
label(axA, 101.75, 5.55, "M A L A Y S I A", **ck)
wk = dict(fontsize=6.5, color="#4F7290", style="italic", path_effects=HALO_W)
label(axA, 97.55, 10.4, "Andaman\nSea", linespacing=1.0, **wk)
label(axA, 101.15, 9.85, "Gulf of\nThailand", linespacing=1.0, **wk)
label(axA, 104.95, 9.45, "South China\nSea", linespacing=1.0, **wk)
rk = dict(fontsize=5.8, color=fs.C_RIVER_D, style="italic", path_effects=HALO)
label(axA, 100.33, 15.48, "Chao Phraya", rotation=80, **rk)
label(axA, 103.55, 18.47, "Mekong", rotation=-8, **rk)
label(axA, 99.35, 19.05, "Ping", rotation=-60, **rk)
# scale bar + north arrow (Andaman Sea)
scalebar(axA, 97.05, 6.35, [100, 200], ext=EXT_A)
nx, ny = P(97.55, 7.55)
axA.annotate("", xy=(nx, ny + 70e3), xytext=(nx, ny), zorder=10,
             arrowprops=dict(arrowstyle="-|>,head_width=0.22,head_length=0.5", lw=0.8, color="#222222"))
axA.text(nx, ny + 82e3, "N", ha="center", va="bottom", fontsize=7, weight="bold", zorder=10)
axA.text(0.025, 0.985, "a", transform=axA.transAxes, fontsize=9, weight="bold", va="top", ha="left",
         bbox=dict(facecolor="white", edgecolor="none", pad=1.2), zorder=20)

# locator inset (top-right corner of panel a)
ins_w = 0.80
axL = fig.add_axes([(lm + wa - ins_w - 0.02) / W, y0 + (ha - ins_w * 0.92 - 0.02) / H,
                    ins_w / W, ins_w * 0.92 / H])
loc = c50[c50.intersects(box(86, -11, 126, 30))]
axL.set_facecolor(fs.C_WATER)
loc.plot(ax=axL, color="#D9D6CF", edgecolor="white", linewidth=0.2)
loc[loc["ADM0_A3"] == "THA"].plot(ax=axL, color="#3C4A57", edgecolor="none")
axL.set_xlim(88, 124); axL.set_ylim(-9, 28); axL.set_xticks([]); axL.set_yticks([])
axL.set_xlabel(""); axL.set_ylabel("")
for s in axL.spines.values():
    s.set_linewidth(0.6); s.set_color("#333333")
axL.text(0.5, 0.06, "Southeast Asia", transform=axL.transAxes, ha="center", va="bottom",
         fontsize=5.6, color="#333333", path_effects=HALO_W)

# ------------------------------------------------------------ panel b
base(axB, EXT_B, river_min_q=12, bp_min_q=12, river_scale=(0.35, 0.40))
graticule(axB, EXT_B, [100.5, 101, 101.5, 102], [12.5, 13, 13.5, 14, 14.5], dms)
for _, r in dsel[dsel.grp == "E"].iterrows():
    gpd.GeoSeries([r.geometry], crs=CRS_TH).plot(ax=axB, facecolor="none", edgecolor=fs.C_EAST_D,
                                                  hatch="//////", linewidth=0.75, zorder=5)
pk = dict(fontsize=6.4, weight="bold", color="#5C2A08")
label(axB, 101.80, 14.20, "PRACHIN BURI", **pk)
label(axB, 101.55, 13.43, "CHACHOENGSAO", **pk)
label(axB, 101.12, 13.22, "CHON BURI", **pk)
label(axB, 101.70, 12.98, "RAYONG", **pk)
gk = dict(fontsize=6.0, color="#55524C")
label(axB, 101.22, 14.33, "Nakhon Nayok", **gk)
label(axB, 102.22, 13.73, "Sa Kaeo", **gk)
label(axB, 102.12, 12.72, "Chanthaburi", **gk)
leader(axB, (101.43, 13.83), (101.62, 13.66), "Si Mahosot", fs.C_EAST_D, weight="bold")
leader(axB, (101.36, 12.80), (101.55, 12.60), "Ban Khai", fs.C_EAST_D, ha="left", weight="bold")
x, y = P(100.5018, 13.7563)
axB.plot(x, y, marker="*", ms=7, color="#111111", mec="white", mew=0.4, zorder=13)
axB.annotate("Bangkok", (x, y), xytext=(0, 5), textcoords="offset points", ha="center", va="bottom",
             fontsize=6.2, path_effects=HALO, zorder=12)
x, y = P(100.884, 13.083)
axB.plot(x, y, marker="s", ms=3.6, color="#111111", mec="white", mew=0.4, zorder=13)
axB.annotate("Laem Chabang\nPort", (x, y), xytext=(-5, 0), textcoords="offset points", ha="right",
             va="center", fontsize=6.0, linespacing=1.0, path_effects=HALO_W, zorder=12)
label(axB, 100.62, 12.78, "Gulf of\nThailand", linespacing=1.0, **wk)
rkb = dict(fontsize=6.0, color=fs.C_RIVER_D, style="italic", weight="bold", path_effects=HALO)
label(axB, 101.06, 13.58, "Bang Pakong R.", rotation=72, **rkb)
label(axB, 101.47, 14.07, "Prachin Buri R.", rotation=-2, **rkb)
scalebar(axB, 100.36, 12.56, [25, 50], ext=EXT_B, h_frac=0.012)
axB.text(0.03, 0.97, "b", transform=axB.transAxes, fontsize=9, weight="bold", va="top", ha="left",
         bbox=dict(facecolor="white", edgecolor="none", pad=1.2), zorder=20)

# ------------------------------------------------------------ panel c
base(axC, EXT_C, river_min_q=12, bp_min_q=12, river_scale=(0.35, 0.40))
graticule(axC, EXT_C, [102.5, 103, 103.5, 104], [15, 15.5, 16, 16.5], dms)
for _, r in dsel[dsel.grp == "N"].iterrows():
    gpd.GeoSeries([r.geometry], crs=CRS_TH).plot(ax=axC, facecolor="none", edgecolor=fs.C_NE_D,
                                                  hatch="//////", linewidth=0.75, zorder=5)
pk2 = dict(fontsize=6.4, weight="bold", color="#2E2560")
label(axC, 103.62, 16.58, "KALASIN", **pk2)
label(axC, 102.80, 15.18, "BURI RAM", **pk2)
label(axC, 102.60, 16.45, "Khon Kaen", **gk)
label(axC, 103.16, 15.99, "Maha Sarakham", **gk)
label(axC, 103.80, 15.83, "Roi Et", **gk)
label(axC, 103.62, 15.08, "Surin", **gk)
leader(axC, (103.47, 16.27), (103.72, 16.36), "Khong Chai", fs.C_NE_D, weight="bold")
leader(axC, (102.86, 15.60), (103.05, 15.45), "Ban Mai\nChaiyaphot", fs.C_NE_D, weight="bold")
label(axC, 102.98, 16.24, "Chi R.", rotation=-22, **rk)
label(axC, 103.30, 15.33, "Mun R.", rotation=0, **rk)
scalebar(axC, 102.30, 15.83, [25, 50], ext=EXT_C, h_frac=0.012)
axC.text(0.03, 0.97, "c", transform=axC.transAxes, fontsize=9, weight="bold", va="top", ha="left",
         bbox=dict(facecolor="white", edgecolor="none", pad=1.2), zorder=20)

# ------------------------------------------------------------ legend
H_ = [Patch(facecolor=fs.C_EAST, edgecolor="#9C9890", lw=0.4),
      Patch(facecolor=fs.C_NE, edgecolor="#9C9890", lw=0.4),
      Patch(facecolor="white", edgecolor="#555555", hatch="//////", lw=0.6),
      Line2D([], [], marker="^", ls="none", mfc=fs.C_EAST_D, mec="white", ms=5),
      Line2D([], [], color=fs.C_RIVER_D, lw=1.3),
      Line2D([], [], color=fs.C_RIVER, lw=1.0),
      Line2D([], [], color=fs.C_BORDER, lw=0.75, ls=(0, (4, 1.2, 1, 1.2))),
      Line2D([], [], marker="*", ls="none", color="#111111", ms=6.5)]
L_ = ["Reported industrial-scale processing or enforcement (East)",
      "Reported household-scale dismantling and burning (Northeast)",
      "Example districts, seed localities (panels b, c)",
      "Example districts in panel a (\u25b2 East, \u25cf Northeast)",
      "Bang Pakong river system (proposed case basin)",
      "Other rivers, Q \u2265 12 m$^3$ s$^{-1}$ (\u2265 150 in panel a)",
      "International boundary",
      "Bangkok (\u25a0 Laem Chabang Port in panel b)"]
leg = fig.legend(H_, L_, loc="lower left", bbox_to_anchor=(lm / W, 0.0, 1 - lm / W - rm / W, bottom_leg / H),
                 ncol=2, fontsize=6.3, handlelength=1.8, handleheight=0.9, columnspacing=1.2,
                 labelspacing=0.5, borderaxespad=0.1, mode="expand")

for _ax in (axA, axB, axC, axL):
    _ax.set_xlabel(""); _ax.set_ylabel("")

if __name__ == "__main__":
    hits, out = fs.check_overlaps(fig)
    fig.savefig("paper/figures/fig1_study_area.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig("paper/figures/fig1_study_area.png", dpi=220, bbox_inches="tight", pad_inches=0.02)
    print("size in:", fig.get_size_inches())
