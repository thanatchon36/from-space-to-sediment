"""Figure 6 - Indicative 36-month work plan."""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import to_rgb
import figstyle as fs

fs.apply_style()
C1, C2, C3, C4 = "#2E5E8C", "#9E5B2B", "#16817A", "#7A7A7A"
ROWS = [
    ("Module 1  \u00b7  Detection and inventory", "head", C1, [], (18, "Paper 1 submitted")),
    ("Data curation, labelling, VHR interpretation", "task", C1, [(0, 9)]),
    ("Model development and calibration", "task", C1, [(6, 15)]),
    ("Accuracy assessment, registry gap analysis", "task", C1, [(12, 18)]),
    ("Module 2  \u00b7  Dynamics and displacement", "head", C2, [], (27, "Paper 2 submitted")),
    ("Emergence dating and activity indices", "task", C2, [(12, 20)]),
    ("Event-study and displacement analysis", "task", C2, [(18, 26)]),
    ("Module 3  \u00b7  River source attribution", "head", C3, [], (34, "Paper 3 submitted")),
    ("Network construction and sampling design", "task", C3, [(3, 10)]),
    ("Field campaigns (dry, wet, dry season)", "task", C3, [(13, 16), (19, 22), (25, 28)]),
    ("Laboratory analyses and QA/QC", "task", C3, [(14, 31)]),
    ("Attribution modelling and synthesis", "task", C3, [(24, 33)]),
    ("Integration and thesis writing", "task", C4, [(29, 36)]),
]


def tint(c, f):
    r, g, b = to_rgb(c)
    return (r + (1 - r) * f, g + (1 - g) * f, b + (1 - b) * f)


n = len(ROWS)
fig = plt.figure(figsize=(6.5, 3.0))
ax = fig.add_axes([0.355, 0.12, 0.625, 0.80])
ax.set_xlim(0, 36); ax.set_ylim(n - 0.45, -1.05)
for m in range(0, 37, 3):
    ax.axvline(m, color="#EDEDED", lw=0.5, zorder=0)
for m in (12, 24):
    ax.axvline(m, color="#9A9A9A", lw=0.8, zorder=0.5)
for yr, xc in ((1, 6), (2, 18), (3, 30)):
    ax.text(xc, -0.72, f"Year {yr}", ha="center", va="center", fontsize=6.8, weight="bold", color="#444444")
labels, colors, weights = [], [], []
for i, row in enumerate(ROWS):
    name, kind, col = row[0], row[1], row[2]
    labels.append(name); colors.append(col if kind == "head" else fs.INK)
    weights.append("bold" if kind == "head" else "normal")
    if kind == "head":
        ax.axhspan(i - 0.42, i + 0.42, color=tint(col, 0.9), lw=0, zorder=0.2)
        m, txt = row[4]
        ax.plot([m], [i], marker="D", ms=5.2, color=col, mec="white", mew=0.6, zorder=4)
        ax.text(m - 0.6, i, txt, ha="right", va="center", fontsize=6.2, color=col, weight="bold", zorder=4)
    else:
        segs = row[3]
        for j, (a, b) in enumerate(segs):
            ax.add_patch(Rectangle((a, i - 0.27), b - a, 0.54, fc=col, ec="none", zorder=2))
            if len(segs) == 3:
                ax.text((a + b) / 2, i, ["dry", "wet", "dry"][j], ha="center", va="center",
                        fontsize=5.6, color="white", weight="bold", zorder=3)
ax.set_yticks(range(n)); ax.set_yticklabels(labels, fontsize=6.5)
for tl, c, w in zip(ax.get_yticklabels(), colors, weights):
    tl.set_color(c); tl.set_fontweight(w)
ax.tick_params(axis="y", length=0, pad=4)
ax.set_xticks(range(0, 37, 6)); ax.tick_params(axis="x", labelsize=6.4, length=2.5)
ax.set_xlabel("Month from project start", fontsize=6.8, labelpad=2)
for s in ("left", "right", "top"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_linewidth(0.6)

if __name__ == "__main__":
    fs.check_overlaps(fig)
    fig.savefig("paper/figures/fig6_workplan.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig("paper/figures/fig6_workplan.png", dpi=220, bbox_inches="tight", pad_inches=0.02)
