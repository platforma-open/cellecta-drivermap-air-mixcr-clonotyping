"""Template-molecule estimation for Cellecta DriverMap AIR.

Ported from kitt-cellecta/AIR_VBC_filtering@main (2_quantify/normalize.py) with the
Platforma block adaptation layer:

  - Explicit-file CLI: `normalize.py <maxima_file> <input_file> <output_file>` (the
    workflow's vbc-processing.tpl.tengo contract), instead of upstream's directory/
    sample_name/--mode model.
  - Always emits `templateEstimateFraction` in addition to `templateEstimate` — the
    block's downstream xsv import requires it; upstream main does not compute it.
  - No report-file / "already done" idempotency guard (Platforma owns idempotency).

Estimation math is upstream main's: `templateEstimate = floor(readCount/normFactor + 0.5)`
(avoids banker's rounding), drop clones whose estimate rounds to 0, and emit `"NA"` when
the normalization factor is missing/NaN (degenerate VBC bins).
"""

import argparse
import math
import os

import pandas as pd


def quantify_templates(maxima_file, input_file, output_file):
    df = pd.read_csv(input_file, sep="\t")

    # normFactor is the right-peak max of the VBC=1 bin: column 3 of the maximas' first row.
    normFactor = float("nan")
    if os.path.exists(maxima_file) and os.path.getsize(maxima_file) > 0:
        try:
            normFactor = float(pd.read_csv(maxima_file, sep="\t", header=None).iloc[0, 3])
        except Exception as e:
            print(f"Error reading maxima file: {e}")

    if "readCount" not in df.columns:
        print(f"'readCount' column missing in {input_file}")
        df.to_csv(output_file, sep="\t", index=False)
        return

    # Empty input, or no usable normalization factor -> emit NA estimates (no crash).
    if df.empty or math.isnan(normFactor):
        df["templateEstimate"] = "NA"
        df["templateEstimateFraction"] = "NA"
        df.to_csv(output_file, sep="\t", index=False)
        return

    # floor(x/f + 0.5) avoids Python round()'s banker's rounding; drop zero-estimate clones.
    df["templateEstimate"] = df["readCount"].apply(lambda x: int(math.floor(x / normFactor + 0.5)))
    df = df[df["templateEstimate"] != 0].copy()

    total = df["templateEstimate"].sum()
    df["templateEstimateFraction"] = (df["templateEstimate"] / total) if total else 0
    df.to_csv(output_file, sep="\t", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantify templates based on normFactor")
    parser.add_argument("maxima_file", help="Path to the <prefix>.kde.maximas.txt file")
    parser.add_argument("input_file", help="Path to the filtered clones TSV")
    parser.add_argument("output_file", help="Path to write the quantified clones TSV")
    args = parser.parse_args()
    quantify_templates(args.maxima_file, args.input_file, args.output_file)
