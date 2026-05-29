---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.hash-column': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-normalization': patch
---

MILAB-6335: add a Python test/lint harness and format the software scripts (no runtime behavior change).

- Add a shared `software/pyproject.toml` (ruff + pytest) and a `python-tests.yaml` CI job that runs ruff format-check, ruff lint, and pytest.
- Add behavioral tests for the hash-column script.
- Apply ruff formatting to all Python software (`filter.py`, `normalize.py`, `hash-column/main.py`); `hash-column/main.py` marks `import polars_hash` as a required side-effect import (`# noqa: F401`).
