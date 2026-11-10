"""Build the web reader docs/paper/ from paper/paper.tex (same text and numbers as the PDF).

The LaTeX source is preprocessed first: the \\input files are inlined, the generated numbers in
paper/sim_numbers.tex are substituted, cleveref references become linked "Figure 2" / "Section 9"
text numbered as in the PDF, and figures point at the PNG versions. pandoc then renders it with
paper/reader.html: masthead, abstract, a results strip whose numbers come from sim_numbers.tex,
contents, numbered sections and the reference list. The PDF and the figures it uses are copied next
to the page; GitHub Pages serves docs/ at https://thanatchon36.github.io/from-space-to-sediment/.

Usage (from the repository root): python scripts/build_web.py      Requires pandoc on PATH.
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
OUT = ROOT / "docs" / "paper"
REPO_URL = "https://github.com/thanatchon36/from-space-to-sediment"
PAPER_URL = "https://thanatchon36.github.io/from-space-to-sediment/paper/"

# (label, style, finding, detail) with {macro} placeholders filled from sim_numbers.tex.
# style: "ref" = simulation result, "null" = pending.
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

KIND = {"sec": "Section", "fig": "Figure", "tab": "Table", "eq": "Equation"}


def die(msg: str) -> None:
    sys.exit(f"build_web: {msg}")


def read_numbers(path: Path) -> dict[str, str]:
    nums = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", path.read_text(encoding="utf-8")))
    if not nums:
        die(f"no \\newcommand values in {path}")
    return nums


def inline_inputs(tex: str) -> str:
    def sub(m: re.Match) -> str:
        f = PAPER / (m.group(1) if m.group(1).endswith(".tex") else m.group(1) + ".tex")
        if not f.exists():
            die(f"\\input{{{m.group(1)}}}: {f} not found")
        return inline_inputs(f.read_text(encoding="utf-8"))
    return re.sub(r"\\input\{([^}]+)\}", sub, tex)


def substitute_numbers(tex: str, nums: dict[str, str]) -> str:
    tex = re.sub(r"\\newcommand\{\\\w+\}\{[^}]*\}\n?", "", tex)
    # longest names first so \typeI does not eat \typeILo
    for name in sorted(nums, key=len, reverse=True):
        tex = re.sub(r"\\" + name + r"(?![A-Za-z])(\{\})?", lambda m, v=nums[name]: v, tex)
    return tex


def number_labels(body: str) -> dict[str, str]:
    """Label -> number, in source order as LaTeX assigns them (sections, floats, equations)."""
    counters = {"sec": 0, "fig": 0, "tab": 0, "eq": 0}
    labels: dict[str, str] = {}
    pending = None  # counter whose label is expected next
    token = re.compile(
        r"\\section(\*?)\{|\\begin\{(figure|table|equation)\}|\\label\{([^}]+)\}"
    )
    for m in token.finditer(body):
        if m.group(0).startswith("\\section"):
            if m.group(1):
                pending = None
                continue
            counters["sec"] += 1
            pending = "sec"
        elif m.group(2):
            kind = {"figure": "fig", "table": "tab", "equation": "eq"}[m.group(2)]
            counters[kind] += 1
            pending = kind
        else:
            label = m.group(3)
            prefix = label.split(":", 1)[0]
            if prefix not in counters:
                continue  # e.g. subsection labels; not referenced
            if prefix != pending:
                die(f"label {label} does not follow its {KIND[prefix].lower()}")
            labels[label] = str(counters[prefix])
    return labels


def replace_crefs(body: str, labels: dict[str, str]) -> str:
    def link(label: str) -> str:
        if label not in labels:
            die(f"\\cref to unknown label {label}")
        return f"\\hyperref[{label}]{{{labels[label]}}}"

    def join(parts: list[str]) -> str:
        return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]

    def sub(m: re.Match) -> str:
        groups: list[tuple[str, list[str]]] = []
        for label in [x.strip() for x in m.group(1).split(",")]:
            kind = label.split(":", 1)[0]
            if kind not in KIND:
                die(f"\\cref to {label}: unknown prefix")
            if groups and groups[-1][0] == kind:
                groups[-1][1].append(label)
            else:
                groups.append((kind, [label]))
        words = [
            (KIND[k] + ("s" if len(ls) > 1 else "")) + "~" + join([link(x) for x in ls]) for k, ls in groups
        ]
        return join(words)

    return re.sub(r"\\[cC]ref\{([^}]+)\}", sub, body)


def tag_equations(body: str, labels: dict[str, str]) -> str:
    """Give each numbered equation an anchor for the cross-references."""
    def sub(m: re.Match) -> str:
        inner = m.group(1)
        lab = re.search(r"\\label\{([^}]+)\}", inner)
        if not lab:
            die("unlabelled equation; cannot number it consistently")
        inner = inner.replace(lab.group(0), "").rstrip()
        n = labels[lab.group(1)]
        # pandoc's MathML drops \\tag, so the number is added after rendering (number_equations)
        return f"\\hypertarget{{{lab.group(1)}}}{{}}\n\\begin{{equation*}}{inner}\n\\end{{equation*}}"
    return re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", sub, body, flags=re.DOTALL)


def plain_tables(body: str) -> str:
    """tabularx with the paper's custom L{}/Y column types -> plain tabular, which pandoc reads.

    pandoc silently drops the tabularx tables otherwise; in the browser they size to their content.
    """
    def spec(m: re.Match) -> str:
        s = m.group(1)
        s = s.replace("@{}", "")
        s = re.sub(r">\{[^{}]*\}", "", s)
        s = re.sub(r"[LpPmb]\{[^{}]*\}", "l", s)
        s = re.sub(r"[XY]", "l", s)
        if not re.fullmatch(r"[lcr|]+", s):
            die(f"cannot simplify table column spec {m.group(1)!r} (got {s!r})")
        return "\\begin{tabular}{" + s.replace("|", "") + "}"

    # the spec can hold one level of nested braces, e.g. >{\centering\arraybackslash}p{2.95cm}
    body = re.sub(r"\\begin\{tabularx\}\{\\textwidth\}\{((?:[^{}]|\{[^{}]*\})*)\}", spec, body)
    return body.replace("\\end{tabularx}", "\\end{tabular}")


def preprocess(nums: dict[str, str]) -> tuple[str, dict[str, object]]:
    tex = inline_inputs((PAPER / "paper.tex").read_text(encoding="utf-8"))
    tex = substitute_numbers(tex, nums)
    leftover = sorted(set(re.findall(r"\\(" + "|".join(map(re.escape, nums)) + r")(?![A-Za-z])", tex)))
    if leftover:
        die(f"unresolved number macros: {leftover}")

    meta: dict[str, object] = {}
    title = re.search(r"\\title\{(.*?)\}\n", tex).group(1)
    head, _, sub = title.partition(": ")
    meta["title"], meta["subtitle"] = head, sub
    meta["author"] = re.sub(r"\\textbf\{([^}]*)\}", r"\1", re.search(r"\\author\{(.*)\}\n", tex).group(1))
    meta["date"] = re.search(r"\\date\{(.*?)\}", tex).group(1)
    kw = re.search(r"\\keywords\{(.*?)\}\n", tex)
    if not kw:
        die("\\keywords not found")
    meta["keywords"] = [k.strip() for k in kw.group(1).split("\\textperiodcentered{}")]
    tex = tex.replace(kw.group(0), "")

    labels = number_labels(tex[tex.index("\\begin{document}"):])
    meta["labels"] = labels
    tex = tag_equations(tex, labels)
    tex = replace_crefs(tex, labels)
    tex = plain_tables(tex)
    if tex.count("\\begin{tabular}") != len([k for k in labels if k.startswith("tab:")]):
        die("table count does not match the number of table labels")
    tex = re.sub(r"(\\includegraphics(?:\[[^\]]*\])?\{figures/[\w.-]+)\.pdf\}", r"\1.png}", tex)
    # pandoc has no use for the arXiv style or the PDF float tuning
    tex = re.sub(r"\\(?:re)?newcommand\{\\(?:shorttitle|headeright|topfraction|bottomfraction|textfraction|floatpagefraction|arraystretch)\}\{[^}]*\}\n", "", tex)
    # citeproc appends the reference list at the end of the document, under this heading
    tex, n = re.subn(r"\\bibliographystyle\{\w+\}\s*\\bibliography\{references\}", r"\\section*{References}", tex)
    if n != 1:
        die("\\bibliography{references} not found")
    tex = re.sub(r"\\title\{.*?\}\n", "\\\\title{" + head + "}\n", tex, count=1)
    tex = re.sub(r"\\author\{.*\}\n", "\\\\author{" + meta["author"] + "}\n", tex, count=1)
    return tex, meta


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
    if n != sum(k.startswith("eq:") for k in labels):
        die(f"numbered {n} equations, the paper has {sum(k.startswith('eq:') for k in labels)}")
    return page


def web_images(page: str) -> str:
    def img(m: re.Match) -> str:
        tag = re.sub(r'\s(?:style|width|height)="[^"]*"', "", m.group(0))
        return tag.replace("<img ", '<img loading="lazy" ', 1)
    return re.sub(r"<img\b[^>]*>", img, page)


def fill(s: str, nums: dict[str, str]) -> str:
    try:
        return s.format(**nums).replace("--", "–")
    except KeyError as e:
        die(f"results strip refers to unknown number {e}")


def build() -> Path:
    if shutil.which("pandoc") is None:
        die("pandoc not found; install pandoc to build the web reader")
    nums = read_numbers(PAPER / "sim_numbers.tex")
    tex, meta = preprocess(nums)

    args = [
        "pandoc", "--from=latex", "--to=html5", "--mathml", "--wrap=none", "--standalone",
        "--citeproc", "--bibliography=references.bib", "--template=reader.html",
        "--number-sections", "--toc", "--toc-depth=1",
        "--metadata=pagetitle:From Space to Sediment",
        f"--metadata=subtitle:{meta['subtitle']}",
        f"--metadata=date:{meta['date']}",
        "--metadata=link-citations:true",
        (
            "--metadata=description:Preprint: multi-sensor satellite screening of e-waste sites in Thailand "
            "and attribution of river contamination in the Bang Pakong basin."
        ),
    ]
    args += [f"--metadata=keywords:{k}" for k in meta["keywords"]]
    run = subprocess.run(args, input=tex, capture_output=True, text=True, cwd=str(PAPER))
    if run.returncode != 0:
        die(f"pandoc failed:\n{run.stderr}")
    for line in run.stderr.splitlines():
        print(f"pandoc: {line}", file=sys.stderr)
    page = run.stdout

    page = number_captions(page)
    page = number_equations(page, meta["labels"])
    page = web_images(page)
    page = re.sub(
        r"<table\b[^>]*>\s*<caption>(.*?)</caption>(.*?)</table>",
        r'<div class="tbl"><p class="tcap">\1</p><div class="tscroll"><table>\2</table></div></div>',
        page, flags=re.DOTALL,
    )
    page = re.sub(r"<colgroup>.*?</colgroup>\s*", "", page, flags=re.DOTALL)

    items = "\n".join(
        f'<li class="r r-{style}"><span class="r-id">{html.escape(label)}</span>'
        f'<span class="r-text">{html.escape(fill(finding, nums))}<small>{html.escape(fill(detail, nums))}</small></span></li>'
        for label, style, finding, detail in RESULTS
    )
    actions = (
        '<li><a href="paper.pdf">Download PDF</a></li>'
        f'<li><a href="{REPO_URL}">Code and replication</a></li>'
    )
    full_title = f"{meta['title']}: {meta['subtitle']}"
    bib = (
        "@misc{chongmankhong2026space,\n"
        "  author       = {Chongmankhong, Thanatchon},\n"
        f"  title        = {{{full_title}}},\n"
        "  year         = {2026},\n"
        "  howpublished = {Preprint},\n"
        f"  url          = {{{PAPER_URL}}}\n"
        "}"
    )
    for marker, value in (
        ("<!--ACTIONS-->", actions),
        ("<!--RESULTS-NOTE-->", (
            "Headline numbers from the implementation checks and simulations (paper/sim_numbers.tex). They use the "
            "real Bang Pakong river network with synthetic sites and stations, so they validate the method, not "
            "any real site. Amber: simulation results; grey: pending."
        )),
        ("<!--RESULTS-->", items),
        ("<!--CITE-->", f"<h2>How to cite</h2><pre><code>{html.escape(bib)}</code></pre>"),
        ("<!--COLOPHON-->", (
            "<p>Rendered from <code>paper/paper.tex</code> by <code>scripts/build_web.py</code>. Every number "
            "comes from <code>paper/sim_numbers.tex</code>, the same file the PDF uses; the PDF is "
            "authoritative.</p>"
        )),
    ):
        if marker not in page:
            die(f"reader.html lacks {marker}")
        page = page.replace(marker, value)

    for what, found, want in (
        ("figures", page.count("<figure"), sum(k.startswith("fig:") for k in meta["labels"])),
        ("tables", page.count('class="tbl"'), sum(k.startswith("tab:") for k in meta["labels"])),
    ):
        if found != want:
            die(f"rendered {found} {what}, the paper has {want}")
    raw = re.findall(r"\\[A-Za-z]+", re.sub(r"<math\b.*?</math>", "", page, flags=re.DOTALL))
    if raw:
        die(f"raw LaTeX left in the page: {sorted(set(raw))}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    shutil.copyfile(PAPER / "paper.pdf", OUT / "paper.pdf")
    figs = OUT / "figures"
    if figs.exists():
        shutil.rmtree(figs)
    figs.mkdir()
    used = sorted(set(re.findall(r'src="figures/([\w.-]+)"', page)))
    for name in used:
        src = PAPER / "figures" / name
        if not src.exists():
            die(f"figure {src} missing")
        shutil.copyfile(src, figs / name)
    print(f"wrote {OUT / 'index.html'} ({len(used)} figures)")
    return OUT / "index.html"


if __name__ == "__main__":
    build()
