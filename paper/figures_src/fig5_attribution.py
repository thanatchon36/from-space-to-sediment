"""Figure 5 - Schematic of the Module 3 attribution design (illustrative; not data)."""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Ellipse, Polygon, Patch
from matplotlib.lines import Line2D
import figstyle as fs

fs.apply_style()
HALO = [pe.withStroke(linewidth=2.0, foreground="white")]
RIV, SITE, SITE_D, STN, CORE = "#5E93BF", "#E8A15B", "#A84F12", "#1F5F9A", "#4B3F8C"


def catmull(points, n=30):
    P = np.asarray(points, float)
    P = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2][None, :])
    return np.vstack(out)


def nearest(curve, p):
    k = int(np.argmin(np.hypot(curve[:, 0] - p[0], curve[:, 1] - p[1])))
    return curve[k], k


fig = plt.figure(figsize=(6.5, 2.85))
axA = fig.add_axes([0.0, 0.0, 0.48, 1.0])
XR = 10.0; YR = XR * 2.85 / (0.48 * 6.5)
axA.set_xlim(0, XR); axA.set_ylim(0, YR); axA.set_xticks([]); axA.set_yticks([])
axA.set_facecolor("#FBFAF6")
for s in axA.spines.values():
    s.set_color("#BBBBBB"); s.set_linewidth(0.6)

axA.add_patch(Polygon([(0, 0), (3.6, 0), (3.0, 0.55), (2.1, 1.0), (1.0, 1.3), (0, 1.45)],
                      closed=True, fc=fs.C_WATER, ec="#9DB7CC", lw=0.6, zorder=1))
flood = Polygon([(6.75, 3.55), (7.2, 2.75), (8.15, 2.55), (8.55, 3.05), (7.85, 3.75), (7.1, 4.15)],
                closed=True, fc="#DCEAF5", ec="#8DB3D1", lw=0.5, hatch="....", zorder=1.5)
axA.add_patch(flood)
main = catmull([(9.85, 8.9), (8.95, 7.95), (8.0, 7.1), (7.0, 6.25), (5.9, 5.45), (4.9, 4.6),
                (3.95, 3.75), (3.1, 2.8), (2.35, 1.8), (1.75, 1.05)])
t1 = catmull([(0.35, 6.0), (1.3, 5.5), (2.25, 4.9), (3.15, 4.3), (3.95, 3.75)])
t2 = catmull([(9.85, 2.4), (8.9, 2.95), (7.9, 3.6), (6.9, 4.35), (5.9, 5.45)])
for c, lw in ((main, 2.3), (t1, 1.4), (t2, 1.4)):
    axA.plot(c[:, 0], c[:, 1], color=RIV, lw=lw, solid_capstyle="round", zorder=2)
for c, k in ((main, 40), (main, 170), (t1, 55), (t2, 60)):
    a, b = c[k], c[k + 4]
    axA.annotate("", xy=b, xytext=a, zorder=3,
                 arrowprops=dict(arrowstyle="-|>", color="#2E5E8C", lw=0.8, mutation_scale=8, shrinkA=0, shrinkB=0))

pond = Ellipse((2.0, 3.05), 0.95, 0.5, fc="#DCEAF5", ec="#6F95B5", lw=0.6, zorder=2)
axA.add_patch(pond)
axA.plot([2.0], [3.05], marker="s", ms=4.6, color=CORE, mec="white", mew=0.5, zorder=5)
axA.annotate("C", (2.0, 3.05), xytext=(-9, 0), textcoords="offset points", ha="right", va="center",
             fontsize=6.6, weight="bold", color=CORE, path_effects=HALO, zorder=6)

p, k = nearest(main, (2.35, 1.8))
d = main[k + 2] - main[k - 2]; d = d / np.hypot(*d); perp = np.array([d[1], -d[0]])
axA.plot([p[0] - 0.55 * perp[0], p[0] + 0.55 * perp[0]], [p[1] - 0.55 * perp[1], p[1] + 0.55 * perp[1]],
         color="#333333", lw=0.8, ls=(0, (3, 2)), zorder=4)
axA.text(p[0] + 0.78 * perp[0] + 0.12, p[1] + 0.78 * perp[1], "tidal limit", ha="left", va="center",
         fontsize=6.0, style="italic", color="#333333", path_effects=HALO, zorder=6)
axA.text(0.85, 0.55, "estuary", ha="center", va="center", fontsize=6.0, style="italic", color="#4F7290", zorder=6)
axA.text(7.55, 1.95, "flood-connected\narea", ha="center", va="center", fontsize=5.9, color="#4F7290",
         linespacing=1.0, path_effects=HALO, zorder=6)

SITES = {"S1": ((8.75, 6.85), main, (7, -4)), "S2": ((7.55, 3.05), t2, (0, -9)),
         "S3": ((4.75, 3.85), main, (7, -3))}
for name, (xy, curve, off) in SITES.items():
    q, _ = nearest(curve, xy)
    axA.plot([xy[0], q[0]], [xy[1], q[1]], color=SITE_D, lw=0.7, ls=(0, (1, 1.2)), zorder=3)
    axA.plot([xy[0]], [xy[1]], marker="^", ms=6.2, color=SITE, mec=SITE_D, mew=0.7, zorder=5)
    axA.annotate(name, xy, xytext=off, textcoords="offset points", ha="left" if off[0] > 0 else "center",
                 va="center" if off[1] > -5 else "top", fontsize=6.6, weight="bold", color=SITE_D,
                 path_effects=HALO, zorder=6)
STATIONS = {"U1": (main, (9.35, 8.35), (6, 1), "left"), "D1": (main, (7.5, 6.65), (-7, -3), "right"),
            "U2": (t2, (8.9, 2.95), (5, -7), "left"), "D2": (t2, (6.55, 4.65), (-7, 1), "right"),
            "R": (t1, (1.3, 5.5), (0, 7), "center"), "D3": (main, (3.35, 3.1), (7, 1), "left")}
for name, (curve, xy, off, ha) in STATIONS.items():
    q, _ = nearest(curve, xy)
    axA.plot([q[0]], [q[1]], marker="o", ms=5.2, color=STN, mec="white", mew=0.7, zorder=5)
    axA.annotate(name, q, xytext=off, textcoords="offset points", ha=ha, va="center", fontsize=6.6,
                 weight="bold", color=STN, path_effects=HALO, zorder=6)
handles = [Line2D([], [], marker="^", ls="none", ms=6, mfc=SITE, mec=SITE_D, mew=0.7),
           Line2D([], [], marker="o", ls="none", ms=5, mfc=STN, mec="white"),
           Line2D([], [], marker="s", ls="none", ms=4.6, mfc=CORE, mec="white"),
           Line2D([], [], color="#333333", lw=0.8, ls=(0, (3, 2))),
           Patch(fc="#DCEAF5", ec="#8DB3D1", hatch="....", lw=0.5)]
labels = ["Candidate site S (from Module 1)", "Station: U upstream, D downstream, R reference",
          "Sediment core C in a floodplain pond", "Tidal limit", "Flood-connected area"]
axA.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.075, 0.995), fontsize=6.0,
           handlelength=1.5, labelspacing=0.35, borderaxespad=0.2, frameon=False)
axA.text(0.025, 0.975, "a", transform=axA.transAxes, fontsize=9, weight="bold", ha="left", va="top")
axA.text(XR - 0.12, 0.22, "schematic \u2014 not data", ha="right", va="bottom", fontsize=5.8,
         style="italic", color="#777777")

# (b) isotope mixing space
axB = fig.add_axes([0.567, 0.22, 0.165, 0.66])
axB.set_xlim(0, 1); axB.set_ylim(0, 1); axB.set_xticks([]); axB.set_yticks([])
for s in axB.spines.values():
    s.set_linewidth(0.6)
EM = {"Geogenic": ((0.78, 0.24), "#8C7B6B"), "Legacy gasoline": ((0.22, 0.78), "#6C5B7B"),
      "E-waste": ((0.40, 0.30), SITE_D)}
cs = [v[0] for v in EM.values()]
for a, b in ((0, 1), (1, 2), (0, 2)):
    axB.plot([cs[a][0], cs[b][0]], [cs[a][1], cs[b][1]], color="#9A9A9A", lw=0.6, ls=(0, (2, 2)), zorder=1)
for name, (c, col) in EM.items():
    axB.add_patch(Ellipse(c, 0.24, 0.14, fc=col, alpha=0.18, ec=col, lw=0.8, zorder=2))
axB.text(0.78, 0.07, "Geogenic", ha="center", va="center", fontsize=6.0, color="#6B5B4B")
axB.text(0.37, 0.80, "Legacy gasoline", ha="left", va="center", fontsize=6.0, color="#6C5B7B")
axB.text(0.36, 0.14, "E-waste", ha="center", va="center", fontsize=6.0, color=SITE_D)
U = np.array([(0.62, 0.46), (0.58, 0.50), (0.65, 0.43)])
Dd = np.array([(0.50, 0.37), (0.47, 0.40), (0.53, 0.34)])
axB.plot(U[:, 0], U[:, 1], "o", ms=3.6, color=STN, mec="white", mew=0.4, zorder=4)
axB.plot(Dd[:, 0], Dd[:, 1], "o", ms=3.6, color=SITE_D, mec="white", mew=0.4, zorder=4)
axB.annotate("", xy=Dd.mean(0) + (0.02, 0.02), xytext=U.mean(0) - (0.01, 0.01), zorder=3,
             arrowprops=dict(arrowstyle="-|>", color="#333333", lw=0.7, mutation_scale=7))
axB.text(0.71, 0.53, "U", ha="left", va="center", fontsize=6.4, weight="bold", color=STN)
axB.text(0.43, 0.45, "D", ha="right", va="center", fontsize=6.4, weight="bold", color=SITE_D)
axB.set_xlabel("$^{206}$Pb/$^{207}$Pb", fontsize=6.6, labelpad=2)
axB.set_ylabel("$^{208}$Pb/$^{206}$Pb", fontsize=6.6, labelpad=2)
axB.set_title("b   Lead-isotope mixing", fontsize=7, weight="bold", loc="left", pad=4)

# (c) sediment-core chronology
axC = fig.add_axes([0.826, 0.22, 0.165, 0.66])
axC.set_xlim(0, 1); axC.set_ylim(0, 1)
yy = np.linspace(0.05, 0.95, 16)
rng = np.random.default_rng(7)
xx = np.where(yy < 0.52, 0.17 + 0.03 * rng.standard_normal(len(yy)),
              0.17 + 0.72 * (yy - 0.52) / 0.43 + 0.03 * rng.standard_normal(len(yy)))
axC.axhspan(0.47, 0.57, color="#9A9A9A", alpha=0.18, lw=0, zorder=0)
axC.axhline(0.52, color="#333333", lw=0.8, ls=(0, (3, 2)), zorder=1)
axC.plot(xx, yy, "-o", color=SITE_D, ms=2.8, lw=0.9, mec="white", mew=0.3, zorder=3)
axC.text(0.97, 0.445, "emergence $t_i$\n(satellite)", ha="right", va="top", fontsize=6.0,
         color="#333333", linespacing=1.0)
axC.set_xticks([]); axC.set_yticks([0.06, 0.94]); axC.set_yticklabels(["older", "recent"], fontsize=6.0)
axC.tick_params(axis="y", length=0, pad=2)
axC.set_xlabel("Marker enrichment", fontsize=6.6, labelpad=2)
axC.set_title("c   Core chronology", fontsize=7, weight="bold", loc="left", pad=4)
for s in axC.spines.values():
    s.set_linewidth(0.6)

if __name__ == "__main__":
    fs.check_overlaps(fig)
    fig.savefig("paper/figures/fig5_attribution_schematic.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig("paper/figures/fig5_attribution_schematic.png", dpi=220, bbox_inches="tight", pad_inches=0.02)
