"""Shared matplotlib style and a text-overlap checker for the paper figures."""
import itertools
import matplotlib as mpl

FONT = "Liberation Sans"

def apply_style():
    mpl.rcParams.update({
        "font.family": FONT,
        "font.size": 7,
        "axes.linewidth": 0.6,
        "axes.edgecolor": "#333333",
        "axes.labelsize": 7,
        "axes.titlesize": 8,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "legend.fontsize": 6.5,
        "legend.frameon": False,
        "hatch.linewidth": 0.45,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "mathtext.fontset": "custom",
        "mathtext.rm": FONT,
        "mathtext.it": FONT + ":italic",
        "mathtext.bf": FONT + ":bold",
        "savefig.dpi": 400,
    })

# Palette (colour-blind safe, print friendly)
C_EAST = "#E8A15B"      # industrial-scale (East)
C_EAST_D = "#A84F12"
C_NE = "#9A8FC9"        # household-scale (Northeast)
C_NE_D = "#4B3F8C"
C_WATER = "#E3EDF5"
C_RIVER = "#7FAACB"
C_RIVER_D = "#1F5F9A"
C_LAND_TH = "#FBFAF6"
C_LAND_OTHER = "#E7E5E0"
C_BORDER = "#5A5A5A"
C_GRID = "#9AA5AE"
INK = "#222222"
MUTED = "#6B6B6B"

FAMILY_COLOURS = {
    "Thermal": "#C8553D",
    "Optical": "#2E86AB",
    "SAR": "#6C5B7B",
    "Night lights": "#D9A400",
    "Imaging spectroscopy": "#3B8B5A",
    "Atmospheric": "#8C8C8C",
    "Hydrology": "#16817A",
}


def _boxes(fig, renderer, extra_artists=()):
    boxes = []
    for t in fig.findobj(mpl.text.Text):
        if not t.get_visible() or not t.get_text().strip():
            continue
        if t.get_alpha() == 0:
            continue
        # skip texts inside legends (checked separately by matplotlib layout)
        bb = t.get_window_extent(renderer)
        if bb.width == 0 or bb.height == 0:
            continue
        boxes.append((t, bb))
    for a in extra_artists:
        boxes.append((a, a.get_window_extent(renderer)))
    return boxes


def check_overlaps(fig, pad=0.5, extra_artists=(), ignore=lambda a, b: False, verbose=True):
    """Return list of overlapping text pairs (display-space bounding boxes)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    boxes = _boxes(fig, r, extra_artists)
    hits = []
    for (a, ba), (b, bb) in itertools.combinations(boxes, 2):
        if ignore(a, b):
            continue
        if (ba.x0 + pad < bb.x1 and bb.x0 + pad < ba.x1 and
                ba.y0 + pad < bb.y1 and bb.y0 + pad < ba.y1):
            hits.append((a, b))
    W, H = fig.bbox.width, fig.bbox.height
    out = [(t, bb) for t, bb in boxes if bb.x0 < -1 or bb.y0 < -1 or bb.x1 > W + 1 or bb.y1 > H + 1]
    if verbose:
        for a, b in hits:
            ta = a.get_text() if hasattr(a, "get_text") else str(a)
            tb = b.get_text() if hasattr(b, "get_text") else str(b)
            print(f"  OVERLAP: {ta!r} <-> {tb!r}")
        for t, bb in out:
            print(f"  OUTSIDE FIGURE: {t.get_text()!r} {bb}")
        print(f"  overlap check: {len(boxes)} labels, {len(hits)} overlaps, {len(out)} outside")
    return hits, out
