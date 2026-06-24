"""Shared paths + fixtures for the VBC normalize golden tests.

Mirrors `software/vbc-filtering/test/conftest.py` — these are separate pnpm packages,
so each carries its own copy. The golden-test bed (`~/Desktop/Data/vbc-synthetic/`) is
local and uncommitted. Run with the bed's venv:

    cd software/vbc-normalization && ~/Desktop/Data/vbc-synthetic/.venv/bin/python -m pytest test/ -v
"""
import os
import pathlib

import pytest

BED = pathlib.Path(os.path.expanduser("~/Desktop/Data/vbc-synthetic"))
REF_FILTER = BED / "reference" / "filter_main.py"
REF_NORM = BED / "reference" / "normalize_main.py"


@pytest.fixture(scope="session")
def fixtures():
    """Map fixture stem -> path, e.g. {'clones_main': .../clones_main.tsv}."""
    fx = {p.stem: p for p in sorted(BED.glob("clones_*.tsv"))}
    if not fx:
        pytest.skip(f"golden-test bed not found at {BED}; regenerate it with generate.py")
    return fx
