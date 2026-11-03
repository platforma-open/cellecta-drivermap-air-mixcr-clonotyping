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

- MiXCR 4.7.0-415-develop (the Docker image of 413 trusts the compromised eMudhra intermediate CAs). `mixcr analyze --dry-run-json` plans the run and each step (align, refineTagsAndSort, assemble, qc) runs as its own job, with CPU and memory from a per-step table and a scratch request sized from the reads.
- `exportClones` runs on the `memory-from-limits` entrypoint with RAM sized from the `.clns`, floored at 24 GiB (it ran an 8 GiB heap inside a 1 GiB grant before). The hash-column, VBC and aggregation jobs request memory sized from their input.
- Advanced Settings gain a minimum memory and a CPU count for every sample process and a per-step memory floor; the step list is planned on request in the prerun. The minimum memory raises the floor of every MiXCR step and clone export, and changing it re-runs no sample.
- Index reads (I1, I2) are no longer staged for MiXCR; a sample that has them no longer fails.
- The log tab shows one log per MiXCR step.

**QC report table**

- A new QC Report Table page lists one row per sample from `mixcr exportReportsTable`: alignment, tag refinement and assembly metrics.

**BlockModelV3 + SDK/tooling**

- `BlockModelV3` with a unified `BlockData`; persisted V1 projects upgrade transparently, title included.
- The block declares a kind with its init-params contract, and the model supports project templates.
- Current SDK (`@platforma-sdk/model`/`ui-vue` 1.86, `workflow-tengo` 6.18, `block-tools` 2.17; Node 24, pnpm 12) on the block-tools structurer, with the slim block facade; the software builds with `block-tools software build`.
- The block owns its MiXCR report and QC types instead of depending on the private mixcr-clonotyping model.
- The three Python packages share one `uv` + `ruff` platform; the `hash-column` software moved to the block's own `cellecta` namespace.

**Export raw results**

- An "Export raw results" button, as in MiXCR Clonotyping, saves a ZIP with each sample's raw `mixcr exportClones` table and its VBC-filtered table, one file per chain.

**Status & error surfacing**

- The results table shows the furthest MiXCR step's progress while MiXCR runs, "Processing clonotypes" through the post-MiXCR phase, and "Done" only when the whole block finishes.
- A sample whose MiXCR or VBC step failed shows "Error" instead of a false "Done"; the other samples of a failed run show "Stopped".
- A failed VBC step fails the block instead of reading as done.
- The settings warn when the selected preset is one the block cannot run.

**Tests**

- Block tests: an idle smoke test and end-to-end runs of the RNA Profiling and RNA Full-Length Profiling presets on synthetic Cellecta-shaped reads.
- Workflow tests plan every Cellecta preset from the MiXCR 4.7.0-415-develop step lists; model tests cover the V1 upgrade and the per-sample status.
- Python Tests CI: ruff gate and the whole pytest suite, golden comparisons against upstream included.

Existing projects re-run every sample on update.
