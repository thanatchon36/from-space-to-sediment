"""Figure 2 - The From Space to Sediment framework."""
import itertools
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import to_rgb
import figstyle as fs

fs.apply_style()
W, H = 6.5, 6.6
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
fig.canvas.draw()
R = fig.canvas.get_renderer()
inv = ax.transData.inverted()
BOXES = []
FC = fs.FAMILY_COLOURS
_ref = {}


def tint(c, f=0.86):
    r, g, b = to_rgb(c)
    return (r + (1 - r) * f, g + (1 - g) * f, b + (1 - b) * f)


def dbox(t):
    bb = t.get_window_extent(R)
    (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
    return x0, x1, y0, y1


def ref_h(size, nlines, weight="normal", ls=1.22):
    key = (size, nlines, weight, ls)
    if key not in _ref:
        t = ax.text(0, 0, "\n".join(["Hg"] * nlines), fontsize=size, weight=weight, linespacing=ls)
        b = dbox(t); t.remove(); _ref[key] = b[3] - b[2]
    return _ref[key]


def tbox(cx, top, width, title, body, fc, ec, title_color=None, body_color=fs.INK,
         pad=0.075, gap=0.035, fs_t=6.9, fs_b=6.25, lw=0.9):
    t1 = ax.text(cx, top - pad, title, ha="center", va="top", fontsize=fs_t, weight="bold",
                 color=title_color or ec, zorder=4)
    b1 = dbox(t1); b2 = None
    y = top - pad - ref_h(fs_t, 1, "bold")
    if body:
        nl = body.count("\n") + 1
        t2 = ax.text(cx, y - gap, body, ha="center", va="top", fontsize=fs_b, color=body_color,
                     linespacing=1.22, zorder=4)
        b2 = dbox(t2)
        y = min(y - gap - ref_h(fs_b, nl), b2[2])
    bottom = y - pad
    left, right = cx - width / 2, cx + width / 2
    for b in (b1, b2):
        if b and (b[0] < left + 0.03 or b[1] > right - 0.03):
            raise ValueError(f"text overflows box: {title!r} {b} vs {(left, right)}")
    ax.add_patch(FancyBboxPatch((left, bottom), width, top - bottom,
                                boxstyle="round,pad=0,rounding_size=0.06", fc=fc, ec=ec, lw=lw, zorder=2))
    r = (left, right, bottom, top)
    BOXES.append((title, r))
    return r


def arrow(x1, y1, x2, y2, color="#4A4A4A", lw=0.9):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=3,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=8))


GAP = 0.30
ax.text(0.07, H - 0.06, "EARTH OBSERVATION \u2014 proxies of activity", ha="left", va="top",
        fontsize=6.8, weight="bold", color="#555555")
EO = [("Thermal infrared", "VIIRS \u00b7 Landsat TIRS\nECOSTRESS \u00b7 SDGSAT-1", "Thermal"),
      ("Optical and VHR", "Sentinel-2 \u00b7 Landsat OLI\nPlanetScope \u00b7 THEOS-2", "Optical"),
      ("Radar (SAR)", "Sentinel-1 \u00b7 ALOS-2/4\nNISAR", "SAR"),
      ("Night-time lights", "VIIRS DNB\nSDGSAT-1 Glimmer", "Night lights"),
      ("Imaging spectroscopy", "EnMAP \u00b7 PRISMA\nEMIT", "Imaging spectroscopy")]
top = H - 0.30
eo = []
for i, (t, b, fam) in enumerate(EO):
    eo.append(tbox(0.66 + i * 1.295, top, 1.18, t, b, tint(FC[fam]), FC[fam], fs_t=6.6, fs_b=6.0))
eo_bottom = min(r[2] for r in eo)

m1 = tbox(3.25, eo_bottom - GAP, 6.36, "Module 1  \u00b7  Detection and national inventory  (Paper 1)",
          "Labels from enforcement records, NGO and media reports, VHR interpretation and field checks; hard negatives\n"
          "from licensed recyclers, industrial estates and agro-industry  \u00b7  positive\u2013unlabelled learning and segmentation\n"
          "isotonic calibration \u2192 site probabilities $p_i$  \u00b7  design-based accuracy  \u00b7  registry gap analysis (categories 101, 105, 106)",
          tint("#2E5E8C", 0.9), "#2E5E8C")
for r in eo:
    cx = (r[0] + r[1]) / 2
    arrow(cx, r[2], cx, m1[3])

invn = tbox(3.25, m1[2] - GAP, 4.4, "Candidate-site inventory",
            "$S=\\{(s_i,\\ p_i,\\ t_i,\\ a_i)\\}$:  location, probability, emergence date, activity",
            "#2F3B45", "#2F3B45", title_color="white", body_color="white")
arrow(3.25, m1[2], 3.25, invn[3])

m_top = invn[2] - GAP - 0.04
m2 = tbox(1.62, m_top, 3.1, "Module 2  \u00b7  Dynamics and displacement  (Paper 2)",
          "Emergence dating (CCDC) and activity indices\nexposure-based event study around 2018 and 2025\n"
          "heterogeneity-robust staggered DiD \u00b7 spillover rings\ntrade link: UN Comtrade (HS 8549), port access",
          tint("#9E5B2B", 0.9), "#9E5B2B")
m3 = tbox(4.88, m_top, 3.1, "Module 3  \u00b7  River source attribution  (Paper 3)",
          "Hydrography: MERIT Hydro, FABDEM, HydroRIVERS\nSentinel-1 floods \u00b7 paired upstream\u2013downstream sampling\n"
          "SSN models \u00b7 Pb isotopes \u00b7 Bayesian mixing \u00b7 PMF\n$^{210}$Pb-dated sediment cores",
          tint("#16817A", 0.9), "#16817A")
arrow(invn[0] + 0.55, invn[2], 1.62, m2[3])
arrow(invn[1] - 0.55, invn[2], 4.88, m3[3])

syn = tbox(3.25, min(m2[2], m3[2]) - GAP, 6.36, "Evidence synthesis  \u00b7  four-criterion attribution rule",
           "C1 detection ($p_i \\geq \\tau$)   +   C2 hydrological connectivity   +   C3 geochemical consistency   +   "
           "C4 chronology ($t_i$ precedes onset)\nattributed: C1\u2013C4  \u00b7  probable: C1 + C2 + C3  \u00b7  "
           "possible: any two criteria  \u00b7  otherwise retained as candidate",
           tint("#4B3F8C", 0.9), "#4B3F8C")
arrow(1.62, m2[2], 1.62, syn[3]); arrow(4.88, m3[2], 4.88, syn[3])
o1 = tbox(1.62, syn[2] - GAP, 3.1, "Outputs",
          "Aggregated hotspot maps with uncertainty\nenforcement prioritisation \u00b7 policy evaluation", "white", "#555555")
o2 = tbox(4.88, syn[2] - GAP, 3.1, "Safeguards",
          "Candidate-site language; no named facilities\naggregated publication \u00b7 data sharing with authorities",
          "white", "#555555")
arrow(1.62, syn[2], 1.62, o1[3]); arrow(4.88, syn[2], 4.88, o2[3])

if __name__ == "__main__":
    bad = [(a[0], b[0]) for a, b in itertools.combinations(BOXES, 2)
           if a[1][0] < b[1][1] and b[1][0] < a[1][1] and a[1][2] < b[1][3] and b[1][2] < a[1][3]]
    print("  box overlaps:", bad)
    fs.check_overlaps(fig)
    from matplotlib.transforms import Bbox
    crop = Bbox.from_extents(0, min(o1[2], o2[2]) - 0.04, W, H)
    fig.savefig("paper/figures/fig2_framework.pdf", bbox_inches=crop)
    fig.savefig("paper/figures/fig2_framework.png", dpi=220, bbox_inches=crop)
