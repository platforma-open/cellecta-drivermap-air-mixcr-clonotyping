"""Golden comparison: our `filter.py` vs upstream `main` (`reference/filter_main.py`).

Encodes "our filter is in line with upstream main": on the same fixture, the surviving
clonotype set (by `cloneId`) and the per-clone summed `readCount` must match upstream
main. Our output is allowed to carry *extra* columns (e.g. `readFraction`, the block
schema) and a different shape (no `readCount_BC*` pivot) — but it must not drop a clone
main keeps, add one main drops, or disagree on a clone's `readCount`.

These tests are expected to FAIL (red) against the current un-ported `filter.py` and to
PASS (green) once Task 2 ports it to upstream main + the block adaptation layer.
"""
import pathlib
import subprocess
import sys

import pandas as pd
import pytest

from conftest import REF_FILTER

SRC = pathlib.Path(__file__).parents[1] / "src" / "filter.py"


def _mkdir(base, name):
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ours(fixture, tmp):
    """Run our filter (`filter.py <input> <output_prefix>`); return the output TSV."""
    out = tmp / "ours"
    subprocess.run([sys.executable, str(SRC), str(fixture), str(out)], check=True, cwd=tmp)
    return pd.read_csv(f"{out}.tsv", sep="\t")


def _ref(fixture, tmp, sample="s"):
    """Run upstream main (`filter_main.py <input> <dir> <sample> --mode bulk`)."""
    subprocess.run(
        [sys.executable, str(REF_FILTER), str(fixture), str(tmp), sample, "--mode", "bulk"],
        check=True,
        cwd=tmp,
    )
    return pd.read_csv(tmp / f"{sample}.clones_ALL.filtered.tsv", sep="\t")


@pytest.mark.parametrize("name", ["clones_main", "clones_unreliable_vbc1"])
def test_surviving_clonotypes_match_main(fixtures, tmp_path, name):
    """QC-pass fixtures: surviving clone set + per-clone readCount must match main."""
    ours = _ours(fixtures[name], _mkdir(tmp_path, "ours"))
    ref = _ref(fixtures[name], _mkdir(tmp_path, "ref"))

    assert set(ref["cloneId"]).issubset(set(ours["cloneId"])), \
        f"{name}: our filter drops clones upstream main keeps"
    assert set(ours["cloneId"]) == set(ref["cloneId"]), \
        f"{name}: surviving clonotype set differs from upstream main"

    merged = ours[["cloneId", "readCount"]].merge(
        ref[["cloneId", "readCount"]], on="cloneId", suffixes=("_ours", "_ref")
    )
    assert (merged["readCount_ours"] == merged["readCount_ref"]).all(), \
        f"{name}: per-clone readCount differs from upstream main"


def test_qc_fail_passthrough(fixtures, tmp_path):
    """clones_tiny (<1000 rows) → QC fail → passthrough (raw input, no filtering)."""
    raw = pd.read_csv(fixtures["clones_tiny"], sep="\t")
    ours = _ours(fixtures["clones_tiny"], _mkdir(tmp_path, "ours"))
    ref = _ref(fixtures["clones_tiny"], _mkdir(tmp_path, "ref"))

    # upstream copies the raw input unchanged on QC fail
    assert len(ref) == len(raw) and set(ref["cloneId"]) == set(raw["cloneId"])
    # ours must also pass through, not filter
    assert len(ours) == len(raw), "QC-fail should pass through all rows, not filter"
    assert set(ours["cloneId"]) == set(raw["cloneId"]), "QC-fail should keep all clones"


def test_empty_input(fixtures, tmp_path):
    """clones_empty (header only) → valid empty output, no crash."""
    ours = _ours(fixtures["clones_empty"], _mkdir(tmp_path, "ours"))
    assert len(ours) == 0
