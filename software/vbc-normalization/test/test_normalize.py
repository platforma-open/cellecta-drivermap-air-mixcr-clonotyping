"""Golden comparison: our `normalize.py` vs upstream `main` (`reference/normalize_main.py`).

Normalize is tested in isolation from filter: we run the upstream filter once to produce
a real `*.kde.maximas.txt` + `*.clones_ALL.filtered.tsv`, then feed *that same* maximas +
filtered table to BOTH normalize scripts and compare. This decouples the normalize math
(`floor(x/f+0.5)`, drop zero-estimate clones, `NA` on NaN normFactor) from the filter port.

Encodes:
  - per-clone `templateEstimate` matches upstream main (incl. the zero-estimate drop),
  - our output additionally carries `templateEstimateFraction` (required by the block's
    downstream xsv import — upstream main does not compute it),
  - a NaN normFactor yields `templateEstimate = "NA"` (not a crash).

Expected RED against the current `normalize.py` (uses `ceil(x/f)`, no zero-drop, no NA
handling) and GREEN once Task 3 ports it.
"""
import pathlib
import shutil
import subprocess
import sys

import pandas as pd
import pytest

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
    """Produce a shared (maximas, filtered) input, run ref + our normalize, return (ours, ref)."""
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
    ref = pd.read_csv(refdir / f"{sample}.clones_ALL.quantified.tsv", sep="\t")

    # ours on the SAME maximas + filtered table
    our_out = tmp_path / "ours.tsv"
    subprocess.run(
        [sys.executable, str(NORM_SRC), str(maximas_copy), str(filtered_copy), str(our_out)],
        check=True,
        cwd=tmp_path,
    )
    ours = pd.read_csv(our_out, sep="\t")
    return ours, ref


def test_template_estimate_matches_main(fixtures, tmp_path):
    """clones_main: templateEstimate matches main (floor+0.5, zero-drop); fraction emitted."""
    ours, ref = _run_pair(fixtures, tmp_path, "clones_main")

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
    """clones_no_norm: NaN normFactor → templateEstimate == 'NA' (not a crash)."""
    ours, ref = _run_pair(fixtures, tmp_path, "clones_no_norm")

    assert "templateEstimateFraction" in ours.columns
    assert (ours["templateEstimate"].astype(str) == "NA").all(), \
        "NaN normFactor must yield templateEstimate == 'NA' for every clone"
    # upstream also marks every clone NA in this case
    assert (ref["templateEstimate"].astype(str) == "NA").all()
