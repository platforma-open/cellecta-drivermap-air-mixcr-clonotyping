---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow': patch
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering': patch
---

MILAB-6335: second-round code-review fixes.

- The results table no longer shows a green "Done" on a failed or still-running clonotype
  pipeline. `isErrored`/`isRunning` read only `ctx.outputs`, but the clone-export/VBC result
  lived solely in the workflow's `exports` tree, which those accessors cannot reach — so a
  post-MiXCR failure went undetected and `isRunning` cleared as soon as MiXCR analyze
  finished. The workflow now surfaces the clonotype p-frame in `outputs` as well (it stays in
  `exports` for downstream blocks), so the model observes its readiness and error state.
- filter.py (`find_kde_mimima_threshold`): on every KDE fall-back path the threshold falls
  back to `default_low_thresh` (not a detected minimum), so the emitted threshold-KDE value
  is now `nan` instead of `np.exp(log_dens[default_low_thresh])` — which indexed the 1000-point
  density array by a read-count constant rather than a grid index. NaN matches the no-maxima
  path and makes `is_normalization_unreliable` correctly treat such a bin as unreliable. The
  six duplicated 6-tuple returns are collapsed via a `_kde_point` helper (behaviour-preserving;
  golden + property tests green).
- IO_CONTRACT.md: corrected to state that `agg-clones` ranks (`max_by`) on the never-NA
  `readCount`, not `templateEstimate` (which is `NA` on degenerate samples and would crash
  `idxmax`).
