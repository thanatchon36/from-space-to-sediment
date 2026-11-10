PY ?= .venv/bin/python
REPS ?= 150

.PHONY: setup data selftest network sim figures banner paper web arxiv test all clean

setup:          ## create venv and install dependencies (needs uv)
	uv venv .venv --python 3.12
	uv pip install --python .venv/bin/python -r pyproject.toml --extra dev

data:           ## third-party map data into data/ (Natural Earth, districts, HydroRIVERS extract)
	$(PY) scripts/download_data.py

selftest:       ## synthetic end-to-end run, no downloads -> tests/synthetic/out
	$(PY) pipeline/make_synthetic_test.py tests/synthetic
	$(PY) pipeline/fs2s_verify_trace.py \
	  --candidates tests/synthetic/candidates.csv --factories tests/synthetic/diw_factories.csv \
	  --known tests/synthetic/known_sites.csv --negatives tests/synthetic/hard_negatives.csv \
	  --labels tests/synthetic/labels.csv --rivers tests/synthetic/rivers.geojson \
	  --stations tests/synthetic/stations.csv --matrix sediment --cores tests/synthetic/cores.csv \
	  --outdir tests/synthetic/out --n-perm 199

network:        ## network checks on the real Bang Pakong network -> results/sim_out (needs make data)
	$(PY) pipeline/sim_validate.py --scenario -1

sim:            ## Monte Carlo scenarios 0-3, $(REPS) replicates each (about 0.6 s per replicate)
	for s in 0 1 2 3; do $(PY) pipeline/sim_validate.py --scenario $$s --reps $(REPS) || exit 1; done

figures:        ## redraw every paper figure, sim_numbers.tex and tab_validation.tex (needs make data)
	for f in paper/figures_src/fig*.py; do $(PY) "$$f" || exit 1; done

banner:         ## README banner -> docs/assets/banner.png (needs make data)
	$(PY) scripts/make_banner.py

paper:          ## compile paper/paper.pdf (tectonic), then the web reader
	cd paper && tectonic paper.tex
	$(MAKE) web

web:            ## web reader only -> docs/paper/ (pandoc)
	$(PY) scripts/build_web.py

arxiv:          ## arXiv source bundle -> paper/arxiv.tar.gz
	cd paper && tar -czf arxiv.tar.gz paper.tex arxiv.sty paper.bbl references.bib \
	  sim_numbers.tex tab_validation.tex figures/*.pdf
	@echo "wrote paper/arxiv.tar.gz"

test:           ## pytest: synthetic end-to-end run and unit checks
	$(PY) -m pytest -q

all: data network figures paper

clean:
	rm -rf tests/synthetic paper/arxiv.tar.gz paper/*.aux paper/*.log paper/*.out paper/*.blg
