---
'@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow': patch
---

MILAB-6335: tolerate unreliable VBC normalization instead of crashing the run.

When VBC=1/2/3 normalization is all unreliable for a sample, `vbc-normalization` emits the
literal `"NA"` for `templateEstimate` / `templateEstimateFraction` for every clone in that
sample. Three workflow consumers rejected it and failed the whole multi-sample run:

- The `abundancePf` xsv import declared both molecule columns `allowNA: false`, so the
  `pfconv` "Binary" importer hard-errored (`N/A value: NA not allowed`) on a single degenerate
  sample. They are now `allowNA: true` (imported as null). `readCount` / `readFraction` stay
  `allowNA: false` — MiXCR always emits valid values for them.
- `agg-clones` ranked representative clones by `templateEstimate` via `ptransform` `max_by`
  (pandas `idxmax`), which raises `KeyError` on an all-`NaN` ranking group (a clonotype seen
  only in degenerate samples). Ranking now uses `readCount`, which is always present and orders
  identically to `templateEstimate` within a sample.
- The `abundancePf` import is keyed by `clonotypeKey` and requires it unique, but `mixcr
  exportClones` can emit several clones sharing one `clonotypeKey`; the good path's
  zero-estimate drop masked this, the degenerate path keeps them, so the import failed with
  `Multiple rows with the same axis key`. A new `aggregate-abundance` workflow template (`pt`)
  sums the abundance columns per `clonotypeKey` per sample before the import; an all-NA
  molecule count stays null (count-mask) rather than collapsing to 0. The per-clone table
  feeding `agg-clones` is untouched, and no python software package changes.

Adds a Tengo unit test locking the `allowNA` / ranking-column contract. Note: the degradation
is still silent downstream (null molecule counts read as 0, e.g. repertoire-diversity
`fill_null(0)`) — see the Layer C TODO in `get-export-params.lib.tengo` for the deferred
per-sample QC-visibility follow-up.
