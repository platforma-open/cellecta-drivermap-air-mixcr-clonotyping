---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.hash-column': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-normalization': patch
---

MILAB-6335: fix Full-Length Profiling and add Python tooling.

- Fix the Full-Length crash (`column nSeqVDJRegion does not exist in export`): the kit assembles `CDR1_TO_FR4`, not `VDJRegion`. The export now keys on `nSeqCDR1_TO_FR4`, drops uncovered `FR1`, and starts V-segment mutations at `CDR1Begin`.
- Annotate the clns column with the preset's real assembling feature instead of a hardcoded `CDR3`.
- Rename the hash-column package to the block's own namespace (`@platforma-open/cellecta.drivermap-mixcr-clonotyping.hash-column`).
- Add a shared Python test/lint harness (ruff + pytest) with CI, and generate each `src/requirements.txt` from `pyproject.toml` (single source of truth, CI drift-checked). Dependencies unchanged.
