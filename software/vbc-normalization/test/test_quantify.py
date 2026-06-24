"""Property + example tests for normalize.quantify_templates — the estimation math
isolated from the KDE filter.

The golden test (test_normalize.py) proves the math matches upstream on a real maximas +
filtered table, but is slow (it runs the upstream KDE filter to build that input). These
feed `quantify_templates` a tiny synthetic (maximas, filtered) pair directly, so they're
fast, KDE-free, need no test bed, and register in coverage. They lock the numeric contract:
round-half-up (`floor(x/f + 0.5)`, not ceil, not banker's rounding), drop zero-estimate
clones, and fractions that sum to 1. Not marked slow.
"""

import math
import os
import tempfile

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st
from normalize import quantify_templates


def _run(reads, norm_factor):
    """Run quantify_templates on a tiny synthetic (maximas, filtered) pair; return the output df.

    normalize reads normFactor from row 0, column index 3 of the maximas file.
    """
    with tempfile.TemporaryDirectory() as d:
        maxima = os.path.join(d, "m.kde.maximas.txt")
        with open(maxima, "w") as f:
            f.write(f"1\t2\t0\t{norm_factor}\t0\t0\t0\n")
        inp = os.path.join(d, "in.tsv")
        pd.DataFrame({"cloneId": list(range(len(reads))), "readCount": reads}).to_csv(inp, sep="\t", index=False)
        out = os.path.join(d, "out.tsv")
        quantify_templates(maxima, inp, out)
        return pd.read_csv(out, sep="\t")


@settings(deadline=None, max_examples=75)
@given(
    reads=st.lists(st.integers(min_value=1, max_value=100_000), min_size=1, max_size=60),
    norm_factor=st.floats(min_value=1.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
)
def test_template_estimate_is_round_half_up_and_nonzero(reads, norm_factor):
    """Surviving templateEstimate == floor(readCount/normFactor + 0.5); zero estimates are dropped."""
    res = _run(reads, norm_factor)
    assert (res["templateEstimate"] != 0).all()
    for cid, est in zip(res["cloneId"], res["templateEstimate"]):
        assert est == math.floor(reads[cid] / norm_factor + 0.5)


@settings(deadline=None, max_examples=75)
@given(
    reads=st.lists(st.integers(min_value=1, max_value=100_000), min_size=1, max_size=60),
    norm_factor=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
)
def test_fraction_sums_to_one_when_any_survive(reads, norm_factor):
    """templateEstimateFraction is each clone's share of the total estimate, so it sums to 1."""
    res = _run(reads, norm_factor)
    if len(res) > 0:
        assert abs(res["templateEstimateFraction"].sum() - 1.0) < 1e-9


def test_rounding_examples():
    """Concrete contract: .5 rounds UP (distinguishes from banker's), sub-0.5 drops the clone.

    With normFactor=100: 150->2 (1.5+0.5=2.0), 149->1 (1.99), 50->1 (0.5+0.5=1.0, half-up
    where banker's would give 0), 49->dropped (0.99->0), 10->dropped (0.6->0).
    """
    res = _run([150, 149, 50, 49, 10], norm_factor=100.0).set_index("cloneId")
    assert set(res.index) == {0, 1, 2}  # clones 3 (reads=49) and 4 (reads=10) dropped
    assert res.loc[0, "templateEstimate"] == 2
    assert res.loc[1, "templateEstimate"] == 1
    assert res.loc[2, "templateEstimate"] == 1
