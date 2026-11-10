"""Figure 7 - Network checks on the real Bang Pakong river network (HydroRIVERS v1.0 extract)."""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle
from shapely.geometry import LineString, box
from pyproj import CRS, Transformer
import figstyle as fs

fs.apply_style()
SIM = "results/sim_out/"
D = "data/"
ALB = CRS.from_proj4("+proj=aea +lat_1=8 +lat_2=18 +lat_0=13 +lon_0=101 +datum=WGS84 +units=m +no_defs")
TO = Transformer.from_crs("EPSG:4326", ALB, always_xy=True)
HALO = [pe.withStroke(linewidth=1.8, foreground="white")]

rv = json.load(open(D + "rivers.json"))
net = gpd.GeoDataFrame([{"HYRIV_ID": r["id"], "q": r["q"], "geometry": LineString(r["c"])}
                        for r in rv["reaches"] if r["main"] == 41340295 and len(r["c"]) > 1],
                       crs="EPSG:4326").to_crs(ALB)
dist = pd.read_csv(SIM + "reach_dist_outlet.csv").set_index("HYRIV_ID")["d_outlet_km"]
net["d"] = net["HYRIV_ID"].map(dist)
chk = json.load(open(SIM + "network_checks.json"))
pairs = pd.read_csv(SIM + "network_pairs.csv")

xb = net.total_bounds
ext = (xb[0] - 18e3, xb[2] + 12e3, xb[1] - 14e3, xb[3] + 10e3)
cb = box(ext[0] - 3e4, ext[2] - 3e4, ext[1] + 3e4, ext[3] + 3e4)
adm1 = gpd.read_file(D + "ne_10m_admin_1_states_provinces.geojson")
prov = adm1[adm1["adm0_a3"] == "THA"].to_crs(ALB)
prov = prov[prov.intersects(cb)].clip(cb)
coast = gpd.read_file(D + "ne_10m_coastline.geojson")
coast = coast[coast.intersects(box(99, 11, 104, 16))].to_crs(ALB).clip(cb)
countries = gpd.read_file(D + "ne_10m_admin_0_countries.geojson")
a3 = "ADM0_A3" if "ADM0_A3" in countries.columns else "adm0_a3"
oth = countries[(countries[a3] != "THA") & countries.intersects(box(99, 11, 104, 16))].to_crs(ALB).clip(cb)

fig = plt.figure(figsize=(6.5, 3.35))
axA = fig.add_axes([0.07, 0.06, 0.51, 0.90])
axB = fig.add_axes([0.765, 0.17, 0.22, 0.70])

# (a) map
axA.set_facecolor(fs.C_WATER)
oth.plot(ax=axA, color=fs.C_LAND_OTHER, edgecolor="#B9B6AF", lw=0.3, zorder=1)
prov.plot(ax=axA, color=fs.C_LAND_TH, edgecolor="#BDBAB2", lw=0.35, zorder=2)
coast.plot(ax=axA, color="#6F8394", lw=0.4, zorder=3)
norm = Normalize(0, np.ceil(net["d"].max() / 50) * 50)
segs, cols, lws = [], [], []
for g, d, q in zip(net.geometry, net["d"], net["q"]):
    segs.append(np.asarray(g.coords)); cols.append(plt.cm.viridis_r(norm(d)))
    lws.append(float(np.clip(0.5 + 0.55 * np.log10(q / 12), 0.5, 2.4)))
axA.add_collection(LineCollection(segs, colors=cols, linewidths=lws, capstyle="round", zorder=4))
ox, oy = net.loc[net["d"].idxmin()].geometry.coords[-1]
axA.plot(ox, oy, marker="o", ms=4.5, mfc="white", mec="#222222", mew=0.8, zorder=6)
axA.annotate("outlet", (ox, oy), xytext=(-6, -6), textcoords="offset points", ha="right", va="top",
             fontsize=6.3, path_effects=HALO, zorder=7)
for lon, lat, name in ((101.62, 14.17, "PRACHIN BURI"), (101.50, 13.38, "CHACHOENGSAO"),
                       (101.15, 14.33, "NAKHON NAYOK"), (102.07, 13.62, "SA KAEO")):
    x, y = TO.transform(lon, lat)
    axA.text(x, y, name, ha="center", va="center", fontsize=5.9, color="#6B675F", path_effects=HALO, zorder=5)
x, y = TO.transform(100.80, 13.36)
axA.text(x, y, "Gulf of\nThailand", ha="center", va="center", fontsize=6.0, style="italic",
         color="#4F7290", linespacing=1.0, zorder=5)
axA.set_xlim(ext[0], ext[1]); axA.set_ylim(ext[2], ext[3]); axA.set_xticks([]); axA.set_yticks([])
axA.set_xlabel(""); axA.set_ylabel("")
for s in axA.spines.values():
    s.set_linewidth(0.7)
# graticule labels
for lo in (101.0, 101.5, 102.0):
    la = np.linspace(12, 16, 200); xx, yy = TO.transform(np.full_like(la, lo), la)
    axA.plot(xx, yy, color=fs.C_GRID, lw=0.3, ls=(0, (2, 2)), zorder=3.5)
    k = np.argmin(np.abs(np.array(yy) - ext[2]))
    if ext[0] < xx[k] < ext[1]:
        axA.annotate(f"{lo:g}\u00b0E".replace(".5\u00b0", "\u00b030\u2032"), (xx[k], ext[2]), xytext=(0, -2.5),
                     textcoords="offset points", ha="center", va="top", fontsize=5.9, color="#444444",
                     annotation_clip=False)
for la_ in (13.5, 14.0):
    lo = np.linspace(99, 104, 200); xx, yy = TO.transform(lo, np.full_like(lo, la_))
    axA.plot(xx, yy, color=fs.C_GRID, lw=0.3, ls=(0, (2, 2)), zorder=3.5)
    k = np.argmin(np.abs(np.array(xx) - ext[0]))
    if ext[2] < yy[k] < ext[3]:
        axA.annotate(f"{la_:g}\u00b0N".replace(".5\u00b0", "\u00b030\u2032"), (ext[0], yy[k]), xytext=(-2.5, 0),
                     textcoords="offset points", ha="right", va="center", fontsize=5.9, color="#444444",
                     annotation_clip=False)
# scale bar (bottom right)
sx, sy = ext[1] - 62e3, ext[2] + 7e3
for i, (a, b) in enumerate(((0, 25e3), (25e3, 50e3))):
    axA.add_patch(Rectangle((sx + a, sy), b - a, 1.6e3, facecolor="#222222" if i == 0 else "white",
                            edgecolor="#222222", lw=0.5, zorder=8))
for v in (0, 25, 50):
    axA.text(sx + v * 1e3, sy + 3.0e3, f"{v}", ha="center", va="bottom", fontsize=5.8, zorder=8)
axA.text(sx + 52e3, sy + 0.8e3, "km", ha="left", va="center", fontsize=5.8, zorder=8)
# colorbar
cax = fig.add_axes([0.597, 0.20, 0.013, 0.60])
cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap="viridis_r"), cax=cax)
cbar.set_label("Along-network distance to outlet (km)", fontsize=6.4, labelpad=3)
cbar.ax.tick_params(labelsize=6, length=2)
cbar.outline.set_linewidth(0.5)
axA.text(0.025, 0.975, "a", transform=axA.transAxes, fontsize=9, weight="bold", ha="left", va="top",
         bbox=dict(facecolor="white", edgecolor="none", pad=1.2), zorder=10)

# (b) pipeline vs reference distances
mx = float(np.ceil(max(pairs.max()) / 50) * 50)
axB.plot([0, mx], [0, mx], color="#9A9A9A", lw=0.8, ls=(0, (3, 2)), zorder=1)
axB.scatter(pairs["d_reference_km"], pairs["d_pipeline_km"], s=6, color="#2E5E8C", alpha=0.6, lw=0, zorder=2)
axB.set_xlim(0, mx); axB.set_ylim(0, mx)
axB.set_xlabel("Reference distance (km)", fontsize=6.6)
axB.set_ylabel("Pipeline distance (km)", fontsize=6.6)
axB.tick_params(labelsize=6)
axB.set_title("b   Distance check", fontsize=7, weight="bold", loc="left", pad=4)
txt = (f"n = {chk['pairs']} random pairs\nmax |error| < 1 nm\n"
       f"orientation: {chk['orientation_agreement']*100:.0f}% of {chk['n_reaches']} reaches")
axB.text(0.04, 0.96, txt, transform=axB.transAxes, ha="left", va="top", fontsize=6.0, linespacing=1.15)
for s in ("top", "right"):
    axB.spines[s].set_visible(False)

if __name__ == "__main__":
    fs.check_overlaps(fig)
    fig.savefig("paper/figures/fig7_network_check.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig("paper/figures/fig7_network_check.png", dpi=220, bbox_inches="tight", pad_inches=0.02)
    print(chk)
