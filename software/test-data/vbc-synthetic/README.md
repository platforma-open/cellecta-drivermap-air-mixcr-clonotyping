# Synthetic VBC test data (Cellecta DriverMap AIR)

Synthetic test data for the VBC `filter.py` / `normalize.py` scripts
(MILAB-6335 item 2 — aligning the block fork with `kitt-cellecta/AIR_VBC_filtering` main).
**Committed in-repo** as the golden-test bed for `software/vbc-filtering` and
`software/vbc-normalization` (see their `test/`). The `clones_*.tsv` fixtures are
deterministic — regenerate any time with `python3 generate.py` (pure stdlib, seed=42).

## What this is

Synthetic "exported clones" TSVs in the format the VBC scripts consume. Each row is one
`(cloneId, validator-barcode)` observation with a `readCount`. `tagValueMIBC` is one of the
8 fixed DriverMap validator barcodes `BC1..BC8`; a clone's **VBC count** = how many distinct
BCs it was seen with (1..8). `tagValueMIVBC` is included as a copy so the *current* block
script (which still uses the buggy `MIVBC` name) also runs.

Columns: `cloneId, tagValueMIBC, tagValueMIVBC, readCount, readFraction, targetSequences,
nSeqCDR3, aaSeqCDR3, bestVGene, bestJGene, bestCGene, isotypePrimary, topChains, clonotypeKey`.

Read model: per VBC bin `b`, "real" clones ~ lognormal(median 150·b) and "noise" clones ~
lognormal(median 7) → each bin is bimodal (noise peak vs real peak), real peaks scale with
VBC count. Bin 2 gets a 2nd high-read sub-population (→ tri-modal). ~12% of multi-VBC clones
in `clones_main` are barcode-hopping (one dominant BC + sub-5% BCs).

## Fixtures

| File | Targets |
|---|---|
| `clones_main.tsv` (1980 clones, 8760 rows) | QC pass; bins 1–8 each well-populated & bimodal; barcode hopping; bin-2 tri-modal; full filter→normalize path |
| `clones_tiny.tsv` (64 clones, 160 rows) | QC fail (<1000 rows) → passthrough, no filtering |
| `clones_empty.tsv` (header only) | empty-input handling |
| `clones_unreliable_vbc1.tsv` (bin 1 = 5 clones) | VBC=1 normalization unreliable → fallback to VBC=2 (`right_maxes[1] = right_maxes[2]/2`) |
| `clones_no_norm.tsv` (bins 1,2,3 sparse) | VBC 1/2/3 all unreliable → normFactor = NaN → `templateEstimate = "NA"` |

## Verified coverage (ran upstream `main` on the fixtures — observed each branch fire)

| Condition | Fixture | Evidence |
|---|---|---|
| QC pass → filtering | clones_main | 8760 rows ≥ 1000 |
| QC fail → passthrough | clones_tiny | 160 in = 160 out, no KDE |
| Barcode-hopping filter (5%) | clones_main | 392 rows / 6452 reads removed |
| Per-bin KDE on all 8 VBC bins | clones_main | maximas has 8 rows, real KDE (≥10 clones/bin) |
| Bimodal valley threshold | clones_main | noise ~5–8, real 178→1155, thresholds 31.7→97.2 |
| Monotonic non-decreasing thresholds | clones_main | thresholds increase across bins |
| Mutated-sequence filter | clones_main | 8368→4048 rows |
| Normalization `floor(x/f+0.5)` | clones_main | normFactor 178.31, templateEstimate 1–10 |
| Reliability fallback VBC1→VBC2 | clones_unreliable_vbc1 | VBC1 rightMax 149.73 = VBC2 299.46 / 2 |
| normFactor NaN → `NA` | clones_no_norm | 612 clones templateEstimate = NA |
| Empty input | clones_empty | no crash |

**Not forced by these fixtures** (paths exist; would need extra engineering to guarantee):
`>2-maxima` k-means split (bin-2 tri-modal is engineered but not independently confirmed from
output); the 20×-jump "3+ VBC" threshold *correction* (thresholds came out cleanly monotonic,
so no correction was needed); the shallow-valley `min_valley_depth` collapse; forced
zero-estimate drop (the read filter already removes the very-low-read clones).

## How to run

Deps live in a local `uv` venv (python 3.12, block-pinned pandas/numpy/sklearn/scipy +
matplotlib/seaborn for upstream main's histogram):

```bash
# one-time
uv venv --python 3.12 .venv
uv pip install --python .venv pandas==2.2.3 numpy==2.2.6 scikit-learn==1.6.1 scipy==1.15.3 matplotlib seaborn

# upstream main (reference). filter: <input> <out-dir> <sample> --mode bulk
.venv/bin/python reference/filter_main.py clones_main.tsv out main --mode bulk
.venv/bin/python reference/normalize_main.py out main --mode bulk
# → out/main.kde.maximas.txt, out/main.clones_ALL.filtered.tsv, out/main.clones_ALL.quantified.tsv
```

`reference/filter_main.py` / `normalize_main.py` are verbatim copies of
`kitt-cellecta/AIR_VBC_filtering@main` `1_vbc_filtering/filter.py` / `2_quantify/normalize.py`.

## Use for the item-2 port (the parked plan)

This is the golden-test bed for `.meta/plans/2026-06-22-vbc-scripts-upstream-alignment.md`:
when the block's `filter.py`/`normalize.py` are ported, diff their output against
`reference/*_main.py` on these fixtures (Tasks 1–3). It validates the **algorithm** port and
the ours-vs-main equivalence.

**Caveat — still want one real exported TSV.** This data's *schema* (column names,
`tagValueMIBC`, the `BC1..8` design) is reconstructed from reading the upstream + block code,
not from a real `mixcr export`. A single real exported clones TSV (Task 0) is still needed to
confirm the column names match reality and to validate the downstream block schema. Notably,
upstream main's filtered output here is `cloneId, readCount_BC1..BC8, readCount, <metadata>` —
the `simplify_clonotypes_table` pivot, **with no `readFraction`** — which is exactly the
block-incompatibility the port must reconcile (preserve the block's expected columns).
