# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Zenodo DOI [10.5281/zenodo.24102402](https://doi.org/10.5281/zenodo.24102402) in the README, `CITATION.cff`,
  the web reader and the Hugging Face dataset card.

## [2.0.0] - 2026-11-10

### Added
- Implementation and simulation-based validation (paper, Section 9): exact along-network distances on the
  real Bang Pakong river network (HydroRIVERS v1.0) and Monte Carlo scenarios with synthetic sites and stations
  (`from_space_to_sediment.sim_validate`, results in `results/sim_out/`).
- Earth Engine screening script for Module 1 (`gee/fs2s_module1_screening.js`), checked statically and against
  a mock of the Earth Engine API.
- Verification and downstream attribution for Modules 1 and 3 (`from_space_to_sediment.verify_trace`) and a
  synthetic end-to-end test data set (`from_space_to_sediment.synthetic`).
- Python package `src/from_space_to_sediment/` with the `fs2s` command
  (`synthetic`, `selftest`, `verify`, `network`, `sim`, `figures`, `paper`, `web`) and a `Makefile` around it.
- Paper source in Markdown: `paper/paper.md` is built by pandoc with `paper/template.tex` into `paper/paper.tex`
  and by tectonic into `paper/paper.pdf`. Simulation numbers are placeholders filled from
  `results/sim_out/paper_numbers.json`; `make arxiv` writes a self-contained source bundle.
- Web reader for the paper at <https://thanatchon36.github.io/from-space-to-sediment/paper/>, built from the same
  source into `docs/paper/`.
- Dataset on Hugging Face, [`thanatchon36/from-space-to-sediment`](https://huggingface.co/datasets/thanatchon36/from-space-to-sediment):
  simulation replicates, network checks, the synthetic test set and the input templates (`make hf`).
- `docs/data_sources.md`: where every input for a real run comes from.
- Test suite (`tests/`) run by CI: the synthetic end-to-end run, river orientation, along-network distances,
  `<DL` parsing, the CLI, and a check that public outputs hold no site coordinates.
- CSV templates for every input table (`templates/`), MIT `LICENSE`, `CITATION.cff`, `.zenodo.json` and a README
  banner of the Bang Pakong river network (`scripts/make_banner.py`).

### Changed
- Evidence rule: the simulations showed the count-based rule was too permissive, so a probable attribution now
  requires geochemical evidence (C1 + C2 + C3) and an attributed one all four criteria. `--evidence-rule count`
  restores the old rule.
