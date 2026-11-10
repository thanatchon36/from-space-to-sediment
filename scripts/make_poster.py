#!/usr/bin/env python3
"""LinkedIn launch poster -> docs/assets/linkedin_poster.png (1440 x 1800 px, 4:5).

Companion to the thainowcast poster: same grid, teal instead of amber. The map is the real Bang Pakong
river network (HydroRIVERS v1.0) with Natural Earth land; no candidate site is drawn. Every number comes
from the paper or results/sim_out/. Needs `make data`; uses Fira Sans from data/fonts/ when present
(Google Fonts, OFL), otherwise DejaVu Sans.
"""
import json
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results" / "sim_out"
OUT = ROOT / "docs" / "assets" / "linkedin_poster.png"
W, H, DPI = 1440, 1800, 120
BP_MAIN = 41340295
BG, LAND, COAST = "#04060c", "#0e1424", "#26314d"
ACC, ACC2, INK, INK2, MUTED = "#3fd0dc", "#a8eef3", "#f2f4f8", "#a9b3c8", "#6f7b95"

fonts = {}
for w in ("Regular", "Medium", "SemiBold", "Bold"):
    f = DATA / "fonts" / f"FiraSans-{w}.ttf"
    if f.exists():
        fm.fontManager.addfont(str(f))
        fonts[w] = fm.FontProperties(fname=str(f))
FAMILY = "Fira Sans" if fonts else "DejaVu Sans"


def T(x, y, s, size, color=INK, weight="normal", **kw):
    """Text at pixel coordinates from the top-left corner."""
    return fig.text(x / W, 1 - y / H, s, fontsize=size, color=color, family=FAMILY, weight=weight,
                    va=kw.pop("va", "top"), **kw)


nums = json.load(open(RES / "paper_numbers.json"))
net = json.load(open(RES / "network_checks.json"))
lo, hi = nums["rngPrecAttributed"].split("--")
reaches = json.load(open(DATA / "rivers.json"))["reaches"]
bp = [r for r in reaches if r["main"] == BP_MAIN and len(r["c"]) > 1]
bp_ids = {r["id"] for r in bp}
outlet = np.asarray(next(r for r in bp if r["down"] not in bp_ids)["c"])[-1]

fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)

# ---------------------------------------------------------------- map (right)
ax = fig.add_axes([0.40, 0.255, 0.60, 0.70], facecolor=BG)
x0, x1, y0, y1 = 100.62, 102.47, 12.55, 15.05
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
ax.set_aspect(1 / np.cos(np.radians(13.9)))
ax.axis("off")
yy, xx = np.mgrid[0:1:300j, 0:1:300j]          # faint blue glow over the Gulf
glow = np.exp(-((xx - 0.30) ** 2 / 0.10 + (yy - 0.12) ** 2 / 0.06))
ax.imshow(glow, extent=(x0, x1, y0, y1), origin="lower", cmap=matplotlib.colors.LinearSegmentedColormap
          .from_list("g", [BG, "#0c1a33"]), zorder=0, aspect="auto")
land = gpd.read_file(DATA / "ne_10m_admin_0_countries.geojson", bbox=(x0, y0, x1, y1))
land.plot(ax=ax, color=LAND, edgecolor=COAST, linewidth=0.8, zorder=1)
for r in reaches:                                # other basins, faint
    c = np.asarray(r["c"])
    if r["id"] in bp_ids or len(c) < 2 or c[:, 0].max() < x0 or c[:, 0].min() > x1 \
            or c[:, 1].max() < y0 or c[:, 1].min() > y1:
        continue
    ax.plot(c[:, 0], c[:, 1], color="#1d2a45", lw=0.4 + 0.3 * np.log10(1 + r["q"]), zorder=2)
ny, nx = 400, 300                                # fade the map edges into the page
v = np.minimum.reduce([np.linspace(0, 1, nx)[None, :].repeat(ny, 0) / 0.12,
                       np.linspace(1, 0, nx)[None, :].repeat(ny, 0) / 0.04,
                       np.linspace(0, 1, ny)[:, None].repeat(nx, 1) / 0.18,
                       np.linspace(1, 0, ny)[:, None].repeat(nx, 1) / 0.12]).clip(0, 1)
rgba = np.zeros((ny, nx, 4)); rgba[..., :3] = matplotlib.colors.to_rgb(BG)
rgba[..., 3] = 1 - v * v * (3 - 2 * v)                # smoothstep
ax.imshow(rgba, extent=(x0, x1, y0, y1), origin="lower", zorder=2.5, aspect="auto")
for width, alpha in ((9, 0.05), (5, 0.10), (2.6, 0.22)):   # glow, then the line itself
    for r in bp:
        c = np.asarray(r["c"])
        ax.plot(c[:, 0], c[:, 1], color=ACC, lw=width * (0.4 + 0.35 * np.log10(1 + r["q"])),
                alpha=alpha, zorder=3, solid_capstyle="round")
for r in bp:
    c = np.asarray(r["c"])
    ax.plot(c[:, 0], c[:, 1], color=ACC2, lw=0.5 + 0.55 * np.log10(1 + r["q"]), zorder=4,
            solid_capstyle="round", solid_joinstyle="round")
ax.plot(*outlet, "o", ms=7, mfc="none", mec=ACC2, mew=1.2, zorder=5)


def to_px(lon, lat):
    X, Y = fig.transFigure.inverted().transform(ax.transData.transform((lon, lat)))
    return X * W, (1 - Y) * H


def leader(px, py, lon, lat):
    tx, ty = to_px(lon, lat)
    fig.add_artist(plt.Line2D([px / W, tx / W], [1 - py / H, 1 - ty / H], color=ACC, lw=0.8, alpha=0.7))


# ---------------------------------------------------------------- header + hero (left)
T(94, 66, "FROM SPACE TO SEDIMENT", 17, ACC, "bold")
T(470, 68, "open-source e-waste forensics for Thailand", 15, INK2)
T(80, 112, "62", 150, ACC, "bold")
T(100, 352, "million tonnes", 34, ACC2)
T(104, 430, "of e-waste in 2022. Only 22%\nwas documented as formally\nrecycled. Where does the rest go?",
  19, INK, linespacing=1.3)
T(104, 580, "From Space to Sediment follows it\nfrom orbit to the riverbed.", 21, ACC, "semibold",
  linespacing=1.25)

# ---------------------------------------------------------------- callouts
cx = 700
T(cx, 790, "Bang Pakong basin", 18, ACC, "semibold", ha="right")
T(cx, 828, f"{net['n_reaches']} river reaches, {net['total_length_km']:.0f} km\nof real channel network",
  13.5, INK, ha="right", linespacing=1.3)
leader(cx + 12, 812, 101.55, 14.10)
T(cx, 950, "Measured along the water", 18, ACC, "semibold", ha="right")
T(cx, 988, "distances follow the river, downstream\nonly, to the Gulf outlet",
  13.5, INK, ha="right", linespacing=1.3)
leader(cx + 12, 972, *outlet)
T(cx, 1110, "No sites on this map", 18, INK2, "semibold", ha="right")
T(cx, 1148, "candidate locations stay restricted;\nonly aggregated grids are published",
  13.5, INK2, ha="right", linespacing=1.3)

# ---------------------------------------------------------------- stats row
fig.add_artist(plt.Line2D([94 / W, 1346 / W], [1 - 1326 / H] * 2, color="#1c2740", lw=1))
stats = [("5", "satellite sensor\nfamilies"), ("4", "lines of evidence before\na site counts as a source"),
         (nums["simRepsTotal"], "simulations on the\nreal river network"),
         (f"{lo}–{hi}", "simulated precision when\nall four lines agree")]
for i, (big, small) in enumerate(stats):
    x = 94 + i * 324
    T(x, 1375, big, 44 if len(big) < 5 else 38, ACC, "semibold")
    T(x, 1450, small, 13.5, INK2, linespacing=1.3)

# ---------------------------------------------------------------- link box + footer
fig.add_artist(FancyBboxPatch((86 / W, 1 - 1728 / H), 1268 / W, 182 / H, boxstyle="round,pad=0,rounding_size=0.012",
                              transform=fig.transFigure, fc="#0a1222", ec="#1c2740", lw=1.2))
T(130, 1588, "Code + paper", 12.5, INK2)
T(130, 1618, "github.com/thanatchon36/from-space-to-sediment", 13, INK)
T(730, 1588, "Dataset", 12.5, INK2)
T(730, 1618, "hf.co/datasets/thanatchon36/from-space-to-sediment", 13, INK)
T(130, 1676, "This release validates the method on the real Bang Pakong network with synthetic sites; "
             "field results come next.", 11.5, INK2)
T(94, 1755, "Thanatchon Chongmankhong  ·  views are my own  ·  DOI 10.5281/zenodo.24102402", 11, INK2)
T(1346, 1757, "HydroRIVERS v1.0 · Natural Earth · Global E-waste Monitor 2024", 9, MUTED, ha="right")

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=DPI, facecolor=BG)
print(f"wrote {OUT}")
