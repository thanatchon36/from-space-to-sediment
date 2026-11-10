# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Web reader for the paper at <https://thanatchon36.github.io/from-space-to-sediment/paper/>, built from
  `paper/paper.tex` by `make web` into `docs/paper/`.
- `Makefile` with targets for setup, the self-test, the network checks and simulations, figures, the paper,
  the web reader and the arXiv bundle.
- Test suite (`tests/`): the synthetic end-to-end run, river-orientation and along-network distance checks,
  `<DL` parsing, and a check that public outputs hold no site coordinates. CI runs it on every push.
- `pyproject.toml` (replaces `requirements.txt`), MIT `LICENSE`, `.zenodo.json` and a README banner of the
  Bang Pakong river network (`docs/assets/banner.png`, drawn by `scripts/make_banner.py`).

## [2.0.0] - 2026-11-10

### Added
- Implementation and simulation-based validation (paper, Section 9): exact along-network distances on the
  real Bang Pakong river network (HydroRIVERS v1.0) and Monte Carlo scenarios with synthetic sites and stations
  (`pipeline/sim_validate.py`, results in `results/sim_out/`).
- Earth Engine screening script for Module 1 (`pipeline/gee/fs2s_module1_screening.js`), checked statically
  and against a mock of the Earth Engine API.
- Verification and downstream attribution for Modules 1 and 3 (`pipeline/fs2s_verify_trace.py`) and a
  synthetic end-to-end test data set (`pipeline/make_synthetic_test.py`).
- CSV templates for every input table (`templates/`) and a download script for third-party map data.

### Changed
- Evidence rule: the simulations showed the count-based rule was too permissive, so a probable attribution now
  requires geochemical evidence (C1 + C2 + C3) and an attributed one all four criteria. `--evidence-rule count`
  restores the old rule.

