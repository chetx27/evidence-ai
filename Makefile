.PHONY: test harness slice serve ui ci lint

export PYTHONPATH := src

PY := .venv/bin/python
RUFF := .venv/bin/ruff

lint:
	$(RUFF) check src tests

test: lint
	$(PY) -m pytest

slice:
	$(PY) -m evidenceai.cli slice --out data/slice

harness: slice
	$(PY) -m evidenceai.cli harness --db data/slice/evidence.db --out eval/logs/gate1.json

serve:
	$(PY) -m evidenceai.cli serve --db data/slice/evidence.db --host 127.0.0.1 --port 8000

ui:
	npm --prefix frontend run dev

ci: test
	npm --prefix frontend run build
