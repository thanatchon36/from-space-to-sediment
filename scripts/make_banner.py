#!/usr/bin/env python3
"""README banner: the real Bang Pakong river network (HydroRIVERS v1.0 extract) on a dark plate.

Line width follows long-term discharge; neighbouring basins are drawn faintly for context.
Needs data/rivers.json and data/ne_10m_coastline.geojson (python scripts/download_data.py).
Writes docs/assets/banner.png (1680 x 624 px).
"""
import json
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "docs" / "assets" / "banner.png"
BP_MAIN = 41340295                      # HydroRIVERS MAIN_RIV of the Bang Pakong
BG, WATER, CONTEXT, INK = "#0b1020", "#5cc8d6", "#2a3550", "#e8ecf4"
W, H, DPI = 1680, 624, 120


def main():
    reaches = json.load(open(DATA / "rivers.json"))["reaches"]
    bp = [r for r in reaches if r["main"] == BP_MAIN and len(r["c"]) > 1]
    xs = np.concatenate([np.asarray(r["c"])[:, 0] for r in bp])
    ys = np.concatenate([np.asarray(r["c"])[:, 1] for r in bp])
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()

    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
    ax = fig.add_axes([0.40, 0.04, 0.58, 0.92], facecolor=BG)
    # map window: the basin, widened to the axes aspect so nothing is distorted
    aspect = (0.58 * W) / (0.92 * H) / np.cos(np.radians((y0 + y1) / 2))
    cx, cy, half_h = (x0 + x1) / 2, (y0 + y1) / 2, (y1 - y0) / 2 * 1.06
    half_w = max(half_h * aspect, (x1 - x0) / 2 * 1.04)
    half_h = half_w / aspect
    ax.set_xlim(cx - half_w, cx + half_w)
    ax.set_ylim(cy - half_h, cy + half_h)
    ax.set_aspect(1 / np.cos(np.radians(cy)))
    ax.axis("off")

    coast = DATA / "ne_10m_coastline.geojson"
    if coast.exists():
        gpd.read_file(coast, bbox=(cx - half_w, cy - half_h, cx + half_w, cy + half_h)).plot(
            ax=ax, color="#3d4a68", linewidth=0.8, zorder=1)
    for r in reaches:                    # context: other basins inside the window
        c = np.asarray(r["c"])
        if r["main"] == BP_MAIN or len(c) < 2:
            continue
        if c[:, 0].max() < cx - half_w or c[:, 0].min() > cx + half_w:
            continue
        if c[:, 1].max() < cy - half_h or c[:, 1].min() > cy + half_h:
            continue
        ax.plot(c[:, 0], c[:, 1], color=CONTEXT, lw=0.35 + 0.25 * np.log10(1 + r["q"]), zorder=2,
                solid_capstyle="round")
    for r in bp:
        c = np.asarray(r["c"])
        ax.plot(c[:, 0], c[:, 1], color=WATER, lw=0.5 + 0.55 * np.log10(1 + r["q"]), zorder=3,
                solid_capstyle="round", solid_joinstyle="round")

    fig.text(0.045, 0.60, "From Space\nto Sediment", color=INK, fontsize=40, fontweight="bold",
             va="center", ha="left", linespacing=1.05, family="DejaVu Sans")
    fig.text(0.045, 0.33, "Screening e-waste sites from satellite data and\n"
                          "attributing river contamination in Thailand",
             color="#a9b3c8", fontsize=13.5, va="center", ha="left", linespacing=1.4)
    fig.text(0.045, 0.12, "Bang Pakong river network · HydroRIVERS v1.0 (Lehner & Grill, 2013)",
             color="#6f7b95", fontsize=9.5, va="center", ha="left")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=DPI, facecolor=BG)
    print(f"wrote {OUT} ({len(bp)} Bang Pakong reaches)")


if __name__ == "__main__":
    main()
