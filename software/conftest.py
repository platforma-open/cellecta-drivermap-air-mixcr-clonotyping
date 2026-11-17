"""Shared fixtures for the VBC software golden tests (vbc-filtering, vbc-normalization).

A conftest.py here at the software root is auto-applied to every test below it, so both
packages' tests share one definition instead of carrying near-identical copies. The
golden-test bed is committed in-repo at `software/test-data/vbc-synthetic/`: 5 synthetic
`clones_*.tsv` fixtures plus verbatim copies of the upstream
`kitt-cellecta/AIR_VBC_filtering@main` scripts under `reference/`.

Reference-script paths are exposed as fixtures (`ref_filter`, `ref_norm`) rather than
module-level constants imported via `from conftest import …` (the pytest anti-pattern).
"""

import pathlib

import pytest

# software/conftest.py -> the bed sits next to it under test-data/.
BED = pathlib.Path(__file__).resolve().parent / "test-data" / "vbc-synthetic"


@pytest.fixture(scope="session")
def ref_filter():
    """Path to the upstream reference filter (`reference/filter_main.py`)."""
    return BED / "reference" / "filter_main.py"


@pytest.fixture(scope="session")
def ref_norm():
    """Path to the upstream reference normalize (`reference/normalize_main.py`)."""
    return BED / "reference" / "normalize_main.py"


@pytest.fixture(scope="session")
def fixtures():
    """Map fixture stem -> path, e.g. {'clones_main': .../clones_main.tsv}."""
    fx = {p.stem: p for p in sorted(BED.glob("clones_*.tsv"))}
    if not fx:
        # The bed is committed (software/test-data/vbc-synthetic/), so a missing fixture is
        # a hard error, not a reason to silently skip and go green.
        pytest.fail(
            f"committed golden-test bed missing at {BED} (no clones_*.tsv found); "
            "restore software/test-data/vbc-synthetic/ or regenerate it with generate.py",
            pytrace=False,
        )
    return fx
