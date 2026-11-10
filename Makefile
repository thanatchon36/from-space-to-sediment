PY ?= .venv/bin/python
REPS ?= 150

.PHONY: setup data synthetic selftest network sim figures banner paper web arxiv hf test all clean

setup:          ## create venv and install the package (needs uv)
	uv venv .venv --python 3.12
	uv pip install --python .venv/bin/python -e ".[dev,hub]"

data:           ## third-party map data into data/ (Natural Earth, districts, HydroRIVERS extract)
	$(PY) scripts/download_data.py

synthetic:      ## synthetic end-to-end test data -> tests/synthetic. NEVER a substitute for real data
	$(PY) -m from_space_to_sediment.cli synthetic

selftest:       ## synthetic data + verification and attribution -> tests/synthetic/out (no downloads)
	$(PY) -m from_space_to_sediment.cli selftest

network:        ## network checks on the real Bang Pakong network -> results/sim_out (needs make data)
	$(PY) -m from_space_to_sediment.cli network

sim:            ## Monte Carlo scenarios 0-3, $(REPS) replicates each (about 0.6 s per replicate; resumes)
	$(PY) -m from_space_to_sediment.cli sim --reps $(REPS)

figures:        ## redraw every paper figure and the generated numbers (needs make data)
	$(PY) -m from_space_to_sediment.cli figures

banner:         ## README banner -> docs/assets/banner.png (needs make data)
	$(PY) scripts/make_banner.py

paper:          ## paper/paper.md -> paper.tex -> paper.pdf (pandoc + tectonic) and the web reader docs/paper/
	$(PY) -m from_space_to_sediment.cli paper

web:            ## web reader only -> docs/paper/index.html (pandoc)
	$(PY) -m from_space_to_sediment.cli web

arxiv: paper    ## arXiv source bundle -> paper/arxiv.tar.gz
	$(PY) scripts/arxiv_bundle.py

hf:             ## publish the Hugging Face dataset (needs `hf auth login`)
	$(PY) scripts/publish_hf.py

test:
	$(PY) -m pytest -q

all: data network figures paper

clean:
	rm -rf tests/synthetic paper/paper_build.md paper/paper.tex paper/paper.log paper/arxiv paper/arxiv.tar.gz
