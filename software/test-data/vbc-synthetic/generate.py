#!/usr/bin/env python3
"""
Synthetic Cellecta DriverMap AIR "exported clones" TSVs for testing the VBC
filter.py / normalize.py scripts (block fork vs kitt-cellecta upstream main).

Pure standard library — no numpy/pandas needed to GENERATE (so it runs on any
python3). The VBC scripts themselves still need pandas/numpy/sklearn/scipy to RUN.

Row model: each row is one (cloneId, validator-barcode) observation with a
readCount. tagValueMIBC is one of the 8 fixed DriverMap validator barcodes
BC1..BC8 (upstream `simplify_clonotypes_table` pivots into readCount_BC1..BC8).
`barcode_count` (per clone) = how many distinct BCs the clone was seen with.

Conditions each fixture targets are documented in README.md. Deterministic (seeded).
"""
import csv
import math
import random
import os

SEED = 42
OUTDIR = os.path.dirname(os.path.abspath(__file__))
BARCODES = [f"BC{i}" for i in range(1, 9)]          # the 8 fixed validator barcodes
NTS = "ACGT"
AAS = "ACDEFGHIKLMNPQRSTVWY"
VGENES = ["TRBV5-1", "TRBV7-2", "TRBV20-1", "IGHV3-23", "IGHV1-69", "TRAV1-2"]
JGENES = ["TRBJ2-1", "TRBJ1-2", "IGHJ4", "IGHJ6", "TRAJ33"]
CGENES = ["TRBC1", "IGHM", "IGHG1", "TRAC", ""]


def rseq(rng, alphabet, n):
    return "".join(rng.choice(alphabet) for _ in range(n))


def lognormal_int(rng, median, log_sigma, lo=1):
    """A positive integer read count ~ lognormal(median, log_sigma)."""
    v = math.exp(rng.normalvariate(math.log(median), log_sigma))
    return max(lo, int(round(v)))


def make_clone(rng, cid, barcode_count, kind, hopping, real_base, real_log_sigma,
               noise_median, noise_log_sigma, real_level_mult=1.0):
    """Build one clone: metadata + a list of (BC, readCount) rows.

    kind == "real": total reads ~ real_base * barcode_count * real_level_mult
                    (reads scale ~linearly with VBC count — the "doubling" the
                    upstream threshold check relies on). High → survives filtering.
    kind == "noise": low total reads, independent of barcode_count → filtered out.
    hopping == True: one dominant BC + the rest get <5% of its reads (barcode
                     hopping; the 5% barcode_hopping_filter drops the low ones).
    """
    if kind == "real":
        total = lognormal_int(rng, real_base * barcode_count * real_level_mult, real_log_sigma)
    else:
        total = lognormal_int(rng, noise_median, noise_log_sigma)

    bcs = rng.sample(BARCODES, barcode_count)
    if hopping and barcode_count >= 2:
        # dominant BC gets ~92%, others share a tiny remainder (each < 5% of dominant)
        dominant = int(round(total * 0.92))
        rest = max(barcode_count - 1, 1)
        small = max(1, int(round(dominant * 0.02)))          # ~2% of dominant → below 5% cutoff
        per = [dominant] + [small] * (barcode_count - 1)
    else:
        # split evenly with mild jitter
        base = max(1, total // barcode_count)
        per = [max(1, base + rng.randint(-base // 4, base // 4)) for _ in range(barcode_count)]

    # per-clone metadata (constant across the clone's BC rows)
    aa = rseq(rng, AAS, rng.randint(10, 16))
    meta = {
        "targetSequences": rseq(rng, NTS, rng.randint(80, 130)),
        "nSeqCDR3": rseq(rng, NTS, len(aa) * 3),
        "aaSeqCDR3": aa,
        "bestVGene": rng.choice(VGENES),
        "bestJGene": rng.choice(JGENES),
        "bestCGene": rng.choice(CGENES),
        "isotypePrimary": rng.choice(["IgM", "IgG", "IgA", ""]),
        "topChains": rng.choice(["TRB", "TRA", "IGH", "IGK", "IGL"]),
        "clonotypeKey": "C-" + rseq(rng, "ABCDEFGHJKLMNPQRSTUVWXYZ23456789", 8),
    }
    rows = [{"tagValueMIBC": bc, "readCount": rc} for bc, rc in zip(bcs, per)]
    return cid, meta, rows


def build(rng, spec):
    """spec: dict bin -> (n_real, n_noise, n_hopping, real_level_mult).
    Returns a flat list of row dicts (exported-clones format)."""
    clones = []
    cid = 0
    for b in sorted(spec):
        n_real, n_noise, n_hop, lvl = spec[b]
        for i in range(n_real):
            hop = i < n_hop
            clones.append(make_clone(rng, f"clone{cid}", b, "real", hop,
                                     real_base=150, real_log_sigma=0.16,
                                     noise_median=7, noise_log_sigma=0.30,
                                     real_level_mult=lvl))
            cid += 1
        for _ in range(n_noise):
            clones.append(make_clone(rng, f"clone{cid}", b, "noise", False,
                                     real_base=150, real_log_sigma=0.16,
                                     noise_median=7, noise_log_sigma=0.30))
            cid += 1

    # flatten + compute readFraction over all rows
    flat = []
    for c_id, meta, rows in clones:
        for r in rows:
            row = {"cloneId": c_id, "tagValueMIBC": r["tagValueMIBC"],
                   "tagValueMIVBC": r["tagValueMIBC"],  # alias so the CURRENT (MIVBC) block script also runs
                   "readCount": r["readCount"]}
            row.update(meta)
            flat.append(row)
    total_reads = sum(r["readCount"] for r in flat) or 1
    for r in flat:
        r["readFraction"] = round(r["readCount"] / total_reads, 9)
    return flat


COLUMNS = ["cloneId", "tagValueMIBC", "tagValueMIVBC", "readCount", "readFraction",
           "targetSequences", "nSeqCDR3", "aaSeqCDR3", "bestVGene", "bestJGene",
           "bestCGene", "isotypePrimary", "topChains", "clonotypeKey"]


def write_tsv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n_clones = len({r["cloneId"] for r in rows})
    print(f"  wrote {os.path.basename(path):32s} rows={len(rows):6d}  clones={n_clones:5d}")


def main():
    rng = random.Random(SEED)

    # --- clones_main.tsv: comprehensive. QC pass; bins 1..8 each well-populated &
    #     bimodal (noise peak ~7 reads, real peak ~150*b). Bin 2 has a 2nd real
    #     sub-population (level x4) → 3 maxima. ~12% hopping clones in bins >=2.
    main_spec = {}
    for b in range(1, 9):
        n_real = 120
        n_noise = 120
        n_hop = 0 if b == 1 else 14
        main_spec[b] = (n_real, n_noise, n_hop, 1.0)
    main_rows = build(rng, main_spec)
    # add a higher-read real sub-population to bin 2 → tri-modal KDE (>2 maxima)
    rng2 = random.Random(SEED + 1)
    extra = []
    for i in range(60):
        c_id, meta, rows = make_clone(rng2, f"cloneX{i}", 2, "real", False,
                                      real_base=150, real_log_sigma=0.12,
                                      noise_median=7, noise_log_sigma=0.30,
                                      real_level_mult=4.0)
        for r in rows:
            row = {"cloneId": c_id, "tagValueMIBC": r["tagValueMIBC"],
                   "tagValueMIVBC": r["tagValueMIBC"], "readCount": r["readCount"]}
            row.update(meta)
            extra.append(row)
    main_rows += extra
    tot = sum(r["readCount"] for r in main_rows) or 1
    for r in main_rows:
        r["readFraction"] = round(r["readCount"] / tot, 9)
    write_tsv(os.path.join(OUTDIR, "clones_main.tsv"), main_rows)

    # --- clones_tiny.tsv: < 1000 rows → qc_mixcr_output returns False (passthrough).
    tiny_rng = random.Random(SEED + 2)
    tiny_spec = {b: (8, 8, 2, 1.0) for b in range(1, 5)}     # ~64 clones, ~200 rows
    write_tsv(os.path.join(OUTDIR, "clones_tiny.tsv"), build(tiny_rng, tiny_spec))

    # --- clones_empty.tsv: header only → empty-input path.
    write_tsv(os.path.join(OUTDIR, "clones_empty.tsv"), [])

    # --- clones_unreliable_vbc1.tsv: VBC=1 bin sparse (< 10 clones) → VBC=1
    #     normalization unreliable → upstream falls back to VBC=2 peak/2.
    unrel_rng = random.Random(SEED + 3)
    # No hopping here: hopping clones get their low VBCs dropped and migrate into
    # bin 1 after barcode_count is recomputed, which would un-sparse bin 1. Keep
    # bin 1 genuinely sparse (< 10 clones) so VBC=1 normalization is unreliable.
    unrel_spec = {1: (3, 2, 0, 1.0)}                          # only 5 clones in bin 1
    for b in range(2, 9):
        unrel_spec[b] = (120, 120, 0, 1.0)
    write_tsv(os.path.join(OUTDIR, "clones_unreliable_vbc1.tsv"), build(unrel_rng, unrel_spec))

    # --- clones_no_norm.tsv: VBC=1,2,3 all sparse → all unreliable → right_maxes[1]
    #     becomes NaN → normalize emits templateEstimate = "NA" (no normalization).
    nonorm_rng = random.Random(SEED + 4)
    nonorm_spec = {1: (3, 1, 0, 1.0), 2: (3, 1, 0, 1.0), 3: (3, 1, 0, 1.0)}
    for b in range(4, 9):
        nonorm_spec[b] = (120, 120, 0, 1.0)
    write_tsv(os.path.join(OUTDIR, "clones_no_norm.tsv"), build(nonorm_rng, nonorm_spec))

    # --- coverage summary for clones_main ---
    print("\nclones_main per-bin clone counts (real vs noise) and read medians:")
    from collections import defaultdict
    by_clone = defaultdict(list)
    for r in main_rows:
        by_clone[r["cloneId"]].append(r["readCount"])
    bins = defaultdict(lambda: {"n": 0, "totals": []})
    # recompute barcode_count + total per clone
    bc_count = defaultdict(set)
    for r in main_rows:
        bc_count[r["cloneId"]].add(r["tagValueMIBC"])
    for cid, reads in by_clone.items():
        b = len(bc_count[cid])
        bins[b]["n"] += 1
        bins[b]["totals"].append(sum(reads))
    for b in sorted(bins):
        tots = sorted(bins[b]["totals"])
        med = tots[len(tots) // 2]
        lo = tots[len(tots) // 10]
        hi = tots[len(tots) * 9 // 10]
        print(f"  VBC={b}: clones={bins[b]['n']:4d}  reads p10/median/p90 = {lo}/{med}/{hi}")


if __name__ == "__main__":
    main()
