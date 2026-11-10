#!/usr/bin/env python3
"""Stage and publish the Hugging Face dataset thanatchon36/from-space-to-sediment.

    python scripts/publish_hf.py --stage-only     # build the folder, print where it is
    python scripts/publish_hf.py                  # build and upload (needs `hf auth login`)

Contents: the simulation and network-check results in results/sim_out/, the synthetic end-to-end
test data set (fs2s synthetic), the input templates, a dataset card, licence terms and SHA256SUMS.
No real candidate sites exist, so none are published. The DOI is read from CITATION.cff when present.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import tempfile
from pathlib import Path

from from_space_to_sediment.config import PAPER_URL, REPO_URL, RESULTS_DIR, ROOT
from from_space_to_sediment.synthetic import generate

REPO_ID = "thanatchon36/from-space-to-sediment"
TITLE = ("From Space to Sediment: An Integrated Multi-Sensor Remote Sensing and Geochemical Fingerprinting "
         "Framework for Detecting E-Waste Hotspots and Attributing River Contamination in Thailand")


def doi() -> str | None:
    m = re.search(r"^doi:\s*(\S+)", (ROOT / "CITATION.cff").read_text(encoding="utf-8"), re.M)
    return m.group(1).strip("\"'") if m else None


def card(d: str | None) -> str:
    archive = f"; archived on Zenodo: [{d}](https://doi.org/{d})" if d else ""
    doi_bib = f"  doi    = {{{d}}},\n" if d else ""
    return f"""---
license: cc-by-4.0
pretty_name: "From Space to Sediment: e-waste site screening and river attribution, validation data"
language:
  - en
  - th
size_categories:
  - n<1K
tags:
  - electronic-waste
  - remote-sensing
  - source-apportionment
  - river-networks
  - geospatial
  - thailand
  - simulation
  - synthetic
configs:
  - config_name: simulations
    data_files: results/sim_results_s*.csv
    default: true
  - config_name: network_pairs
    data_files: results/network_pairs.csv
  - config_name: reach_dist_outlet
    data_files: results/reach_dist_outlet.csv
---

# From Space to Sediment: validation data

> **No real e-waste sites are in this dataset.** The simulations place synthetic sites, factories, records and
> sampling stations on the real Bang Pakong river network, and `synthetic/` is a small made-up test set. The
> real-world inputs are the river network itself (HydroRIVERS v1.0) and nothing else.

Data for the preprint *{TITLE}* by Thanatchon Chongmankhong ([read online]({PAPER_URL}) ·
[PDF]({REPO_URL}/blob/main/paper/paper.pdf)). The framework screens candidate e-waste processing and dumping
sites from multi-sensor satellite data, verifies them against the factory registry and public records, and
attributes river contamination to upstream sources; a site is reported as an attributed source only when
detection, hydrological connectivity, geochemistry and chronology agree. Code: <{REPO_URL}>{archive}.

*Independent personal research. Does not represent the views of any employer or institution.*

## Files

| path | content |
|---|---|
| `results/sim_results_s0.csv` … `s3.csv` | **simulation.** Monte Carlo validation (paper, Section 9 and Table 5): 150 replicates per scenario. Scenarios 0–2 have a true decay length `lam_true` of 3, 8 and 20 km with source fraction `pi` = 0.25; scenario 3 is the null (`pi` = 0). One row per replicate: selected λ, the association statistic and permutation p-value, flag accuracy, and counts of sites reaching each evidence level with their true positives |
| `results/network_checks.json` | network checks on the real Bang Pakong network: 240 reaches, orientation agreement, geometric vs attribute length, along-network distance error against an independent reference |
| `results/network_pairs.csv` | 500 random point pairs: along-network distance from the pipeline and from the reference, km |
| `results/reach_dist_outlet.csv` | distance from each HydroRIVERS reach (`HYRIV_ID`) to the Bang Pakong outlet, km |
| `results/paper_numbers.json` | the numbers quoted in the paper, computed from the simulation files (when present) |
| `synthetic/` | **synthetic.** The end-to-end test set: candidates, factories, known sites, hard negatives, labels, stations, one dated core and a five-reach river network. Coordinates are on a made-up local grid around 13.9° N, 101.4° E and do not mark real sites. `fs2s selftest` runs the pipeline on it |
| `templates/` | header rows for every input table the pipeline reads |
| `SHA256SUMS` | checksums of every file above |

Evidence levels: **attributed** = C1–C4, **probable** = C1 + C2 + C3, **possible** = any two criteria, where
C1 = detection, C2 = hydrological connectivity, C3 = geochemistry, C4 = chronology. Column prefixes in the
simulation files: `possible_`, `probable_` (count rule), `probable_c3req_` (strict rule, the default),
`attributed_`; suffix `_n` = sites at that level, `_tp` = true sources among them, `_tp_attr` = attributable
true sources (connected, with a station within 3λ downstream).

## Licence

CC BY 4.0. `results/network_checks.json`, `results/network_pairs.csv` and `results/reach_dist_outlet.csv` are
derived from HydroRIVERS v1.0 (Lehner, B. & Grill, G., 2013, *Hydrological Processes* 27(15): 2171–2186;
https://www.hydrosheds.org), whose licence terms also apply.

## Citation

```bibtex
@misc{{chongmankhong2026fromspace,
  author = {{Chongmankhong, Thanatchon}},
  title  = {{{TITLE}}},
  year   = {{2026}},
{doi_bib}  url    = {{{PAPER_URL}}},
  note   = {{Preprint; framework, implementation and simulation-based validation}}
}}
```
"""


LICENSE = """from-space-to-sediment dataset — licence terms
Copyright (c) 2026 Thanatchon Chongmankhong

Creative Commons Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/

You may share and adapt this material for any purpose, provided you give appropriate credit
(cite the preprint and this dataset), link to the licence and indicate if changes were made.

results/network_checks.json, results/network_pairs.csv and results/reach_dist_outlet.csv are
derived from HydroRIVERS v1.0 (Lehner & Grill, 2013; https://www.hydrosheds.org). The
HydroSHEDS licence terms apply to them in addition, including its attribution requirement.
"""


def stage(out: Path) -> Path:
    if out.exists():
        shutil.rmtree(out)
    (out / "results").mkdir(parents=True)
    for f in sorted(RESULTS_DIR.iterdir()):
        if f.suffix in (".csv", ".json"):
            shutil.copyfile(f, out / "results" / f.name)
    generate(out / "synthetic")
    shutil.copytree(ROOT / "templates", out / "templates")
    (out / "README.md").write_text(card(doi()), encoding="utf-8")
    (out / "LICENSE").write_text(LICENSE, encoding="utf-8")
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name not in ("README.md", "LICENSE"))
    sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}" for p in files]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage-only", action="store_true")
    ap.add_argument("--dir", default=None, help="staging folder (default: a temporary folder)")
    a = ap.parse_args()
    out = stage(Path(a.dir) if a.dir else Path(tempfile.mkdtemp()) / "hf")
    print(f"staged {sum(1 for p in out.rglob('*') if p.is_file())} files in {out}")
    if a.stage_only:
        return
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(REPO_ID, repo_type="dataset", exist_ok=True)
    api.upload_folder(folder_path=str(out), repo_id=REPO_ID, repo_type="dataset",
                      commit_message="Update dataset from the from-space-to-sediment repository",
                      delete_patterns=["results/*", "synthetic/*", "templates/*", "SHA256SUMS"])
    print(f"https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
