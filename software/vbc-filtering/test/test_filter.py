"""Golden comparison: our `filter.py` vs upstream `main` (`reference/filter_main.py`).

Encodes "our filter is in line with upstream main": on the same fixture, the surviving
clonotype set (by `cloneId`) and the per-clone summed `readCount` must match upstream
main. Our output is allowed to carry *extra* columns (e.g. `readFraction`, the block
schema) and a different shape (no `readCount_BC*` pivot) — but it must not drop a clone
main keeps, add one main drops, or disagree on a clone's `readCount`.

The port is complete; these guard that `filter.py` STAYS in line with upstream main — a
regression in our filter, or a divergence from upstream, turns them red. The full-filter
comparisons run the KDE on the large fixtures and are marked `@pytest.mark.slow`.
"""

import pathlib
import subprocess
import sys

import pandas as pd
import pytest

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


def _ref(fixture, tmp, ref_filter, sample="s"):
    """Run upstream main (`filter_main.py <input> <dir> <sample> --mode bulk`)."""
    subprocess.run(
        [sys.executable, str(ref_filter), str(fixture), str(tmp), sample, "--mode", "bulk"],
        check=True,
        cwd=tmp,
    )
    return pd.read_csv(tmp / f"{sample}.clones_ALL.filtered.tsv", sep="\t")


@pytest.mark.slow
@pytest.mark.parametrize("name", ["clones_main", "clones_unreliable_vbc1"])
def test_surviving_clonotypes_match_main(fixtures, tmp_path, name, ref_filter):
    """QC-pass fixtures: surviving clone set + per-clone readCount must match main."""
    ours = _ours(fixtures[name], _mkdir(tmp_path, "ours"))
    ref = _ref(fixtures[name], _mkdir(tmp_path, "ref"), ref_filter)

    assert set(ref["cloneId"]).issubset(set(ours["cloneId"])), f"{name}: our filter drops clones upstream main keeps"
    assert set(ours["cloneId"]) == set(ref["cloneId"]), f"{name}: surviving clonotype set differs from upstream main"

    merged = ours[["cloneId", "readCount"]].merge(
        ref[["cloneId", "readCount"]], on="cloneId", suffixes=("_ours", "_ref")
    )
    assert (merged["readCount_ours"] == merged["readCount_ref"]).all(), (
        f"{name}: per-clone readCount differs from upstream main"
    )


def test_qc_fail_keeps_all_clones_collapsed(fixtures, tmp_path, ref_filter):
    """clones_tiny (<1000 rows) → QC fail → no read filtering, but collapse to the block's
    one-row-per-clone schema.

    Upstream main copies the raw per-molecule input unchanged on QC fail. The block
    intentionally diverges: it still collapses molecule rows to one row per clone (drops
    tagValueMIVBC, recomputes readFraction) so downstream aggregate-abundance never sums
    readFraction over per-molecule rows. No clone is filtered out (that's what "QC fail"
    means — skip the statistical read filter), only the rows are collapsed.
    """
    raw = pd.read_csv(fixtures["clones_tiny"], sep="\t")
    ours = _ours(fixtures["clones_tiny"], _mkdir(tmp_path, "ours"))
    ref = _ref(fixtures["clones_tiny"], _mkdir(tmp_path, "ref"), ref_filter)

    # upstream copies the raw input unchanged on QC fail
    assert len(ref) == len(raw) and set(ref["cloneId"]) == set(raw["cloneId"])

    # ours keeps every clone (no read filtering on QC fail) ...
    assert set(ours["cloneId"]) == set(raw["cloneId"]), "QC-fail should keep all clones"
    # ... but collapses molecule rows to one row per clone (the block schema)
    assert len(ours) == raw["cloneId"].nunique(), "QC-fail should collapse to one row per clone"
    assert "tagValueMIVBC" not in ours.columns, "QC-fail output must drop the molecule tag column"
    assert "barcode_count" in ours.columns, "QC-fail output must carry barcode_count"

    # per-clone readCount is the sum of that clone's molecule rows
    expected_reads = raw.groupby("cloneId")["readCount"].sum().sort_index()
    got_reads = ours.set_index("cloneId")["readCount"].sort_index()
    assert (got_reads == expected_reads).all(), "QC-fail per-clone readCount must be the molecule-row sum"

    # readFraction is recomputed over the surviving clones and sums to 1
    assert abs(ours["readFraction"].sum() - 1.0) < 1e-9, "QC-fail readFraction must sum to 1 over the sample"


def test_empty_input(fixtures, tmp_path):
    """clones_empty (header only) → valid empty output, no crash."""
    ours = _ours(fixtures["clones_empty"], _mkdir(tmp_path, "ours"))
    assert len(ours) == 0
