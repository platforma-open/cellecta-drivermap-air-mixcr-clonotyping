---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.model': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.ui': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-normalization': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow': patch
---

MILAB-6335: code-review fixes for the Cellecta block update.

- The results table no longer shows "Done" when the block failed. `isRunning`
  (`getIsReadyOrError() === false`) goes false on both success and failure, so a failed
  clone export or VBC Python step after MiXCR succeeded showed a green "Done". The model now
  exposes an `isErrored` output and the table shows "Error" for those samples.
- VBC `readFraction` stays a normalized within-sample fraction (sums to 1). filter.py's
  QC-fail path (`< 1000` clonotypes) passed the raw per-molecule export through, so
  aggregate-abundance summed per-molecule fractions and inflated the value; it now collapses
  to one row per clone like every other path. normalize.py recomputes `readFraction` over the
  clones surviving its zero-estimate drop. filter.py also reads its input once, not three times.
- The clonotype key columns derive from a single source of truth: `keyColumns` is computed
  from each preset's `keyFeatures` + `keyGeneColumns` rather than a hand-maintained parallel
  list, so the exported features and the clone key cannot drift apart (byte-identical result,
  pinned by a test).
