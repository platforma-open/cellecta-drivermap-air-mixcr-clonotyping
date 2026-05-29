---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.hash-column': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-normalization': patch
---

MILAB-6335: each package's `src/requirements.txt` is now generated from a dependency group in `software/pyproject.toml` (the single source of truth) via `pnpm deps:export`; a CI job fails if a committed file drifts from pyproject. Dependencies are unchanged (same pins).
