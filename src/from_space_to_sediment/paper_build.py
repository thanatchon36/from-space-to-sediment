"""Build the paper: paper/paper.md -> paper_build.md (filled) -> paper.tex (pandoc) -> paper.pdf (tectonic).

paper/paper.md is the only source. At build time:

- ``{{sim:<name>}}`` is replaced by a number from results/sim_out/paper_numbers.json, which
  paper/figures_src/fig8_simulation.py writes from the network checks and simulations;
- ``{{include:tables/<file>.tex}}`` is replaced by that LaTeX table (booktabs/tabularx, kept as raw LaTeX
  so the PDF tables keep their column layout);
- cross-references stay as ``\\cref{label}`` (cleveref in the PDF; paper_web turns them into links).

pandoc renders paper.tex with paper/template.tex (the arXiv layout of arxiv.sty) and natbib citations;
tectonic compiles it and runs BibTeX (plainnat). paper.tex is the self-contained arXiv source and is
pure ASCII, so it also compiles with pdfLaTeX; scripts/arxiv_bundle.py packs it with paper.bbl and
the figures. Requires pandoc and tectonic on PATH.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from .config import PAPER_DIR, RESULTS_DIR

NUMBERS = RESULTS_DIR / "paper_numbers.json"
# characters pandoc leaves as Unicode in LaTeX output -> ASCII LaTeX (pdfLaTeX/arXiv and the T1 fonts)
TEX_ASCII = {"\u2009": "\\,", "\u00a0": "~", "\u00b5": "\\textmu{}", "\u00b0": "\\textdegree{}"}


class PaperBuildError(RuntimeError):
    pass


def load_numbers(path: Path = NUMBERS) -> dict[str, str]:
    if not path.exists():
        raise PaperBuildError(f"{path} not found; run paper/figures_src/fig8_simulation.py (make figures)")
    nums = json.loads(path.read_text(encoding="utf-8"))
    nums.pop("_comment", None)
    return {k: str(v) for k, v in nums.items()}


def fill(text: str, paper_dir: Path = PAPER_DIR, numbers: dict[str, str] | None = None) -> str:
    """Resolve every {{...}} placeholder; fail on anything left unresolved."""
    nums = load_numbers() if numbers is None else numbers
    text = re.sub(r"<!--.*?-->\n?", "", text, flags=re.DOTALL)

    def include(m: re.Match) -> str:
        p = paper_dir / m.group(1)
        if not p.exists():
            raise PaperBuildError(f"{{{{include:{m.group(1)}}}}}: {p} not found")
        body = p.read_text(encoding="utf-8").strip()
        if p.suffix == ".tex":
            body = "\n".join(ln for ln in body.splitlines() if not ln.startswith("%"))
            return "```{=latex}\n" + body + "\n```"
        return body

    def number(m: re.Match) -> str:
        if m.group(1) not in nums:
            raise PaperBuildError(f"{{{{sim:{m.group(1)}}}}}: no such number in {NUMBERS.name}")
        return nums[m.group(1)]

    text = re.sub(r"\{\{include:([^}]+)\}\}", include, text)
    text = re.sub(r"\{\{sim:(\w+)\}\}", number, text)
    left = sorted(set(re.findall(r"\{\{[^}]*\}\}", text)))
    if left:
        raise PaperBuildError(f"unresolved placeholders: {left}")
    return text


def _postprocess_tex(tex: str) -> str:
    # design principles: pandoc writes the "(1)" list style; the paper labels them (P1)-(P5)
    tex, n = re.subn(r"\\begin\{enumerate\}\n\\def\\labelenumi\{\(\\arabic\{enumi\}\)\}",
                     r"\\begin{enumerate}[label=(P\\arabic*)]", tex)
    if n != 1:
        raise PaperBuildError(f"expected one (P1)-(P5) list, found {n}")
    for ch, rep in TEX_ASCII.items():
        tex = tex.replace(ch, rep)
    bad = sorted({c for c in tex if ord(c) > 127})
    if bad:
        raise PaperBuildError(f"non-ASCII characters left in paper.tex: {bad}; add them to TEX_ASCII")
    return tex


def _check_log(log: str) -> None:
    problems = re.findall(r"^(?:LaTeX|Package \w+) Warning: (?:Reference|Citation|Hyper reference) .*$", log, re.M)
    problems += re.findall(r"^.*There were undefined references.*$", log, re.M)
    if problems:
        raise PaperBuildError("unresolved references in the PDF:\n" + "\n".join(sorted(set(problems))))


def build_tex(paper_dir: Path = PAPER_DIR) -> Path:
    """paper.md -> paper_build.md -> paper.tex."""
    if shutil.which("pandoc") is None:
        raise PaperBuildError("pandoc not found; install pandoc to build the paper")
    build_md = paper_dir / "paper_build.md"
    build_md.write_text(fill((paper_dir / "paper.md").read_text(encoding="utf-8"), paper_dir), encoding="utf-8")
    subprocess.run(
        ["pandoc", build_md.name, "--from=markdown", "--to=latex", "--template=template.tex", "--natbib",
         "--wrap=preserve", "--output=paper.tex"],
        check=True, cwd=str(paper_dir),
    )
    tex = paper_dir / "paper.tex"
    tex.write_text(_postprocess_tex(tex.read_text(encoding="utf-8")), encoding="utf-8")
    return tex


def build_paper(paper_dir: Path = PAPER_DIR) -> Path:
    """Build paper/paper.tex and paper/paper.pdf (and paper/paper.bbl, kept for the arXiv bundle)."""
    build_tex(paper_dir)
    if shutil.which("tectonic") is None:
        raise PaperBuildError("tectonic not found; install tectonic to compile the paper")
    run = subprocess.run(
        ["tectonic", "-X", "compile", "--keep-intermediates", "--keep-logs", "paper.tex"],
        cwd=str(paper_dir), capture_output=True, text=True,
    )
    if run.returncode != 0:
        raise PaperBuildError(f"tectonic failed:\n{run.stdout[-3000:]}\n{run.stderr[-3000:]}")
    _check_log((paper_dir / "paper.log").read_text(encoding="utf-8", errors="replace"))
    for ext in (".aux", ".out", ".blg", ".xdv"):  # keep paper.bbl and paper.log
        (paper_dir / f"paper{ext}").unlink(missing_ok=True)
    pdf = paper_dir / "paper.pdf"
    print(f"wrote {pdf}")
    return pdf
