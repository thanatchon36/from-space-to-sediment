"""Build the web reader docs/paper/ from paper/paper.md (same text and numbers as the PDF).

The Markdown is filled exactly as for the PDF (paper_build.fill), then adapted for the browser:

- ``\\cref{...}`` becomes linked "Figure 2" / "Sections 5, 6 and 7" text, numbered as LaTeX numbers them;
- the raw LaTeX tables are converted to Markdown tables by pandoc (tabularx -> tabular first);
- numbered equations get an anchor and their number at the right (MathML has no \\tag);
- figures point at the PNG versions, and the reference list goes at the end.

pandoc renders the result with paper/reader.html: masthead, abstract, a results strip whose numbers come
from results/sim_out/paper_numbers.json, contents, numbered sections and the reference list. The PDF and
the figures it uses are copied next to the page; GitHub Pages serves docs/ at PAPER_URL.
Requires pandoc on PATH.
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import CONCEPT_DOI, DATA_URL, DOCS_DIR, PAPER_DIR, PAPER_URL, REPO_URL
from .paper_build import PaperBuildError, fill, load_numbers

OUT_DIR = DOCS_DIR / "paper"
KIND = {"sec": "Section", "fig": "Figure", "tab": "Table", "eq": "Equation"}
NBSP = "\u00a0"

# (label, style, finding, detail) with {name} filled from paper_numbers.json.
# style: "ref" = implementation check or simulation result, "null" = pending.
RESULTS = [
    (
        "Network check",
        "ref",
        "Exact along-network distances on {netReaches} real Bang Pakong reaches",
        "{netLengthKm} km of channel; {netPairs} random point pairs agree with merged path lines to within 1e-9 m",
    ),
    (
        "Attributed level",
        "ref",
        "Precision {rngPrecAttributed} when all four criteria (C1–C4) agree",
        "recall {rngRecAttributed} of attributable sources across the three decay-length scenarios",
    ),
    (
        "Evidence rule",
        "ref",
        "Requiring geochemistry (C1–C3) lifts probable precision from {rngPrecCount} to {rngPrecStrict}",
        "the original count-based rule (any three criteria) was too permissive",
    ),
    (
        "Association test",
        "ref",
        "Power {powerThree}%, {powerEight}% and {powerTwenty}% at λ = 3, 8 and 20 km",
        "type I error {typeI}% under the null (95% interval {typeILo}–{typeIHi}%), above the nominal 5%",
    ),
    (
        "Registry flags",
        "ref",
        "{flagMismatches} mismatches with the geometric truth in {simRepsTotal} simulated replicates",
        "registry, known-site and hard-negative flags use exact distance tests",
    ),
    (
        "Real data",
        "null",
        "Real-data results pending",
        "every number here comes from simulations on the real network with synthetic sites and stations",
    ),
]

LATEX_BLOCK = re.compile(r"```\{=latex\}\n(.*?)\n```", re.DOTALL)
EQUATION = re.compile(r"\\begin\{equation\}(.*?)\\end\{equation\}", re.DOTALL)


def _die(msg: str) -> None:
    raise PaperBuildError(f"paper_web: {msg}")


def number_labels(md: str) -> dict[str, str]:
    """Label -> number as LaTeX assigns them: numbered top-level sections, figures, tables, equations."""
    labels: dict[str, str] = {}
    sec = 0
    for m in re.finditer(r"^# (.*)$", md, re.M):
        if re.search(r"\{(?:[^}]*\s)?(?:-|\.unnumbered)(?:\s[^}]*)?\}\s*$", m.group(1)):
            continue
        sec += 1
        ident = re.search(r"\{#(sec:[\w-]+)", m.group(1))
        if ident:
            labels[ident.group(1)] = str(sec)
    for kind, pattern in (("fig", r"\{#(fig:[\w-]+)"), ("tab", r"\\label\{(tab:[\w-]+)\}"),
                          ("eq", r"\\label\{(eq:[\w-]+)\}")):
        for k, label in enumerate(re.findall(pattern, md), 1):
            labels[label] = str(k)
    return labels


def _cref_text(labels: dict[str, str], ids: str, link) -> str:
    def join(parts: list[str]) -> str:
        return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]

    groups: list[tuple[str, list[str]]] = []
    for label in [x.strip() for x in ids.split(",")]:
        kind = label.split(":", 1)[0]
        if kind not in KIND:
            _die(f"\\cref to {label}: unknown prefix")
        if label not in labels:
            _die(f"\\cref to unknown label {label}")
        if groups and groups[-1][0] == kind:
            groups[-1][1].append(label)
        else:
            groups.append((kind, [label]))
    return join([KIND[k] + ("s" if len(ls) > 1 else "") + NBSP + join([link(x) for x in ls]) for k, ls in groups])


def replace_crefs(md: str, labels: dict[str, str]) -> str:
    """\\cref in LaTeX blocks -> \\hyperref (pandoc's LaTeX reader makes it a link); elsewhere -> Markdown links."""
    def in_latex(block: re.Match) -> str:
        body = re.sub(
            r"\\[cC]ref\{([^}]+)\}",
            lambda m: _cref_text(labels, m.group(1), lambda x: f"\\hyperref[{x}]{{{labels[x]}}}"),
            block.group(1),
        )
        return "```{=latex}\n" + body + "\n```"

    md = LATEX_BLOCK.sub(in_latex, md)
    return re.sub(
        r"\\[cC]ref\{([^}]+)\}",
        lambda m: _cref_text(labels, m.group(1), lambda x: f"[{labels[x]}](#{x})"),
        md,
    )


def _plain_tabular(tex: str) -> str:
    """tabularx with the paper's L{}/Y column types -> plain tabular, which pandoc's LaTeX reader reads."""
    def spec(m: re.Match) -> str:
        s = m.group(1).replace("@{}", "")
        s = re.sub(r">\{[^{}]*\}", "", s)
        s = re.sub(r"[LpPmb]\{[^{}]*\}", "l", s)
        s = re.sub(r"[XY]", "l", s)
        if not re.fullmatch(r"[lcr|]+", s):
            _die(f"cannot simplify table column spec {m.group(1)!r} (got {s!r})")
        return "\\begin{tabular}{" + s.replace("|", "") + "}"

    # the spec can hold one level of nested braces, e.g. >{\centering\arraybackslash}p{2.95cm}
    tex = re.sub(r"\\begin\{tabularx\}\{\\textwidth\}\{((?:[^{}]|\{[^{}]*\})*)\}", spec, tex)
    return tex.replace("\\end{tabularx}", "\\end{tabular}")


def latex_tables_to_markdown(md: str) -> str:
    def convert(block: re.Match) -> str:
        tex = block.group(1)
        if "\\begin{table}" not in tex:
            _die("a raw LaTeX block that is not a table; the web reader cannot render it")
        run = subprocess.run(
            ["pandoc", "--from=latex", "--to=markdown", "--wrap=none"],
            input=_plain_tabular(tex), capture_output=True, text=True,
        )
        if run.returncode != 0 or "\\begin" in run.stdout:
            _die(f"pandoc could not convert a table:\n{run.stderr}{run.stdout[:500]}")
        return run.stdout.strip()

    return LATEX_BLOCK.sub(convert, md)


def anchor_equations(md: str, labels: dict[str, str]) -> str:
    """Each numbered equation -> anchor + display math (numbered after rendering, see number_equations)."""
    def sub(m: re.Match) -> str:
        inner = m.group(1)
        lab = re.search(r"\\label\{([^}]+)\}", inner)
        if not lab:
            _die("unlabelled equation; cannot number it consistently")
        inner = inner.replace(lab.group(0), "").strip()
        return f"[]{{#{lab.group(1)}}}$${inner}$$"
    return EQUATION.sub(sub, md)


def principles_list(md: str) -> str:
    """The (1)-(5) list is labelled (P1)-(P5) in the PDF; mark it so the reader's CSS does the same."""
    md, n = re.subn(r"((?:^\(\d\) .*\n)+)", r"::: plist\n\1:::\n", md, flags=re.M)
    if n != 1:
        _die(f"expected one (1)-(5) list, found {n}")
    return md


def prepare(md: str, labels: dict[str, str]) -> str:
    md = replace_crefs(md, labels)
    md = latex_tables_to_markdown(md)
    md = anchor_equations(md, labels)
    md = principles_list(md)
    md = md.replace("\\noindent ", "")
    md = re.sub(r"(\]\(figures/[\w.-]+)\.pdf\)", r"\1.png)", md)
    # citeproc puts the reference list into this div, after the unnumbered sections
    return md.rstrip() + "\n\n# References {-}\n\n::: {#refs}\n:::\n"


def number_captions(page: str) -> str:
    count = {"caption": 0, "figcaption": 0}

    def caption(m: re.Match) -> str:
        tag, attrs, para = m.group(1), m.group(2), m.group(3) or ""
        count[tag] += 1
        word = "Table" if tag == "caption" else "Figure"
        return f"<{tag}{attrs}>{para}<b>{word} {count[tag]}.</b> "

    return re.sub(r"<(caption|figcaption)(\b[^>]*)>(\s*<p>)?", caption, page)


def number_equations(page: str, labels: dict[str, str]) -> str:
    """Equation numbers at the right of each anchored display, as in the PDF."""
    def sub(m: re.Match) -> str:
        return (
            f'<span class="eq" id="{m.group(1)}"><span class="eq-math">{m.group(2)}</span>'
            f'<span class="eqno">({labels[m.group(1)]})</span></span>'
        )
    page, n = re.subn(r'<span id="(eq:[^"]+)"></span>\s*(<math display="block".*?</math>)', sub, page, flags=re.DOTALL)
    want = sum(k.startswith("eq:") for k in labels)
    if n != want:
        _die(f"numbered {n} equations, the paper has {want}")
    return page


def natbib_commas(page: str) -> str:
    """Author-year citations as natbib prints them in the PDF: (Robinson, 2009), not (Robinson 2009)."""
    def fix(m: re.Match) -> str:
        return re.sub(r"([A-Za-z.]|</span>)\s(\d{4}[a-z]?)(?=</a>|;|\))", r"\1, \2", m.group(0))
    # a parenthetical citation ends at ")</span>"; author names may sit in nested <span class="nocase">
    return re.sub(r'<span class="citation"[^>]*>\(.*?\)</span>', fix, page, flags=re.DOTALL)


def web_bibliography(bib: str) -> str:
    """Keep lowercase name particles with the surname for citeproc, as BibTeX/plainnat prints them:
    "van der Woerd and Wernand, 2015", not "Woerd and Wernand, 2015"."""
    particle = r"(?:van|von|der|den|de|du|da|di|la|le)"
    return re.sub(r"(?<=[{ ])(" + particle + r"(?: " + particle + r")* [A-Z][\w'-]*)(?=,)",
                  r"{\1}", bib)


GREEK = {"lambda": "λ", "tau": "τ", "pi": "π", "kappa": "κ", "gamma": "γ", "theta": "θ", "mu": "μ", "delta": "δ"}


def web_images(page: str) -> str:
    """Drop the PDF sizing, load lazily, and turn the TeX that pandoc copies into alt text into plain text."""
    def alt(m: re.Match) -> str:
        text = re.sub(r"\\([A-Za-z]+)", lambda g: GREEK.get(g.group(1), g.group(1)), m.group(1))
        return f'alt="{text.replace("{", "").replace("}", "")}"'

    def img(m: re.Match) -> str:
        tag = re.sub(r'\s(?:style|width|height)="[^"]*"', "", m.group(0))
        tag = re.sub(r'alt="([^"]*)"', alt, tag)
        return tag.replace("<img ", '<img loading="lazy" ', 1)
    return re.sub(r"<img\b[^>]*>", img, page)


def _strip_text(s: str, nums: dict[str, str]) -> str:
    try:
        return s.format(**nums).replace("--", "–")
    except KeyError as e:
        _die(f"results strip refers to unknown number {e}")
        raise


def build_web(paper_dir: Path = PAPER_DIR, out_dir: Path = OUT_DIR) -> Path:
    """paper.md -> filled Markdown -> out_dir/index.html (pandoc, reader.html), plus paper.pdf and figures."""
    if shutil.which("pandoc") is None:
        _die("pandoc not found; install pandoc to build the web reader")
    nums = load_numbers()
    md = fill((paper_dir / "paper.md").read_text(encoding="utf-8"), paper_dir, nums)
    labels = number_labels(md)
    md = prepare(md, labels)

    tmp = tempfile.TemporaryDirectory()
    bib = Path(tmp.name) / "references.bib"
    bib.write_text(web_bibliography((paper_dir / "references.bib").read_text(encoding="utf-8")), encoding="utf-8")
    run = subprocess.run(
        [
            "pandoc", "--from=markdown", "--to=html5", "--mathml", "--wrap=none", "--standalone",
            "--citeproc", f"--bibliography={bib}", "--template=reader.html",
            "--number-sections", "--toc", "--toc-depth=1",
            "--metadata=pagetitle:From Space to Sediment",
            "--metadata=link-citations:true",
            (
                "--metadata=description:Preprint: multi-sensor satellite screening of e-waste sites in Thailand "
                "and attribution of river contamination in the Bang Pakong basin."
            ),
        ],
        input=md, capture_output=True, text=True, cwd=str(paper_dir),
    )
    tmp.cleanup()
    if run.returncode != 0:
        _die(f"pandoc failed:\n{run.stderr}")
    for line in run.stderr.splitlines():
        print(f"pandoc: {line}", file=sys.stderr)
    page = run.stdout

    page = number_captions(page)
    page = number_equations(page, labels)
    page = natbib_commas(page)
    page = web_images(page)
    # The caption sits above the table, outside its sideways scroll, so it wraps at the text width.
    page = re.sub(
        r"<table\b[^>]*>\s*<caption>(.*?)</caption>(.*?)</table>",
        r'<div class="tbl"><p class="tcap">\1</p><div class="tscroll"><table>\2</table></div></div>',
        page, flags=re.DOTALL,
    )
    # Column widths are sized for the PDF page; in the browser the tables size to their content and scroll.
    page = re.sub(r"<colgroup>.*?</colgroup>\s*", "", page, flags=re.DOTALL)

    items = "\n".join(
        f'<li class="r r-{style}"><span class="r-id">{html.escape(label)}</span>'
        f'<span class="r-text">{html.escape(_strip_text(finding, nums))}'
        f'<small>{html.escape(_strip_text(detail, nums))}</small></span></li>'
        for label, style, finding, detail in RESULTS
    )
    actions = (
        '<li><a href="paper.pdf">Download PDF</a></li>'
        f'<li><a href="{REPO_URL}">Code and replication</a></li>'
        f'<li><a href="{DATA_URL}">Data (Hugging Face)</a></li>'
        f'<li><a href="https://doi.org/{CONCEPT_DOI}">Zenodo archive</a></li>'
    )
    title = re.search(r"<h1>(.*?)</h1>", page, re.DOTALL).group(1)
    subtitle = re.search(r'<p class="subtitle">(.*?)</p>', page, re.DOTALL)
    full_title = html.unescape(title + (": " + subtitle.group(1) if subtitle else ""))
    bib = (
        "@misc{chongmankhong2026space,\n"
        "  author       = {Chongmankhong, Thanatchon},\n"
        f"  title        = {{{full_title}}},\n"
        "  year         = {2026},\n"
        "  howpublished = {Preprint},\n"
        f"  doi          = {{{CONCEPT_DOI}}},\n"
        f"  url          = {{{PAPER_URL}}}\n"
        "}"
    )
    for marker, value in (
        ("<!--ACTIONS-->", actions),
        ("<!--RESULTS-NOTE-->", (
            "Headline numbers from the implementation checks and simulations, generated from the result files "
            "(results/sim_out/). They use the real Bang Pakong river network with synthetic sites and stations, "
            "so they validate the method, not any real site. Amber: simulation results; grey: pending."
        )),
        ("<!--RESULTS-->", items),
        ("<!--CITE-->", f"<h2>How to cite</h2><pre><code>{html.escape(bib)}</code></pre>"),
        ("<!--COLOPHON-->", (
            "<p>Rendered from <code>paper/paper.md</code> by <code>from_space_to_sediment.paper_web</code> "
            "(<code>make web</code>). Every number is resolved from <code>results/sim_out/paper_numbers.json</code> "
            "by the same placeholders as the PDF, which is authoritative.</p>"
        )),
    ):
        if marker not in page:
            _die(f"reader.html lacks {marker}")
        page = page.replace(marker, value)

    for what, found, want in (
        ("figures", page.count("<figure"), sum(k.startswith("fig:") for k in labels)),
        ("tables", page.count('class="tbl"'), sum(k.startswith("tab:") for k in labels)),
    ):
        if found != want:
            _die(f"rendered {found} {what}, the paper has {want}")
    raw = re.findall(r"\\[A-Za-z]+", re.sub(r"<math\b.*?</math>", "", page, flags=re.DOTALL))
    if raw:
        _die(f"raw LaTeX left in the page: {sorted(set(raw))}")
    left = re.findall(r"\{\{[^}]*\}\}|\[@[\w-]+|\?\?", page)
    if left:
        _die(f"unresolved placeholders, citations or references in the page: {sorted(set(left))}")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    pdf = paper_dir / "paper.pdf"
    if pdf.exists():
        shutil.copyfile(pdf, out_dir / "paper.pdf")
    figs = out_dir / "figures"
    if figs.exists():
        shutil.rmtree(figs)
    figs.mkdir()
    used = sorted(set(re.findall(r'src="figures/([\w.-]+)"', page)))
    for name in used:
        src = paper_dir / "figures" / name
        if not src.exists():
            _die(f"figure {src} missing")
        shutil.copyfile(src, figs / name)
    print(f"wrote {out_dir / 'index.html'} ({len(used)} figures)")
    return out_dir / "index.html"
