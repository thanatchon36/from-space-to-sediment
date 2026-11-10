"""Figure 8 - Simulation-based validation (synthetic sites and stations on the real Bang Pakong network).

Also writes the numbers the paper quotes to results/sim_out/paper_numbers.json (resolved into the
{{sim:<name>}} placeholders of paper/paper.md at build time) and Table 5 to paper/tables/tab_validation.tex."""
import glob
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import figstyle as fs

fs.apply_style()
SIM = "results/sim_out/"
OUT_TAB = "paper/tables/"
df = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(SIM + "sim_results_s*.csv"))], ignore_index=True)
alt, null = df[df["pi"] > 0], df[df["pi"] == 0]
LAMS = [3.0, 8.0, 20.0]
NAMES = {3.0: "Three", 8.0: "Eight", 20.0: "Twenty"}
COL = {3.0: "#C8553D", 8.0: "#2E86AB", 20.0: "#3B8B5A"}
GRID = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
LEVELS = [("possible", "possible_n", "possible_tp", "possible_tp_attr", "\u2265 2 of 4"),
          ("count", "probable_n", "probable_tp", "probable_tp_attr", "\u2265 3 of 4\n(count rule)"),
          ("strict", "probable_c3req_n", "probable_c3req_tp", "probable_c3req_tp_attr", "C1+C2+C3\n(strict rule)"),
          ("attributed", "attributed_n", "attributed_tp", "attributed_tp_attr", "C1\u2013C4")]


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, c - h, c + h)


S = {}
for lam in LAMS:
    d = alt[alt["lam_true"] == lam]
    r = {"reps": len(d),
         "lam_within": np.mean((d["lam_sel"] >= lam / 2.5) & (d["lam_sel"] <= lam * 2.5)),
         "power": np.mean(d["p_perm"] < 0.05),
         "attrib_share": d["n_attributable_unreg"].sum() / max(1, d["n_true_unreg"].sum())}
    for key, nc, tc, ac, _ in LEVELS:
        r[f"prec_{key}"] = wilson(d[tc].sum(), d[nc].sum())
        r[f"rec_{key}"] = wilson(d[ac].sum(), d["n_attributable_unreg"].sum())
    r["c3_tpr"] = wilson(d["c3_tp"].sum(), d["c3_pos"].sum())
    r["c3_fpr"] = wilson(d["c3_fp"].sum(), d["c3_neg"].sum())
    r["c3_fpr_conf"] = wilson(d["c3_fp_conf"].sum(), d["c3_neg_conf"].sum())
    S[lam] = r
type1 = wilson(int((null["p_perm"] < 0.05).sum()), int(null["p_perm"].notna().sum()))
mism = {c: int(round(((1 - df[c]) * 60).sum())) for c in df.columns if c.startswith("flag_acc_")}

fig = plt.figure(figsize=(6.5, 4.85))
axA = fig.add_axes([0.07, 0.60, 0.40, 0.33])
axB = fig.add_axes([0.585, 0.60, 0.40, 0.33])
axC = fig.add_axes([0.07, 0.115, 0.40, 0.33])
axD = fig.add_axes([0.585, 0.115, 0.40, 0.33])

# (a) selected lambda
w = 0.26
for k, lam in enumerate(LAMS):
    sel = alt[alt["lam_true"] == lam]["lam_sel"]
    axA.bar(np.arange(6) + (k - 1) * w, [np.mean(sel == g) for g in GRID], width=w, color=COL[lam],
            edgecolor="white", lw=0.3, label=f"\u03bb$_{{true}}$ = {lam:g} km")
    near = GRID.index(min(GRID, key=lambda g: abs(np.log(g / lam))))
    axA.plot(near + (k - 1) * w, 1.03, marker="v", ms=4, color=COL[lam], clip_on=False)
axA.set_xticks(range(6)); axA.set_xticklabels([f"{g:g}" for g in GRID])
axA.set_xlabel("Selected \u03bb (km)", fontsize=6.6); axA.set_ylabel("Share of replicates", fontsize=6.6)
axA.set_ylim(0, 1.0)
axA.legend(loc="upper left", fontsize=5.9, handlelength=1.0, borderaxespad=0.2, labelspacing=0.3)
axA.set_title("a   \u03bb recovery", fontsize=7, weight="bold", loc="left", pad=9)

# (b) permutation p-values
for lam in LAMS:
    p = np.sort(alt[alt["lam_true"] == lam]["p_perm"].dropna())
    axB.step(p, np.arange(1, len(p) + 1) / len(p), where="post", color=COL[lam], lw=1.1)
p0 = np.sort(null["p_perm"].dropna())
axB.step(p0, np.arange(1, len(p0) + 1) / len(p0), where="post", color="#333333", lw=1.1, ls=(0, (3, 1.5)))
axB.plot([0, 1], [0, 1], color="#BBBBBB", lw=0.6, zorder=0)
axB.axvline(0.05, color="#777777", lw=0.6, ls=(0, (1, 1.5)))
axB.set_xlim(0, 1); axB.set_ylim(0, 1.0)
axB.set_xlabel("Permutation p-value", fontsize=6.6); axB.set_ylabel("Cumulative share", fontsize=6.6)
hand = [Line2D([], [], color=COL[l], lw=1.1) for l in LAMS] + \
       [Line2D([], [], color="#333333", lw=1.1, ls=(0, (3, 1.5)))]
lab = [f"\u03bb$_{{true}}$ = {l:g} km" for l in LAMS] + [f"null (type I error {type1[0]*100:.1f}%)"]
axB.legend(hand, lab, loc="lower right", fontsize=5.9, handlelength=1.6, borderaxespad=0.2, labelspacing=0.3)
axB.set_title("b   Association test", fontsize=7, weight="bold", loc="left", pad=9)

# (c) precision and recall by evidence level
x = np.arange(len(LEVELS))
for k, lam in enumerate(LAMS):
    r = S[lam]; xs = x + (k - 1) * 0.22
    for kind, marker, mfc in (("prec", "o", COL[lam]), ("rec", "s", "white")):
        v = [r[f"{kind}_{key}"] for key, *_ in LEVELS]
        axC.errorbar(xs, [t[0] for t in v], yerr=[[t[0] - t[1] for t in v], [t[2] - t[0] for t in v]],
                     fmt=marker, ms=3.4 if marker == "o" else 3.0, mfc=mfc, color=COL[lam],
                     elinewidth=0.7, capsize=1.4)
axC.set_xticks(x); axC.set_xticklabels([lv[4] for lv in LEVELS], fontsize=6.0, linespacing=1.0)
axC.set_ylim(0, 1.05); axC.set_ylabel("Proportion", fontsize=6.6)
axC.legend([Line2D([], [], marker="o", ls="none", color="#555555", ms=3.4),
            Line2D([], [], marker="s", ls="none", mfc="white", color="#555555", ms=3.0)],
           ["precision", "recall (attributable sources)"], loc="lower left", fontsize=5.9,
           borderaxespad=0.2, handletextpad=0.3)
axC.set_title("c   Evidence levels", fontsize=7, weight="bold", loc="left", pad=9)

# (d) C3 rates
cats = [("c3_tpr", "true sources"), ("c3_fpr", "non-sources"), ("c3_fpr_conf", "non-sources,\nconfounder only")]
for k, lam in enumerate(LAMS):
    v = [S[lam][c] for c, _ in cats]; xs = np.arange(3) + (k - 1) * 0.26
    axD.bar(xs, [t[0] for t in v], width=0.26, color=COL[lam], edgecolor="white", lw=0.3)
    axD.errorbar(xs, [t[0] for t in v], yerr=[[max(0, t[0] - t[1]) for t in v], [t[2] - t[0] for t in v]],
                 fmt="none", ecolor="#333333", elinewidth=0.6, capsize=1.3)
axD.set_xticks(range(3)); axD.set_xticklabels([t for _, t in cats], fontsize=6.0, linespacing=1.0)
axD.set_ylim(0, 1.0); axD.set_ylabel("Share meeting C3", fontsize=6.6)
axD.set_title("d   Geochemical criterion C3", fontsize=7, weight="bold", loc="left", pad=9)
for ax in (axA, axB, axC, axD):
    ax.tick_params(labelsize=6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

# ---------------- numbers for the paper and Table 5 ----------------------------------------
net = json.load(open(SIM + "network_checks.json"))
pct = lambda v, nd=0: f"{100 * v:.{nd}f}"
NUM = {}  # name -> text, used as {{sim:name}} in paper/paper.md


def mac(name, value):
    NUM[name] = str(value)

mac("simReps", S[3.0]["reps"]); mac("simRepsTotal", len(df))
mac("typeI", pct(type1[0], 1)); mac("typeILo", pct(type1[1], 1)); mac("typeIHi", pct(type1[2], 1))
for lam in LAMS:
    n, r = NAMES[lam], S[lam]
    mac(f"lamWithin{n}", pct(r["lam_within"])); mac(f"power{n}", pct(r["power"]))
    mac(f"attribShare{n}", pct(r["attrib_share"]))
    for key, *_ in LEVELS:
        mac(f"prec{key.capitalize()}{n}", f"{r[f'prec_{key}'][0]:.2f}")
        mac(f"rec{key.capitalize()}{n}", f"{r[f'rec_{key}'][0]:.2f}")
    mac(f"cthreeTpr{n}", f"{r['c3_tpr'][0]:.2f}"); mac(f"cthreeFpr{n}", f"{r['c3_fpr'][0]:.2f}")
    mac(f"cthreeFprConf{n}", f"{r['c3_fpr_conf'][0]:.2f}")


def rng(key):
    v = [S[l][key][0] for l in LAMS]
    return f"{min(v):.2f}--{max(v):.2f}"


for key, *_ in LEVELS:
    mac(f"rngPrec{key.capitalize()}", rng(f"prec_{key}")); mac(f"rngRec{key.capitalize()}", rng(f"rec_{key}"))
mac("rngCthreeTpr", rng("c3_tpr")); mac("rngCthreeFpr", rng("c3_fpr")); mac("rngCthreeFprConf", rng("c3_fpr_conf"))
mac("flagMismatches", sum(mism.values()))
mac("netReaches", net["n_reaches"]); mac("netLengthKm", f"{net['total_length_km']:.0f}")
mac("netMaxOutletKm", f"{net['max_dist_to_outlet_km']:.0f}"); mac("netPairs", net["pairs"])
mac("netShortMed", f"{100 * (1 - net['length_ratio_median']):.1f}")
mac("netShortPfive", f"{100 * (1 - net['length_ratio_p05']):.1f}")
mac("netLongPninetyfive", f"{100 * (net['length_ratio_p95'] - 1):.1f}")
with open(SIM + "paper_numbers.json", "w") as f:
    json.dump({"_comment": "generated by paper/figures_src/fig8_simulation.py - do not edit", **NUM}, f, indent=1)
    f.write("\n")

fmt = lambda t: f"{t[0]:.2f} [{t[1]:.2f}--{t[2]:.2f}]"
rows = [(r"Selected $\lambda$ within a factor of 2.5 of $\lambda_{\mathrm{true}}$", [pct(S[l]["lam_within"]) + r"\%" for l in LAMS]),
        (r"Power of the association test ($p<0.05$)", [pct(S[l]["power"]) + r"\%" for l in LAMS]),
        (r"Precision, possible ($\geq$2 criteria)", [fmt(S[l]["prec_possible"]) for l in LAMS]),
        (r"Precision, probable, count rule ($\geq$3 criteria)", [fmt(S[l]["prec_count"]) for l in LAMS]),
        (r"Precision, probable, strict rule (C1--C3)", [fmt(S[l]["prec_strict"]) for l in LAMS]),
        (r"Precision, attributed (C1--C4)", [fmt(S[l]["prec_attributed"]) for l in LAMS]),
        (r"Recall, probable, strict rule", [fmt(S[l]["rec_strict"]) for l in LAMS]),
        (r"Recall, attributed", [fmt(S[l]["rec_attributed"]) for l in LAMS]),
        (r"C3 met, true sources", [fmt(S[l]["c3_tpr"]) for l in LAMS]),
        (r"C3 met, non-sources", [fmt(S[l]["c3_fpr"]) for l in LAMS]),
        (r"C3 met, non-sources exposed only to confounders", [fmt(S[l]["c3_fpr_conf"]) for l in LAMS])]
T = [r"% generated by paper/figures_src/fig8_simulation.py - do not edit",
     r"\begin{table}[t]", r"\centering",
     r"\caption{Simulation-based validation on the real Bang Pakong network topology with synthetic sites and "
     r"stations ("
     + NUM["simReps"] + r" replicates per scenario; 95\% Wilson intervals \citep{wilson1927} in brackets). Precision "
     r"and recall refer to unregistered candidate sites; recall is the share of attributable sources (true, "
     r"hydrologically connected sources with a station within $3\lambda_{\mathrm{true}}$ downstream) that reach the "
     r"level. Under the null scenario the association test rejected in "
     + NUM["typeI"] + r"\% of replicates (95\% interval " + NUM["typeILo"] + "--" + NUM["typeIHi"] + r"\%).}",
     r"\label{tab:validation}", r"\footnotesize",
     r"\begin{tabularx}{\textwidth}{@{}Y>{\centering\arraybackslash}p{2.95cm}>{\centering\arraybackslash}p{2.95cm}"
     r">{\centering\arraybackslash}p{2.95cm}@{}}", r"\toprule",
     r"Metric & $\lambda_{\mathrm{true}}=3$~km & $\lambda_{\mathrm{true}}=8$~km & $\lambda_{\mathrm{true}}=20$~km\\",
     r"\midrule"]
T += [f"{name} & " + " & ".join(vals) + r"\\" for name, vals in rows]
T += [r"\bottomrule", r"\end{tabularx}", r"\end{table}"]
open(OUT_TAB + "tab_validation.tex", "w").write("\n".join(T) + "\n")

if __name__ == "__main__":
    fs.check_overlaps(fig)
    fig.savefig("paper/figures/fig8_simulation.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig("paper/figures/fig8_simulation.png", dpi=220, bbox_inches="tight", pad_inches=0.02)
    print("replicates:", df.groupby(["lam_true", "pi"]).size().to_dict(), "| flag mismatches:", mism)
    print("type I error:", [round(v, 3) for v in type1])
    for lam in LAMS:
        r = S[lam]
        print(f"lam={lam:g}: within={r['lam_within']:.2f} power={r['power']:.2f} attrib_share={r['attrib_share']:.2f} | "
              + " ".join(f"{k}: P={r['prec_'+k][0]:.2f} R={r['rec_'+k][0]:.2f}" for k, *_ in LEVELS)
              + f" | C3 tpr={r['c3_tpr'][0]:.2f} fpr={r['c3_fpr'][0]:.2f} conf={r['c3_fpr_conf'][0]:.2f}")
