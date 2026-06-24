---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-normalization': patch
---

MILAB-6335: keep readFraction a normalized within-sample fraction (sums to 1).

`aggregate-abundance` sums `readFraction` per `clonotypeKey`, so the per-clone value must be
a clean within-sample fraction before it gets there. Two paths broke that:

- **filter.py** — the QC-fail path (`< 1000` clonotypes) passed the raw per-`(clone, molecule)`
  mixcr export through unchanged (still carrying `tagValueMIVBC` and many rows per clone), so
  the downstream sum added up per-molecule fractions and inflated `readFraction`. QC-fail now
  collapses to one row per clone (drops `tagValueMIVBC`, recomputes `readFraction`) like every
  other path, via a shared `collapse_to_one_row_per_clone` helper. The input TSV is also read
  once instead of three times.
- **normalize.py** — the zero-estimate-clone drop changed the surviving set but left
  `readFraction` (computed by filter.py over its own survivors) stale, so the summed per-sample
  `readFraction` no longer totalled 1. It is now recomputed over the surviving clones.

No change to the upstream-matched filtering / estimation math (golden tests still pass).
