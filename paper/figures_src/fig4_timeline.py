"""Figure 4 - Policy shocks, enforcement and Earth-observation capability, 2015-2026.

Label positions are chosen by a small constraint solver so that no label overlaps
another label, a stem, or a fixed annotation.
"""
import itertools
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import figstyle as fs

fs.apply_style()
fig = plt.figure(figsize=(6.5, 2.55))
ax = fig.add_axes([0.01, 0.02, 0.98, 0.96])
X0, X1 = 2014.55, 2027.1
ax.set_xlim(X0, X1)
ax.set_ylim(-3.7, 3.45)
ax.axis("off")
POL, EO = "#9E2A2B", "#2E5E8C"
fig.canvas.draw()
R = fig.canvas.get_renderer()
inv = ax.transData.inverted()


def measure(t):
    bb = t.get_window_extent(R)
    (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
    return x1 - x0, y1 - y0


# ------------------------------------------------------------------ axis (timeline bar)
BAR = 0.21
ax.add_patch(Rectangle((2015.0, -BAR), 12.0, 2 * BAR, fc="#E6E6E6", ec="none", zorder=1))
for y in range(2016, 2027):
    ax.plot([y, y], [-BAR, BAR], color="white", lw=1.2, zorder=1.5)
for y in range(2015, 2027):
    ax.text(y + 0.5, 0, str(y), ha="center", va="center", fontsize=6.5, color="#333333", zorder=3)

# fixed annotations (obstacles)
t_pol = ax.text(X0 + 0.05, 3.42, "Policy and enforcement shocks", ha="left", va="top",
                fontsize=6.9, weight="bold", color=POL)
t_eo = ax.text(X0 + 0.05, -0.36, "Satellite launches", ha="left", va="top",
               fontsize=6.9, weight="bold", color=EO)
band = (2024.70, 2025.92)
ax.add_patch(Rectangle((band[0], BAR + 0.05), band[1] - band[0], 3.0, facecolor=POL, alpha=0.07,
                       edgecolor="none", zorder=0))
t_band = ax.text(sum(band) / 2, 3.22, "Renewed\nenforcement\ncampaigns", ha="center", va="top",
                 fontsize=6.0, color=POL, linespacing=1.0)

# Module 2 periods strip
y0, h = -3.66, 0.52
segs = [(2015.0, 2018.0, "Baseline (2015\u20132017)", "#ECE7DE"),
        (2018.0, 2025.0, "Post-import-ban period (2018\u20132024)", "#DCD2C3"),
        (2025.0, 2027.0, "Post-Basel (2025\u20132026)", "#CBBDA8")]
for a, b, txt, col in segs:
    ax.add_patch(Rectangle((a, y0), b - a, h, facecolor=col, edgecolor="white", lw=1.2, zorder=1))
    ax.text((a + b) / 2, y0 + h / 2, txt, ha="center", va="center", fontsize=6.1, color=fs.INK, zorder=2)
t_strip = ax.text(X0 + 0.05, y0 + h + 0.08, "Module 2 event-study periods (Module 1 inventory spans 2015\u20132026)",
                  ha="left", va="bottom", fontsize=6.4, weight="bold", color="#5A4A35")


def box_of(t):
    bb = t.get_window_extent(R)
    (x0, y0_), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
    return (x0, x1, y0_, y1)


OBST = [box_of(t) for t in (t_pol, t_eo, t_strip, t_band)]

EVENTS = [
    (2017.54, "Jul 2017", "China notifies WTO of\nsolid-waste import ban"),
    (2018.00, "Jan 2018", "China\u2019s import ban\ntakes effect"),
    (2018.45, "2018", "Thai raids on e-waste\nrecyclers; import curbs"),
    (2022.00, "Jan 2022", "HS 2022 heading 8549\n(e-waste and scrap)"),
    (2022.45, "Jun 2022", "Basel COP-15 adopts\ne-waste amendments"),
    (2025.00, "1 Jan 2025", "Basel e-waste amend-\nments enter into force"),
]
LAUNCH = [(2015.48, "Sentinel-2A"), (2017.18, "Sentinel-2B"), (2017.78, "Sentinel-5P"),
          (2018.49, "ECOSTRESS"), (2019.22, "PRISMA"), (2020.13, "GEMS"), (2021.74, "Landsat 9"),
          (2021.85, "SDGSAT-1"), (2022.25, "EnMAP"), (2022.54, "EMIT"), (2022.96, "SWOT"),
          (2023.77, "THEOS-2"), (2024.50, "ALOS-4"), (2024.93, "Sentinel-1C"), (2025.58, "NISAR")]

# measure label sizes
ev_items = []
for t, head, body in EVENTS:
    tt = ax.text(0, 0, head + "\n" + body, fontsize=6.0, linespacing=1.0)
    w, hgt = measure(tt); tt.remove()
    ev_items.append(dict(t=t, w=w + 0.06, h=hgt, head=head, body=body))
la_items = []
for t, name in LAUNCH:
    tt = ax.text(0, 0, name, fontsize=6.0)
    w, hgt = measure(tt); tt.remove()
    la_items.append(dict(t=t, w=w + 0.05, h=hgt, name=name))


def solve(items, levels, upward):
    """Assign (level, side) to items; levels are label anchor y (bottom for upward events)."""
    opts = list(itertools.product(levels, ["R", "L"]))
    best = None

    def geom(it, lev, side):
        x0 = it["t"] + 0.05 if side == "R" else it["t"] - 0.05 - it["w"]
        x1 = x0 + it["w"]
        if upward:
            return (x0, x1, lev, lev + it["h"])
        return (x0, x1, lev - it["h"] / 2, lev + it["h"] / 2)

    def stem(it, lev):
        if upward:
            return (it["t"], BAR, lev + it["h"])
        return (it["t"], lev, -BAR)

    def ov(a, b, pad=0.04):
        return a[0] - pad < b[1] and b[0] - pad < a[1] and a[2] - pad < b[3] and b[2] - pad < a[3]

    def ok(k, assign):
        it = items[k]; lev, side = assign[k]; g = geom(it, lev, side)
        if g[0] < X0 or g[1] > X1:
            return False
        for o in OBST:
            if ov(g, o):
                return False
        for j in range(k):
            gj = geom(items[j], *assign[j])
            if ov(g, gj):
                return False
            for a, b in ((k, j), (j, k)):
                x, ylo, yhi = stem(items[a], assign[a][0])
                gb = geom(items[b], *assign[b])
                if gb[0] - 0.03 < x < gb[1] + 0.03 and ylo < gb[3] and yhi > gb[2]:
                    return False
        return True

    def rec(k, assign, cost):
        nonlocal best
        if best and cost >= best[0]:
            return
        if k == len(items):
            best = (cost, list(assign)); return
        for lev, side in sorted(opts, key=lambda o: (abs(o[0]), o[1] != "R")):
            assign.append((lev, side))
            if ok(k, assign):
                rec(k + 1, assign, cost + abs(lev) + (0.6 if side == "L" else 0))
            assign.pop()

    rec(0, [], 0.0)
    return best


ev_sol = solve(ev_items, [0.5, 1.55, 2.35], upward=True)
la_sol = solve(la_items, [-0.85, -1.5, -2.15, -2.75], upward=False)
assert ev_sol and la_sol, "no feasible layout"

for it, (lev, side) in zip(ev_items, ev_sol[1]):
    x = it["t"] + 0.05 if side == "R" else it["t"] - 0.05
    ha = "left" if side == "R" else "right"
    ax.plot([it["t"], it["t"]], [BAR, lev + it["h"]], color=POL, lw=0.6, zorder=1)
    ax.plot([it["t"]], [BAR], marker="o", ms=3.4, color=POL, mec="white", mew=0.5, zorder=4)
    ax.text(x, lev + it["h"], it["head"], ha=ha, va="top", fontsize=6.0, weight="bold", color=POL)
    ax.text(x, lev, it["body"], ha=ha, va="bottom", fontsize=6.0, color=fs.INK, linespacing=1.0)
for it, (lev, side) in zip(la_items, la_sol[1]):
    x = it["t"] + 0.05 if side == "R" else it["t"] - 0.05
    ha = "left" if side == "R" else "right"
    ax.plot([it["t"], it["t"]], [-BAR, lev], color=EO, lw=0.55, zorder=1)
    ax.plot([it["t"]], [-BAR], marker="v", ms=3.4, color=EO, mec="white", mew=0.4, zorder=4)
    ax.text(x, lev, it["name"], ha=ha, va="center", fontsize=6.0, color=EO)

if __name__ == "__main__":
    print("events:", ev_sol[1]); print("launches:", la_sol[1])
    fs.check_overlaps(fig)
    fig.savefig("paper/figures/fig4_timeline.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig("paper/figures/fig4_timeline.png", dpi=220, bbox_inches="tight", pad_inches=0.02)
