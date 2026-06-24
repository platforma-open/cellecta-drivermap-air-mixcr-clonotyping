#!/usr/bin/env python3
"""VBC QC filtering for Cellecta DriverMap AIR.

Ported from kitt-cellecta/AIR_VBC_filtering@main (1_vbc_filtering/filter.py) with the
Platforma block adaptation layer applied (see software/vbc-filtering/IO_CONTRACT.md):

  - Explicit-file CLI: `filter.py <input.tsv> <output_prefix>` -> `<prefix>.tsv` +
    `<prefix>.kde.maximas.txt` (the workflow's vbc-processing.tpl.tengo contract), instead
    of upstream's directory/sample_name/--mode positional model.
  - The kit's molecule tag column is `tagValueMIVBC` (upstream uses `tagValueMIBC`).
  - The output preserves the block's downstream schema (one row per cloneId carrying
    clonotypeKey + the clone columns + readCount + a recomputed readFraction), NOT
    upstream's `readCount_BC1..8` pivot from simplify_clonotypes_table (which also drops
    readFraction and keys on targetSequences, a column the real mixcr export does not emit).
  - No matplotlib/seaborn histogram (no consumer; avoids the deps).
  - No report-file / "already done" idempotency guard (Platforma's per-step model owns it).
  - bulk mode is the only exercised path; the single_cell branches are retained but unused.

The KDE thresholding (`find_kde_mimima_threshold`) is upstream main's robust version: it
returns a tuple on every path (degenerate bins fall back to `default_low_thresh`), so the
`cannot unpack non-iterable NoneType` crash of the old fork cannot recur.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from sklearn.neighbors import KernelDensity


def qc_mixcr_output(input_file):
    """Check MiXCR output quality. Returns True if there are enough clonotypes to filter."""
    print("Running clonotype qc...")
    df = pd.read_csv(input_file, sep="\t", low_memory=False)
    clonotype_count = df.shape[0]
    if clonotype_count < 1000:
        return False
    return True


def barcode_hopping_filter(input_file, percentage, mode="bulk"):
    """Remove VBCs with low reads relative to other VBCs of the same clonotype."""
    print("Running barcode hopping filtering...")
    df = pd.read_csv(input_file, sep="\t", low_memory=False)
    if mode == "single_cell":
        group_cols = ["cloneId", "tagValueMIWELLNAME"]
    else:
        group_cols = ["cloneId"]
    # Maximum read count per group
    df["group_max"] = df.groupby(group_cols)["readCount"].transform("max")

    # Keep rows with readCount >= fraction_threshold of the group maximum
    fraction_threshold = percentage / 100
    filtered_df = df[df["readCount"] >= fraction_threshold * df["group_max"]].copy()
    filtered_df.drop(columns=["group_max"], inplace=True)

    original_rows = df.shape[0]
    filtered_rows = filtered_df.shape[0]
    original_rows_readSum = int(df["readCount"].sum())
    filtered_rows_readSum = int(filtered_df["readCount"].sum())
    print(f"Original number of rows: {original_rows:,}")
    print(f"Final number of rows after barcode hopping filtering: {filtered_rows:,}")
    print(
        f"Reads removed: {original_rows_readSum - filtered_rows_readSum:,} "
        f"({(original_rows_readSum - filtered_rows_readSum) / original_rows_readSum:.1%})"
    )
    print()
    return filtered_df


def find_kde_mimima_threshold(data, barcode_count, default_low_thresh, min_valley_depth=0.10):
    """Find a read-count threshold for a VBC bin via KDE minima detection.

    Returns a 6-tuple on every path:
        (threshold cutoff, left peak max, right peak max,
         threshold cutoff KDE value, left peak max KDE value, right peak max KDE value)
    Degenerate bins (<10 points, zero/NaN bandwidth, no maxima) fall back to
    `default_low_thresh` — the function never returns None.
    """
    if len(data) < 10:
        return (default_low_thresh, float("nan"), float("nan"), float("nan"), float("nan"), float("nan"))

    data_array = np.log10(data[data > 0].values).reshape(-1, 1)

    # Silverman's rule-of-thumb bandwidth
    n = len(data_array)
    sigma = np.std(data_array, ddof=1)
    bandwidth = 1.06 * sigma * (n ** (-1 / 5))
    if bandwidth == 0 or np.isnan(bandwidth):
        return (default_low_thresh, float("nan"), float("nan"), float("nan"), float("nan"), float("nan"))

    kde = KernelDensity(bandwidth=bandwidth)
    kde.fit(data_array)
    x = np.linspace(data_array.min(), data_array.max(), 1000).reshape(-1, 1)
    log_dens = kde.score_samples(x)

    minima = argrelextrema(log_dens, np.less)[0]
    maxima = argrelextrema(log_dens, np.greater)[0]

    if len(maxima) == 0:
        return (default_low_thresh, float("nan"), float("nan"), float("nan"), float("nan"), float("nan"))

    if len(maxima) == 1:
        left_max = 0  # first peak treated as non-existent at 0
        right_max = maxima[0]
        between_minima = minima[(minima > left_max) & (minima < right_max)]
        if between_minima.size > 0:
            selected_min = between_minima[np.argmin(log_dens[between_minima])]
            return (
                10 ** x[selected_min][0],
                10 ** x[left_max][0],
                10 ** x[right_max][0],
                np.exp(log_dens[selected_min]),
                np.exp(log_dens[left_max]),
                np.exp(log_dens[right_max]),
            )
        # unlikely (a maximum implies a low point) -> fall back to default
        return (
            default_low_thresh,
            10 ** x[left_max][0],
            10 ** x[right_max][0],
            np.exp(log_dens[default_low_thresh]),
            np.exp(log_dens[left_max]),
            np.exp(log_dens[right_max]),
        )

    if len(maxima) == 2:
        sorted_maxima = maxima[np.argsort(-log_dens[maxima])]
        top_two_max = sorted_maxima[:2]
        left_max, right_max = sorted(top_two_max)
        between_minima = minima[(minima > left_max) & (minima < right_max)]
        selected_min = between_minima[np.argmin(log_dens[between_minima])]

    elif len(maxima) > 2:
        # k-means-like split: pick the minimum giving the best left/right peak separation
        leftmost_max = np.min(maxima)
        rightmost_max = np.max(maxima)
        between_minima = minima[(minima > leftmost_max) & (minima < rightmost_max)]
        best_score = None
        best_min = None
        for candidate_min in between_minima:
            left_maximas = maxima[maxima < candidate_min]
            right_maximas = maxima[maxima > candidate_min]
            left_mean = np.mean(left_maximas)
            right_mean = np.mean(right_maximas)
            left_ssd = np.sum((left_maximas - left_mean) ** 2)
            right_ssd = np.sum((right_maximas - right_mean) ** 2)
            total_ssd = left_ssd + right_ssd
            if (best_score is None) or (total_ssd < best_score):
                best_score = total_ssd
                best_min = candidate_min

        if best_min is not None:
            selected_min = best_min
            left_maximas = maxima[maxima < selected_min]
            right_maximas = maxima[maxima > selected_min]
            left_max = left_maximas[np.argmax(log_dens[left_maximas])]
            right_max = right_maximas[np.argmax(log_dens[right_maximas])]

    # Valley-depth gate: a too-shallow valley is treated as a single peak
    min_log_dens = log_dens[selected_min]
    left_peak = log_dens[left_max]
    right_peak = log_dens[right_max]
    peak_max_lower = min(left_peak, right_peak)
    relative_depth = abs((peak_max_lower - min_log_dens) / peak_max_lower)
    if relative_depth >= min_valley_depth:
        return (
            10 ** x[selected_min][0],
            10 ** x[left_max][0],
            10 ** x[right_max][0],
            np.exp(log_dens[selected_min]),
            np.exp(log_dens[left_max]),
            np.exp(log_dens[right_max]),
        )
    else:
        zero_left_max = 0
        return (
            default_low_thresh,
            zero_left_max,
            10 ** x[right_max][0],
            np.exp(log_dens[default_low_thresh]),
            np.exp(log_dens[zero_left_max]),
            np.exp(log_dens[right_max]),
        )


def is_normalization_unreliable(
    nVBC, clone_total_reads, thresholds, thresholds_kde_values, right_maxes, right_maxes_kde_values
):
    """Return True if the normalization threshold for VBC bin `nVBC` looks unreliable."""
    unreliable_norm_flag = False
    print(f"Checking reliability of normalization for VBC = {nVBC}...")

    vbc_reads = clone_total_reads[clone_total_reads["barcode_count"] == nVBC]["readCount"]
    vbc_thresh = thresholds.get(nVBC, None)
    vbc_thresh_kde_value = thresholds_kde_values.get(nVBC, None)
    vbc_peak = right_maxes.get(nVBC, None)
    vbc_peak_kde_values = right_maxes_kde_values.get(nVBC, None)

    min_vbc_points = 10  # minimum data points for a reliable bin
    min_peak_distance = 2  # minimum fold distance between threshold and 2nd peak
    min_peak_height_diff = 2  # minimum KDE fold height difference

    if np.isnan(vbc_thresh) or np.isnan(vbc_thresh_kde_value) or np.isnan(vbc_peak) or np.isnan(vbc_peak_kde_values):
        print("WARNING: NaN value for either threshold or right max peak.")
        unreliable_norm_flag = True

    num_above_thresh = (vbc_reads > vbc_thresh).sum()
    if num_above_thresh < min_vbc_points:
        print("WARNING: Too few data points in VBC bin passing threshold. Normalization may be unreliable.")
        unreliable_norm_flag = True

    if vbc_thresh * min_peak_distance > vbc_peak or vbc_thresh_kde_value * min_peak_height_diff > vbc_peak_kde_values:
        print("WARNING: Second peak and threshold value too close in VBC. Normalization may be unreliable.")
        unreliable_norm_flag = True

    return unreliable_norm_flag


def reads_per_clonotype_filter(df, output_prefix, default_low_thresh, mode="bulk"):
    """Filter clonotypes with too few reads, per VBC bin; write the 7-column maximas file.

    Returns the surviving clonotypes grouped one row per cloneId (summed readCount,
    barcode_count, `tagValueMIVBC` dropped). Writes `<output_prefix>.kde.maximas.txt`.
    """
    print("Running VBC filtering...")
    if mode == "single_cell":
        group_cols = ["cloneId", "tagValueMIWELLNAME"]
        n_barcodes = 4
    else:
        group_cols = ["cloneId"]
        n_barcodes = 8

    clone_barcode_counts = df.groupby(group_cols)["tagValueMIVBC"].nunique()
    clone_total_reads = df.groupby(group_cols)["readCount"].sum().reset_index()
    clone_total_reads["barcode_count"] = clone_total_reads.set_index(group_cols).index.map(clone_barcode_counts)

    # --- Per-bin KDE thresholding ---
    thresholds = {}
    left_maxes = {}
    right_maxes = {}
    thresholds_kde_values = {}
    left_maxes_kde_values = {}
    right_maxes_kde_values = {}
    for barcode_count in range(1, n_barcodes + 1):
        subset = clone_total_reads[clone_total_reads["barcode_count"] == barcode_count]["readCount"]
        (
            thresholds[barcode_count],
            left_maxes[barcode_count],
            right_maxes[barcode_count],
            thresholds_kde_values[barcode_count],
            left_maxes_kde_values[barcode_count],
            right_maxes_kde_values[barcode_count],
        ) = find_kde_mimima_threshold(subset, barcode_count, default_low_thresh)

    # --- Threshold sanity checks: 20x-jump correction + monotonic non-decreasing ---
    sorted_keys = sorted(thresholds.keys())
    for i in range(1, len(sorted_keys)):
        current_key = sorted_keys[i]
        previous_key = sorted_keys[i - 1]

        # previous threshold 20x below current (only for VBC > 3)
        if thresholds[current_key] is not default_low_thresh and thresholds[previous_key] is not default_low_thresh:
            if current_key > 3:
                previousThresholdFoldx = thresholds[current_key] > 20 * thresholds[previous_key]
            else:
                previousThresholdFoldx = False
        else:
            previousThresholdFoldx = False

        # next threshold 20x above current
        if thresholds[current_key] is not default_low_thresh and current_key < len(sorted_keys):
            next_key = sorted_keys[i + 1]
            if thresholds[next_key] is not default_low_thresh:
                nextThresholdFoldx = thresholds[next_key] > 20 * thresholds[current_key]
            else:
                nextThresholdFoldx = False
        else:
            nextThresholdFoldx = False

        if previousThresholdFoldx or nextThresholdFoldx:
            thresholds[current_key] = thresholds[previous_key]

        if thresholds[current_key] < thresholds[previous_key]:
            thresholds[current_key] = thresholds[previous_key]

    # --- VBC=1 normalization reliability fallback (VBC1 -> VBC2 -> VBC3 -> NaN) ---
    vbc1_unreliability = is_normalization_unreliable(
        1, clone_total_reads, thresholds, thresholds_kde_values, right_maxes, right_maxes_kde_values
    )
    if vbc1_unreliability:
        print("WARNING: VBC=1 normalization may be unreliable.")
        vbc2_unreliability = is_normalization_unreliable(
            2, clone_total_reads, thresholds, thresholds_kde_values, right_maxes, right_maxes_kde_values
        )
        if vbc2_unreliability:
            print("WARNING: VBC=2 normalization may be unreliable.")
            vbc3_unreliability = is_normalization_unreliable(
                3, clone_total_reads, thresholds, thresholds_kde_values, right_maxes, right_maxes_kde_values
            )
            if vbc3_unreliability:
                print("WARNING: VBC=3 normalization may be unreliable.")
                right_maxes[1] = float("nan")
            else:
                right_maxes[1] = right_maxes[3] / 3  # peak of VBC=3 is 3x that of VBC=1
        else:
            right_maxes[1] = right_maxes[2] / 2  # peak of VBC=2 is 2x that of VBC=1

    # --- Write the 7-column maximas file (normalize.py reads iloc[0, 3] as normFactor) ---
    maximas_file = f"{output_prefix}.kde.maximas.txt"
    with open(maximas_file, "w") as f:
        for barcode_count in range(1, n_barcodes + 1):
            f.write(
                f"{barcode_count}\t{thresholds[barcode_count]}\t{left_maxes[barcode_count]}\t"
                f"{right_maxes[barcode_count]}\t{thresholds_kde_values[barcode_count]}\t"
                f"{left_maxes_kde_values[barcode_count]}\t{right_maxes_kde_values[barcode_count]}\n"
            )

    # --- Apply thresholds, keep passing clones ---
    clone_total_reads = clone_total_reads.copy()
    clone_total_reads.loc[:, "keep"] = clone_total_reads.apply(
        lambda row: row["readCount"] >= thresholds.get(row["barcode_count"], np.inf),
        axis=1,
    )
    clones_to_keep = clone_total_reads[clone_total_reads["keep"]][group_cols]
    final_data = df.merge(clones_to_keep, on=group_cols, how="inner").copy()

    # One row per clone: keep metadata (first), sum readCount, recompute barcode_count
    grouped_final_data = final_data.groupby(group_cols).first().reset_index()
    grouped_final_data["readCount"] = final_data.groupby(group_cols)["readCount"].sum().values
    grouped_final_data["barcode_count"] = grouped_final_data.set_index(group_cols).index.map(clone_barcode_counts)
    grouped_final_data = grouped_final_data.drop(columns=["tagValueMIVBC"], errors="ignore")
    grouped_final_data = grouped_final_data.sort_values("readCount", ascending=False)

    original_rows = df.shape[0]
    original_rows_readSum = int(df["readCount"].sum())
    filtered_rows_readSum = int(grouped_final_data["readCount"].sum())
    print(f"Original number of rows: {original_rows:,}")
    print(f"Surviving clonotypes after read filtering: {grouped_final_data.shape[0]:,}")
    print(
        f"Reads removed: {original_rows_readSum - filtered_rows_readSum:,} "
        f"({(original_rows_readSum - filtered_rows_readSum) / original_rows_readSum:.1%})"
    )
    print()

    return grouped_final_data


def main(input_file, output_prefix, mode="bulk"):
    """Block entry point: filter.py <input.tsv> <output_prefix> [--mode bulk]."""
    default_low_thresh = 2  # default VBC read threshold

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    output_file = f"{output_prefix}.tsv"
    maximas_file = f"{output_prefix}.kde.maximas.txt"

    df_in = pd.read_csv(input_file, sep="\t", low_memory=False)

    # Empty input -> valid empty output (block schema) + empty maximas
    if df_in.empty:
        print("Input is empty. Writing empty output file with headers.")
        empty_cols = [c for c in df_in.columns if c != "tagValueMIVBC"] + ["barcode_count"]
        pd.DataFrame(columns=empty_cols).to_csv(output_file, sep="\t", index=False)
        open(maximas_file, "w").close()
        return

    # QC fail -> pass the raw input through unfiltered + empty maximas
    if not qc_mixcr_output(input_file):
        print("QC failed (too few clonotypes). Passing input through unfiltered.")
        df_in.to_csv(output_file, sep="\t", index=False)
        open(maximas_file, "w").close()
        return

    # Full VBC filtering path
    percentage = 5  # barcode hopping cutoff
    df_bcHop = barcode_hopping_filter(input_file, percentage, mode=mode)
    df_filtered = reads_per_clonotype_filter(df_bcHop, output_prefix, default_low_thresh, mode=mode)

    # Preserve the block's downstream schema: recompute readFraction over surviving clones
    # (filtering changed the read total, so the carried-through value is stale).
    total_reads = df_filtered["readCount"].sum()
    df_filtered["readFraction"] = (df_filtered["readCount"] / total_reads) if total_reads else 0
    df_filtered = df_filtered.sort_values("readCount", ascending=False)
    df_filtered.to_csv(output_file, sep="\t", index=False)
    print(f"Filtered data saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VBC QC filtering for Cellecta DriverMap AIR.")
    parser.add_argument("input_file", type=str, help="Path to input TSV file.")
    parser.add_argument(
        "output_prefix", type=str, help="Prefix for output files (writes <prefix>.tsv + <prefix>.kde.maximas.txt)."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["bulk", "single_cell"],
        default="bulk",
        help="Processing mode: 'bulk' (default) or 'single_cell' DriverMap AIR.",
    )
    args = parser.parse_args()
    main(args.input_file, args.output_prefix, mode=args.mode)
