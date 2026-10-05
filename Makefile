# The Judgment Benchmark - common tasks. Run `make help` for the list.
.DEFAULT_GOAL := help
PY ?= python3
export PYTHONPATH := src

.PHONY: help install test scenarios calibration charts clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	 awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install the package + dev extras (editable)
	$(PY) -m pip install -e ".[test,analysis]"

test: ## Run the test suite (determinism, fairness invariants, calibration)
	$(PY) -m pytest -q

scenarios: ## Generate + inspect all 84 two-arm scenarios (deterministic)
	$(PY) -m judgment_bench.scenarios

calibration: ## Prove balanced accuracy separates discerning (1.0) from one-note (0.50)
	$(PY) -m judgment_bench.calibration

charts: ## Generate result charts from results/results.json
	$(PY) -m analysis.make_charts $(ARGS)

clean: ## Remove caches and generated charts
	rm -rf .pytest_cache **/__pycache__ docs/charts/*.png
