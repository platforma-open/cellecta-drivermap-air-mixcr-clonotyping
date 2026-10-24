---
"@platforma-open/cellecta.drivermap-mixcr-clonotyping": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.model": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.ui": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.workflow": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-filtering": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.vbc-normalization": major
"@platforma-open/cellecta.drivermap-mixcr-clonotyping.hash-column": major
---

MILAB-6335: bring the Cellecta DriverMap AIR + MiXCR clonotyping block up to date — fix the Full-Length Profiling crash, port the VBC Python scripts to upstream, migrate to BlockModelV3 on the current SDK, split MiXCR into one job per step, and add the QC report table.

**Crash & correctness fixes**

- **Full-Length Profiling export no longer crashes.** The full-length preset assembles on `{CDR1Begin:FR4End}`, so MiXCR never exports `nSeqVDJRegion`. The clone key now derives from the regions spanning the assembling feature plus the V/J/C gene calls; `keyColumns` is computed from each preset's `keyFeatures`, so the exported features and the clone key cannot drift apart.
- **TCR gamma and delta are no longer swapped.** `TCRGamma` exports `TRG` and `TCRDelta` exports `TRD`.
- **Unreliable VBC normalization no longer fails the run.** NA molecule counts import as null, `agg-clones` ranks representative clones by the never-NA `readCount`, and an `aggregate-abundance` step sums abundance per `clonotypeKey` per sample so the import key stays unique.
- **`readFraction` stays a within-sample fraction that sums to 1** on every `filter.py` path, including the QC-fail path.
- **The clns column carries the real assembling feature**, covered features and UMI tags, read from the resolved preset.

**VBC Python port**

- Ported `filter.py` and `normalize.py` to `kitt-cellecta/AIR_VBC_filtering@main` (tagged `v1.0.0`): QC gate, barcode-hopping filter and KDE thresholding. The threshold function is total and never returns `None`.
- Kept the block's adaptation layer: explicit-file CLI, the kit's `tagValueMIVBC` tag, the `templateEstimateFraction` output and the downstream column schema.
- Pinned the port with an I/O contract, a golden-comparison harness against upstream, and a synthetic test bed.

**MiXCR split and resource sizing**

- MiXCR 4.7.0-413-develop. `mixcr analyze --dry-run-json` plans the run and each step (align, refineTagsAndSort, assemble, qc) runs as its own job, with CPU and memory from a per-step table and a scratch request sized from the reads.
- `exportClones` runs on the `memory-from-limits` entrypoint with RAM sized from the `.clns`, floored at 24 GiB (it ran an 8 GiB heap inside a 1 GiB grant before). The hash-column, VBC and aggregation jobs request memory sized from their input.
- Advanced Settings gain a memory and CPU override for every sample process and a per-step memory floor; the step list is planned on request in the prerun.
- The log tab shows one log per MiXCR step.

**QC report table**

- A new QC Report Table page lists one row per sample from `mixcr exportReportsTable`: alignment, tag refinement and assembly metrics.

**BlockModelV3 + SDK/tooling**

- `BlockModelV3` with a unified `BlockData`; persisted V1 projects upgrade transparently, and existing V3 data migrates to v2 (table state).
- The block declares a kind with its init-params contract, and the model supports project templates.
- Current SDK (`@platforma-sdk/model`/`ui-vue` 1.85, `workflow-tengo` 6.17, `block-tools` 2.16) on the block-tools structurer, with the slim block facade; the software builds with `block-tools software build`.
- The block owns its MiXCR report and QC types instead of depending on the private mixcr-clonotyping model.
- The three Python packages share one `uv` + `ruff` platform; the `hash-column` software moved to the block's own `cellecta` namespace.

**Status & error surfacing**

- The results table shows the furthest MiXCR step's progress while MiXCR runs, "Processing clonotypes" through the post-MiXCR phase, and "Done" only when the whole block finishes.
- A failed post-MiXCR step shows "Error" instead of a false "Done".
- The settings warn when the selected preset is one the block cannot run.

**Tests**

- Block tests: an idle smoke test and an end-to-end run of the RNA profiling preset on synthetic Cellecta-shaped reads.
- Python Tests CI: ruff gate, fast property tests, and slow golden comparisons.

Existing projects re-run every sample on update.
