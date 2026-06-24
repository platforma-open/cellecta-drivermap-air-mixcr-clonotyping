"""Property tests for filter.find_kde_mimima_threshold.

This is the function whose old version crashed with 'cannot unpack non-iterable NoneType'
on degenerate VBC bins. The golden tests (test_filter.py) prove the port matches upstream
on 5 fixtures; these prove the structural invariant the port was built to guarantee — a
6-tuple of numbers on EVERY input, never None — over generated read-count distributions.

Imported directly (not run via subprocess), so unlike the golden tests these are fast,
need no test bed, and register in coverage. Not marked slow.
"""

import math

import pandas as pd
from filter import find_kde_mimima_threshold
from hypothesis import given, settings
from hypothesis import strategies as st

DEFAULT_LOW_THRESH = 2


@settings(deadline=None, max_examples=75)
@given(reads=st.lists(st.integers(min_value=1, max_value=1_000_000), max_size=300))
def test_always_returns_six_tuple_never_none(reads):
    """Every code path returns a 6-tuple — never None, never a crash (the ported regression)."""
    result = find_kde_mimima_threshold(
        pd.Series(reads, dtype="int64"), barcode_count=1, default_low_thresh=DEFAULT_LOW_THRESH
    )
    assert result is not None
    assert isinstance(result, tuple)
    assert len(result) == 6


@settings(deadline=None, max_examples=75)
@given(reads=st.lists(st.integers(min_value=1, max_value=1_000_000), max_size=300))
def test_threshold_is_a_positive_real(reads):
    """The threshold (element 0) is always a positive number — a read-count cutoff, never NaN/None."""
    threshold = find_kde_mimima_threshold(
        pd.Series(reads, dtype="int64"), barcode_count=1, default_low_thresh=DEFAULT_LOW_THRESH
    )[0]
    assert isinstance(threshold, (int, float))
    assert not (isinstance(threshold, float) and math.isnan(threshold))
    assert threshold > 0


def test_degenerate_bin_falls_back_to_default():
    """Fewer than 10 points (a degenerate bin) → threshold falls back to default_low_thresh."""
    result = find_kde_mimima_threshold(pd.Series([5, 9, 12], dtype="int64"), 1, DEFAULT_LOW_THRESH)
    assert result[0] == DEFAULT_LOW_THRESH


def test_zero_variance_bin_falls_back_to_default():
    """Enough points but zero spread (all identical) → bandwidth 0 → default_low_thresh."""
    result = find_kde_mimima_threshold(pd.Series([100] * 30, dtype="int64"), 1, DEFAULT_LOW_THRESH)
    assert result[0] == DEFAULT_LOW_THRESH
