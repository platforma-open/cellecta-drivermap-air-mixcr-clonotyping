# VBC filter/normalize I/O contract

Authoritative column contract for `filter.py` and `normalize.py`, **derived from the
workflow code** (not from a captured export — see below). Preset in scope:
`cellecta-human-rna-xcr-mivbc-drivermap-air-v2` (the FC298 kit). The other two V2
presets share the same abundance/key structure; the full-length preset adds more
sequence/key columns but the same rules apply.

## Why this is derived from code, not a captured TSV

mixcr runs only inside the platforma block; the `mixcr-export` output (filter.py's
input) is not an exposed block output, and the backend wipes exec workdirs after a
run — so there is no clean way to grab a real TSV. It is unnecessary: the downstream
workflow steps reference these exact column names and **succeed** in the live FC298
run, which makes the workflow code the authoritative source of the real column names.

Sources (all in `workflow/src/`):
- `get-export-params.lib.tengo` — per-preset `cloneColumnSpecs`, `abundanceColumnSpecs`, `keyColumns`, `keyAxesSpec`.
- `mixcr-export.tpl.tengo` — `mixcr exportClones` args + `-cloneId` + `-tags Molecule`; then `hash-column` adds `clonotypeKey`.
- `vbc-processing.tpl.tengo` — the two script CLIs.
- `process.tpl.tengo` — how the vbc output feeds `abundancePf` (Xsv) and `agg-clones` → `byCloneKey`.
- `agg-clones.tpl.tengo` — ptransform `max_by` ranked by `templateEstimate`, grouped on `clonotypeKey`, picking the clone columns.

## Tag column: `tagValueMIVBC` (NOT `tagValueMIBC`)

The molecule (VBC) tag column is **`tagValueMIVBC`**. Evidence:
- `mixcr-export.tpl.tengo:46` passes `-tags Molecule`; MiXCR names the value column from the kit's `MIVBC` molecule-tag pattern.
- The current `filter.py` reads `df.groupby('cloneId')['tagValueMIVBC'].nunique()` (`filter.py:147`) and drops it (`filter.py:193`) — and the live FC298 run reaches the KDE call past that access without a `KeyError`.
- The stale `// ... MIBC tags` comment at `mixcr-export.tpl.tengo:44` is the only `MIBC` mention and is cosmetic (Task 4 fixes it).

When porting from upstream `main`, rename every upstream `tagValueMIBC` → `tagValueMIVBC`.

## `filter.py` INPUT columns (the `mixcr-export` output)

The input TSV is the per-molecule `mixcr exportClones` table (one row per `(cloneId, molecule)`),
with `clonotypeKey` appended by `hash-column`. Columns present:

| Column | Source (mixcr arg / step) | Notes |
|---|---|---|
| `cloneId` | `-cloneId` | clone identifier; filter groups on this |
| `tagValueMIVBC` | `-tags Molecule` | the VBC molecular barcode; `nunique` per clone = `barcode_count` |
| `bestVHit`, `bestVGene` | `-vHit`, `-vGene` | gene hit + gene |
| `bestDHit`, `bestDGene` | `-dHit`, `-dGene` | D may be NA |
| `bestJHit`, `bestJGene` | `-jHit`, `-jGene` | |
| `bestCHit`, `bestCGene` | `-cHit`, `-cGene` | C may be NA |
| `nSeqCDR3`, `aaSeqCDR3` | `-nFeature CDR3`, `-aaFeature CDR3` | |
| `isotypePrimary` | `-isotype primary` | |
| `topChains` | `-topChains` | |
| `readCount` | `-readCount` | |
| `readFraction` | `-readFraction` | becomes stale after filtering → must be recomputed (see output) |
| `clonotypeKey` | `hash-column` (from `keyColumns` = `nSeqCDR3, bestVGene, bestJGene, bestCGene`) | the downstream axis |

## Required OUTPUT columns (vbc-processing `output.tsv` = `normalize.py` output)

The vbc-processing output TSV is consumed two ways in `process.tpl.tengo`, so it **must**
carry every column below or those imports fail:

1. **`abundancePf`** — Xsv import keyed on the `clonotypeKey` axis, reading the four abundance columns.
2. **`byCloneKey`** — `agg-clones` ptransform: `max_by` ranked on `templateEstimate`, grouped on `clonotypeKey`, picking the clone columns (`cloneColumnSpecs[].column`).

### Axis
- `clonotypeKey` — **required** (carried through from input, one value per `cloneId`).

### Abundance columns (4) — `abundanceColumnSpecs`
| Column | Produced by | Type / range |
|---|---|---|
| `readCount` | `filter.py` (summed per clone) | Long ≥ 1 |
| `readFraction` | `filter.py` — **recompute** `readCount / readCount.sum()` after filtering (input value is stale) | Double (0,1] |
| `templateEstimate` | `normalize.py` | Long ≥ 1 (or `NA` when normFactor is `nan`) |
| `templateEstimateFraction` | `normalize.py` — `templateEstimate / templateEstimate.sum()` | Double (0,1] (or `NA`) |

`templateEstimate` is `mainAbundanceColumn` (the agg ranking column) — it must be present and numeric for `agg-clones` to rank.

### Clone columns (12 unique) — `cloneColumnSpecs[].column`
Carried through from input by `filter.py` (one row per surviving `cloneId`):

`bestVHit`, `bestVGene`, `bestDHit`, `bestDGene`, `bestJHit`, `bestJGene`,
`bestCHit`, `bestCGene`, `nSeqCDR3`, `aaSeqCDR3`, `isotypePrimary`, `topChains`.

(No mutation columns for this preset — `coreGeneFeatures` is empty. `aaSeqCDR3` backs
two specs, `aa-seq-cdr3` and `clonotype-label`, but it is one column.)

## Schema-preservation rule for the port (Task 2 Step 5)

Upstream `main`'s `simplify_clonotypes_table` emits a `readCount_BC1..8` pivot and drops
`readFraction`. **Do not** substitute that pivot for the contract columns. The ported
`filter.py` output must keep: `clonotypeKey` + the 12 clone columns + `readCount` +
a **recomputed** `readFraction`. `tagValueMIVBC` is dropped after computing `barcode_count`
(it is not in the contract). If the `readCount_BC*` pivot is unused downstream, drop it.

## Empty / degenerate handling
- Empty input → write a valid empty `output.tsv` carrying the expected headers + empty maximas file.
- QC-fail → passthrough (input copied out unfiltered) + empty maximas file.
- `normalize.py`: missing/empty/`nan` normFactor → `templateEstimate = templateEstimateFraction = "NA"`, output still carries both columns.
