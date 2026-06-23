"""Golden comparison: our `normalize.py` vs upstream `main` (`reference/normalize_main.py`).

Normalize is tested in isolation from filter: we run the upstream filter once to produce
a real `*.kde.maximas.txt` + `*.clones_ALL.filtered.tsv`, then feed *that same* maximas +
filtered table to BOTH normalize scripts and compare. This decouples the normalize math
(`floor(x/f+0.5)`, drop zero-estimate clones, `NA` on NaN normFactor) from the filter port.

Encodes:
  - per-clone `templateEstimate` matches upstream main (incl. the zero-estimate drop),
  - our output additionally carries `templateEstimateFraction` (required by the block's
    downstream xsv import — upstream main does not compute it),
  - a NaN normFactor yields the literal `templateEstimate = "NA"` (not a crash).

Expected RED against the current `normalize.py` (uses `ceil(x/f)`, no zero-drop, no NA
handling) and GREEN once Task 3 ports it.

Note on reading NA: the quantified TSV stores the literal string "NA"; pandas would coerce
it to NaN on read, so the NA test reads with `na_filter=False` to compare the literal.
"""
import pathlib
import shutil
import subprocess
import sys

import pandas as pd

from conftest import REF_FILTER, REF_NORM

NORM_SRC = pathlib.Path(__file__).parents[1] / "src" / "normalize.py"


def _ref_filter(fixture, d, sample="s"):
    """Run upstream filter; return (maximas_path, filtered_path) it produced in `d`."""
    subprocess.run(
        [sys.executable, str(REF_FILTER), str(fixture), str(d), sample, "--mode", "bulk"],
        check=True,
        cwd=d,
    )
    return d / f"{sample}.kde.maximas.txt", d / f"{sample}.clones_ALL.filtered.tsv"


def _run_pair(fixtures, tmp_path, name, sample="s"):
    """Produce a shared (maximas, filtered) input, run ref + our normalize.

    Returns (our_output_path, ref_quantified_path) so each test reads with the dtype
    handling it needs (numeric vs literal-"NA").
    """
    refdir = tmp_path / "refdir"
    refdir.mkdir()
    maximas, filtered = _ref_filter(fixtures[name], refdir, sample)

    # snapshot inputs: upstream normalize deletes the filtered file on success
    maximas_copy = tmp_path / "maximas.txt"
    filtered_copy = tmp_path / "filtered.tsv"
    shutil.copy(maximas, maximas_copy)
    shutil.copy(filtered, filtered_copy)

    # reference normalize: reads <dir>/<sample>.* and writes <sample>.clones_ALL.quantified.tsv
    subprocess.run(
        [sys.executable, str(REF_NORM), str(refdir), sample, "--mode", "bulk"],
        check=True,
        cwd=refdir,
    )
    ref_out = refdir / f"{sample}.clones_ALL.quantified.tsv"

    # ours on the SAME maximas + filtered table
    our_out = tmp_path / "ours.tsv"
    subprocess.run(
        [sys.executable, str(NORM_SRC), str(maximas_copy), str(filtered_copy), str(our_out)],
        check=True,
        cwd=tmp_path,
    )
    return our_out, ref_out


def test_template_estimate_matches_main(fixtures, tmp_path):
    """clones_main: templateEstimate matches main (floor+0.5, zero-drop); fraction emitted."""
    our_out, ref_out = _run_pair(fixtures, tmp_path, "clones_main")
    ours = pd.read_csv(our_out, sep="\t")
    ref = pd.read_csv(ref_out, sep="\t")

    assert "templateEstimate" in ours.columns
    assert "templateEstimateFraction" in ours.columns, \
        "block normalize must emit templateEstimateFraction (downstream xsv import requires it)"

    # main drops templateEstimate == 0; ours (post-port) should too → identical surviving set
    assert set(ours["cloneId"]) == set(ref["cloneId"]), \
        "surviving (post zero-drop) clonotype set differs from upstream main"
    merged = ours[["cloneId", "templateEstimate"]].merge(
        ref[["cloneId", "templateEstimate"]], on="cloneId", suffixes=("_ours", "_ref")
    )
    assert (merged["templateEstimate_ours"] == merged["templateEstimate_ref"]).all(), \
        "per-clone templateEstimate differs from upstream main"


def test_nan_normfactor_yields_na(fixtures, tmp_path):
    """clones_no_norm: NaN normFactor → literal templateEstimate == 'NA' (not a crash)."""
    our_out, ref_out = _run_pair(fixtures, tmp_path, "clones_no_norm")
    # read with na_filter=False so the literal "NA" string is preserved (not coerced to NaN)
    ours = pd.read_csv(our_out, sep="\t", na_filter=False, dtype=str)
    ref = pd.read_csv(ref_out, sep="\t", na_filter=False, dtype=str)

    assert "templateEstimateFraction" in ours.columns
    assert (ours["templateEstimate"] == "NA").all(), \
        "NaN normFactor must yield literal templateEstimate == 'NA' for every clone"
    assert (ours["templateEstimateFraction"] == "NA").all()
    # upstream also marks every clone NA in this case
    assert (ref["templateEstimate"] == "NA").all()
