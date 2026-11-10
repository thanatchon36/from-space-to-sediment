"""Build the arXiv source bundle, ``paper/arxiv.tar.gz``, from the paper as last built.

arXiv compiles the paper itself, from the root of the bundle, with pdfLaTeX (declared in
``00README.json``). This stages ``paper.tex`` (generated from paper/paper.md, every number and table
already filled in), ``arxiv.sty``, ``paper.bbl`` (arXiv does not run BibTeX) and the PDF figures it
uses, compiles the staged copy once with tectonic to prove it is self-contained, then tars it. It also
prints the title, the plain-text abstract (for the arXiv form) and a comments line.
Run ``make paper`` first.

Usage: ``python scripts/arxiv_bundle.py``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
STAGE = PAPER / "arxiv"
OUT = PAPER / "arxiv.tar.gz"
REPO_URL = "https://github.com/thanatchon36/from-space-to-sediment"


def main() -> int:
    for name in ("paper.tex", "paper.bbl", "paper_build.md"):
        if not (PAPER / name).exists():
            raise SystemExit(f"paper/{name} not found; run `make paper` first")
    tex = (PAPER / "paper.tex").read_text(encoding="utf-8")
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / "figures").mkdir(parents=True)
    (STAGE / "paper.tex").write_text(tex, encoding="utf-8")
    for name in ("arxiv.sty", "paper.bbl"):
        shutil.copyfile(PAPER / name, STAGE / name)
    # the optional argument of \includegraphics carries the alt text, which may itself hold brackets
    figures = sorted(set(re.findall(r"\{figures/([\w.-]+)\}", tex)))
    for name in figures:
        shutil.copyfile(PAPER / "figures" / name, STAGE / "figures" / name)
    (STAGE / "00README.json").write_text(
        json.dumps(
            {
                "spec_version": 1,
                "process": {"compiler": "pdflatex"},
                "sources": [{"filename": "paper.tex", "usage": "toplevel"}],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # The staged copy must compile on its own, from paper.bbl: there is no references.bib in the bundle
    # and arXiv does not run BibTeX. tectonic always runs BibTeX when the .aux names a database, so the check
    # compiles a copy that reads paper.bbl directly, which is what pdfLaTeX does with the real paper.tex.
    check = re.sub(r"\\bibliography\{references\}", lambda m: "\\input{paper.bbl}", tex)
    if check == tex:
        raise SystemExit("paper.tex has no \\bibliography{references}")
    (STAGE / "paper_check.tex").write_text(check, encoding="utf-8")
    run = subprocess.run(
        ["tectonic", "-X", "compile", "--keep-logs", "paper_check.tex"], cwd=STAGE, capture_output=True, text=True
    )
    if run.returncode != 0:
        raise SystemExit(f"staged compile failed:\n{run.stdout[-2000:]}\n{run.stderr[-2000:]}")
    log = (STAGE / "paper_check.log").read_text(encoding="utf-8", errors="replace")
    if re.search(r"Citation .* undefined|There were undefined references", log):
        raise SystemExit("staged compile has undefined citations or references; see paper/arxiv/paper_check.log")
    pages = re.search(r"Output written on paper_check\.(?:xdv|pdf) \((\d+) pages", log)
    if pages is None:
        raise SystemExit("staged compile left no page count")
    for p in STAGE.iterdir():  # keep only the sources
        if p.is_file() and p.name not in {"paper.tex", "paper.bbl", "arxiv.sty", "00README.json"}:
            p.unlink()
    with tarfile.open(OUT, "w:gz") as tar:
        for p in sorted(STAGE.rglob("*")):
            if p.is_file():
                tar.add(p, arcname=str(p.relative_to(STAGE)))
    files = sorted(str(p.relative_to(STAGE)) for p in STAGE.rglob("*") if p.is_file())
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} kB, {len(files)} files)")
    print("\n".join(f"  {f}" for f in files))

    # metadata for the submission form, from the filled markdown (numbers already resolved)
    md = (PAPER / "paper_build.md").read_text(encoding="utf-8")
    title = re.search(r'^title: "(.*)"$', md, re.M)
    subtitle = re.search(r'^subtitle: "(.*)"$', md, re.M)
    abstract = re.search(r"^abstract: \|\n((?:  .*\n?)+)", md, re.M)
    if title is None or abstract is None:
        raise SystemExit("paper_build.md lacks the title or abstract")
    full_title = title.group(1) + (": " + subtitle.group(1) if subtitle else "")
    body = " ".join(abstract.group(1).split())
    body = re.sub(r"\^(\d+)\^", r"\1", body).replace("*", "").replace("--", "-").replace(" ", " ")
    print(f"\nTitle:\n{full_title}")
    print(f"\nAbstract ({len(body)} characters; arXiv allows 1,920):\n{body}")
    print(
        f"\nComments:\n{pages.group(1)} pages, {len(figures)} figures. Framework, implementation and "
        f"simulation-based validation; no real candidate sites. Code: {REPO_URL}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
