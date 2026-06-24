"""Shared paths + fixtures for the VBC filter golden tests.

The golden-test bed (`~/Desktop/Data/vbc-synthetic/`) is local and uncommitted; it
holds 5 synthetic `clones_*.tsv` fixtures plus verbatim copies of the upstream
`kitt-cellecta/AIR_VBC_filtering@main` scripts under `reference/`. Tests compare our
ported scripts against those references on identical inputs. Run with the bed's venv:

    cd software/vbc-filtering && ~/Desktop/Data/vbc-synthetic/.venv/bin/python -m pytest test/ -v
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
