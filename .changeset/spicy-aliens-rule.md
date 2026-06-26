---
"@platforma-open/cellecta.drivermap-mixcr-clonotyping": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.model": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.ui": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-normalization": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.hash-column": major
---

MILAB-6335: bring the Cellecta DriverMap AIR + MiXCR clonotyping block up to date — fix the Full-Length Profiling crash, port the VBC Python scripts to upstream, migrate to BlockModelV3 with a full SDK upgrade, and land the correctness, status, and test improvements found along the way.

**Crash & correctness fixes**

- **Full-Length Profiling export no longer crashes.** The full-length preset assembles on `{CDR1Begin:FR4End}`, so MiXCR never exports `nSeqVDJRegion` — yet the preset's `keyColumns`/`assemblingFeature` referenced it and panicked `keyAxesSpec`. The clone key now derives from the regions spanning the assembling feature plus the V/J/C gene calls, and `assemblingFeature` is `CDR3`. `keyColumns` is computed from each preset's `keyFeatures` + `keyGeneColumns`, so the exported features and the clone key cannot drift apart.
- **Unreliable VBC normalization no longer fails the run.** When a sample's VBC normalization is all-unreliable, `normalize.py` emits `"NA"` molecule counts. The `abundancePf` import now marks the molecule columns `allowNA: true` (imported as null; `readCount`/`readFraction` stay non-null), `agg-clones` ranks representative clones by the never-NA `readCount` (not `templateEstimate`, which crashed `idxmax` on all-NA groups), and a new `aggregate-abundance` step sums abundance per `clonotypeKey` per sample so the import key stays unique.
- **`readFraction` stays a within-sample fraction that sums to 1.** Every `filter.py` path — including the QC-fail (`< 1000` clonotypes) path — now collapses to one row per clone before abundance aggregation, instead of passing per-molecule rows through.

**VBC Python port**

- Ported `filter.py` and `normalize.py` up to `kitt-cellecta/AIR_VBC_filtering@main`: QC gate, barcode-hopping filter, and KDE thresholding (Silverman bandwidth, >2-maxima split, valley-depth gate, VBC 1→2→3 reliability fallback). The threshold function is now total — it returns a 6-tuple on every path and never `None`, fixing the `cannot unpack non-iterable NoneType` crash on degenerate bins.
- Kept the block's adaptation layer: explicit-file CLI, the kit's `tagValueMIVBC` tag, the `templateEstimateFraction` output, empty-input/QC-fail handling, and the downstream column schema (no `readCount_BC` pivot).
- Pinned the port with an I/O contract, a golden-comparison harness against upstream, and a committed synthetic test bed.

**BlockModelV3 + SDK/tooling modernization**

- Migrated the model to `BlockModelV3`: a unified `BlockData` (`DataModelBuilder`) with an `.upgradeLegacy` step so persisted V1 projects upgrade transparently; UI bindings move to `app.model.data.*` and the entry to `defineAppV3`.
- Moved onto the block-tools structurer (managed tsconfig/turbo/CI, oxlint/oxfmt, block index) with a full SDK upgrade (`@platforma-sdk/model` & `ui-vue` 1.79, `workflow-tengo` 6, `tengo-builder` 3 → 4, `block-tools`), including the author-code changes the bump required (ag-grid 34, the `ReactiveFileContent` instance API, `PlNumberField`).
- Put the three Python packages on a shared `uv` + `ruff` platform — one `pyproject.toml`/`uv.lock`/ruff config, with each package's `requirements.txt` compiled from a PEP 735 dependency group.
- Renamed the `hash-column` software to the block's own `cellecta` namespace.

**Status & error surfacing**

- **Progress is truthful.** The results table shows MiXCR progress while it runs, "Processing clonotypes" through the post-MiXCR phase, and "Done" only once the whole block finishes — never a premature "Done" the moment MiXCR ends.
- **Failure is surfaced.** A failed post-MiXCR step (clone export or the VBC Python step) now shows per-sample "Error" instead of a false-green "Done". The model derives a `clonotypingStatus` (`OutputWithStatus`) from the top-level output fields plus a new `vbcStatus` workflow output — a nested ResourceMap that exposes the per-sample VBC errors the `clones` exportFrame hides.
- The Settings panel auto-opens on a fresh block add.

**Tests & cleanup**

- Added a Python Tests CI workflow — ruff check/format gate, fast Hypothesis property tests on every push, slow golden comparisons on the merge queue and main, and a `requirements.txt`-sync check — plus a synthetic VBC test bed; coverage rose ~22% → ~81%.
- Removed dead workflow/model code, simplified the UI, and fixed a missing `polars_hash` import in `hash-column`.
