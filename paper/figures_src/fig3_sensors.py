"""Figure 3 - Sensor portfolio: proxy coverage, nominal spatial resolution and revisit."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import figstyle as fs

fs.apply_style()
FC = fs.FAMILY_COLOURS

PROXIES = ["Open burning", "Structures, piles", "All-weather change", "Night activity",
           "Material identity", "Smoke, gases", "Water colour", "Connectivity"]

# name, family, (gsd_min, gsd_max) in m, revisit text, {proxy_index: 1 primary / 0.5 supporting}
ROWS = [
    ("Thermal infrared and active fire", None),
    ("VIIRS I-band (S-NPP, NOAA-20/21)", "Thermal", (375, 375), "\u2264 12 h", {0: 1}),
    ("Landsat 8/9 TIRS", "Thermal", (100, 100), "8 d", {0: 1}),
    ("ECOSTRESS (ISS)", "Thermal", (70, 70), "1\u20135 d*", {0: 1}),
    ("SDGSAT-1 TIS", "Thermal", (30, 30), "11 d", {0: 1}),
    ("Optical multispectral and very high resolution", None),
    ("Sentinel-2 MSI", "Optical", (10, 20), "5 d", {1: 1, 0: .5, 6: 1}),
    ("Landsat 8/9 OLI (archive from 1984)", "Optical", (30, 30), "8 d", {1: .5, 0: .5, 6: .5}),
    ("PlanetScope", "Optical", (3, 3), "1 d", {1: 1, 6: .5}),
    ("THEOS-2 and commercial VHR", "Optical", (0.3, 0.5), "tasked", {1: 1}),
    ("Synthetic aperture radar", None),
    ("Sentinel-1 C-SAR", "SAR", (5, 20), "6\u201312 d", {2: 1, 7: .5}),
    ("ALOS-2/ALOS-4 PALSAR (L-band)", "SAR", (3, 10), "14 d", {2: 1}),
    ("NISAR (L- and S-band)", "SAR", (3, 10), "12 d", {2: 1, 7: .5}),
    ("Night-time lights", None),
    ("VIIRS DNB, Black Marble", "Night lights", (500, 500), "1 d", {3: 1}),
    ("SDGSAT-1 Glimmer", "Night lights", (10, 40), "11 d", {3: 1}),
    ("Imaging spectroscopy", None),
    ("EnMAP, PRISMA", "Imaging spectroscopy", (30, 30), "27\u201329 d\u2020", {4: 1}),
    ("EMIT (ISS)", "Imaging spectroscopy", (60, 60), "irregular*", {4: 1}),
    ("Atmospheric composition", None),
    ("Sentinel-5P TROPOMI", "Atmospheric", (3500, 5500), "1 d", {5: 1}),
    ("GEMS (geostationary)", "Atmospheric", (3500, 8000), "hourly", {5: 1}),
    ("Water and hydrology", None),
    ("Sentinel-3 OLCI", "Hydrology", (300, 300), "\u2264 2 d", {6: 1}),
    ("SWOT (river product)", "Hydrology", (100, 100), "21 d", {7: 1}),
    ("Copernicus DEM, FABDEM, MERIT Hydro", "Hydrology", (30, 90), "static", {7: 1}),
]
FAMILY_OF_HEADER = {"Thermal infrared and active fire": "Thermal",
                    "Optical multispectral and very high resolution": "Optical",
                    "Synthetic aperture radar": "SAR", "Night-time lights": "Night lights",
                    "Imaging spectroscopy": "Imaging spectroscopy",
                    "Atmospheric composition": "Atmospheric", "Water and hydrology": "Hydrology"}

n = len(ROWS)
row_h = 0.158
head_h = 0.80
foot_h = 0.52
H = n * row_h + head_h + foot_h
W = 6.5
fig = plt.figure(figsize=(W, H))
y_body0 = foot_h / H
body_h = n * row_h / H

x_name1 = 2.12          # right edge of names (in)
x_mat0, col_w, ncol = 2.20, 0.262, 8
x_mat1 = x_mat0 + col_w * ncol
x_g0, x_g1 = x_mat1 + 0.20, x_mat1 + 0.20 + 1.38
x_r0 = x_g1 + 0.08

axM = fig.add_axes([0, y_body0, x_mat1 / W, body_h])     # names + matrix in inch-like units
axG = fig.add_axes([x_g0 / W, y_body0, (x_g1 - x_g0) / W, body_h], sharey=axM)
axM.set_xlim(0, x_mat1); axM.set_ylim(n, 0)
axM.axis("off")

for i, row in enumerate(ROWS):
    yc = i + 0.5
    if row[1] is None:  # header row
        fam = FAMILY_OF_HEADER[row[0]]
        axM.add_patch(Rectangle((0.06, i + 0.08), x_mat1 - 0.06, 0.84, facecolor=FC[fam], alpha=0.10,
                                edgecolor="none", zorder=0))
        axG.axhspan(i + 0.08, i + 0.92, color=FC[fam], alpha=0.10, lw=0, zorder=0)
        axM.add_patch(Rectangle((0.06, i + 0.08), 0.045, 0.84, facecolor=FC[fam], edgecolor="none"))
        axM.text(0.16, yc, row[0], va="center", ha="left", fontsize=6.6, weight="bold", color=FC[fam])
        continue
    name, fam, gsd, rev, prx = row
    axM.text(x_name1, yc, name, va="center", ha="right", fontsize=6.4, color=fs.INK)
    for j in range(ncol):
        xc = x_mat0 + (j + 0.5) * col_w
        axM.plot([xc], [yc], marker="o", ms=2.0, color="#D9D9D9", zorder=1)
        if j in prx:
            if prx[j] == 1:
                axM.plot([xc], [yc], marker="o", ms=5.6, mfc=FC[fam], mec=FC[fam], mew=0.6, zorder=2)
            else:
                axM.plot([xc], [yc], marker="o", ms=5.0, mfc="white", mec=FC[fam], mew=0.9, zorder=2)
    # resolution bar
    g0, g1 = gsd
    if g1 > g0:
        axG.plot([g0, g1], [yc, yc], color=FC[fam], lw=3.2, solid_capstyle="round", zorder=3)
    else:
        axG.plot([g0], [yc], marker="o", ms=4.2, color=FC[fam], zorder=3)
    fig.text(x_r0 / W, y_body0 + (n - yc) / n * body_h, rev, ha="left", va="center", fontsize=6.4, color=fs.INK)

# matrix column guides and headers
for j in range(ncol + 1):
    x = x_mat0 + j * col_w
    axM.plot([x, x], [0, n], color="#E4E4E4", lw=0.4, zorder=0)
for j, p in enumerate(PROXIES):
    xc = (x_mat0 + (j + 0.5) * col_w) / W
    fig.text(xc, y_body0 + body_h + 0.05 / H, p, rotation=58, rotation_mode="anchor",
             ha="left", va="center", fontsize=6.3, color=fs.INK)

# resolution axis
axG.set_xscale("log")
axG.set_xlim(0.15, 2.0e4)
axG.set_ylim(n, 0)
axG.set_yticks([])
for v in [1, 10, 100, 1000, 10000]:
    axG.axvline(v, color="#E1E1E1", lw=0.5, zorder=0)
axG.set_xticks([1, 10, 100, 1000, 10000])
axG.set_xticklabels(["1 m", "10 m", "100 m", "1 km", "10 km"])
axG.xaxis.set_minor_locator(plt.NullLocator())
axG.tick_params(axis="x", labelsize=6.2, pad=1.5)
for s in ["left", "right", "top"]:
    axG.spines[s].set_visible(False)
axG.spines["bottom"].set_linewidth(0.5)
fig.text((x_g0 + x_g1) / 2 / W, y_body0 + body_h + 0.07 / H, "Nominal spatial\nresolution (log)",
         ha="center", va="bottom", fontsize=6.6, weight="bold", linespacing=1.0)
fig.text(x_r0 / W, y_body0 + body_h + 0.07 / H, "Nominal\nrevisit", ha="left", va="bottom",
         fontsize=6.6, weight="bold", linespacing=1.0)
fig.text(x_name1 / W, y_body0 + body_h + 0.07 / H, "Sensor or dataset", ha="right", va="bottom",
         fontsize=6.6, weight="bold")

# key
kx = 0.10 / W
ky = 0.03 / H
key = [Line2D([], [], marker="o", ls="none", ms=5.6, mfc="#555555", mec="#555555"),
       Line2D([], [], marker="o", ls="none", ms=5.0, mfc="white", mec="#555555", mew=0.9)]
fig.legend(key, ["Primary role in the framework", "Supporting role"], loc="lower left",
           bbox_to_anchor=(kx, ky - 0.02), ncol=2, fontsize=6.3, handletextpad=0.3, columnspacing=1.2)
fig.text((x_g0 - 0.05) / W, ky, "* irregular sampling (ISS orbit)\n\u2020 4\u20137 d with off-nadir pointing",
         ha="left", va="bottom", fontsize=5.9, color=fs.MUTED, linespacing=1.1)

if __name__ == "__main__":
    rot = lambda t: hasattr(t, "get_rotation") and t.get_rotation() not in (0, 0.0)
    fs.check_overlaps(fig, ignore=lambda a, b: rot(a) and rot(b))
    fig.savefig("paper/figures/fig3_sensor_portfolio.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig("paper/figures/fig3_sensor_portfolio.png", dpi=220, bbox_inches="tight", pad_inches=0.02)
    print(fig.get_size_inches())
