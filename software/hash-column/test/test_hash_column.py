"""Regression tests for hash-column/main.py.

Guards the side-effect import of `polars_hash`, which registers the `.chash` Expr
namespace. Without it, `concat_expr.chash.sha2_256()` raises
`'Expr' object has no attribute 'chash'` at runtime — the MILAB-6335 dev-block failure.
A linter's "unused import" autofix (F401) is exactly how that import got dropped, so these
tests fail loudly if it disappears again.
"""

import base64
import importlib
import pathlib
import subprocess
import sys

import pandas as pd
import polars as pl

MAIN_SRC = pathlib.Path(__file__).parents[1] / "src" / "main.py"

# The columns + output name the block actually invokes (mixcr-export.tpl.tengo):
#   --calculate nSeqCDR3 bestVGene bestJGene bestCGene clonotypeKey
KEY_COLS = ["nSeqCDR3", "bestVGene", "bestJGene", "bestCGene"]


def test_hash_column_adds_clonotype_key(tmp_path):
    """The exact block invocation hashes the 4 key columns into clonotypeKey and exits 0."""
    inp = tmp_path / "input.tsv"
    out = tmp_path / "output.tsv"
    pd.DataFrame(
        [
            ["CASSLGAETQYF", "TRBV5-1", "TRBJ2-5", "TRBC2"],
            ["CASSLGAETQYF", "TRBV5-1", "TRBJ2-5", "TRBC2"],  # identical -> same key
            ["CASRPGQGYEQYF", "TRBV28", "TRBJ2-7", "TRBC2"],  # different -> different key
        ],
        columns=KEY_COLS,
    ).to_csv(inp, sep="\t", index=False)

    res = subprocess.run(
        [
            sys.executable,
            str(MAIN_SRC),
            "--input-table",
            str(inp),
            "--output-table",
            str(out),
            "--calculate",
            *KEY_COLS,
            "clonotypeKey",
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"hash-column exited {res.returncode}; stderr:\n{res.stderr}\n"
        "(a missing `import polars_hash` makes `.chash` unavailable — see MILAB-6335)"
    )

    df = pd.read_csv(out, sep="\t", dtype=str)
    assert "clonotypeKey" in df.columns
    keys = df["clonotypeKey"].tolist()
    assert all(keys), "every row must get a non-empty hash key"
    assert keys[0] == keys[1], "identical key columns must hash identically (determinism)"
    assert keys[0] != keys[2], "different key columns must hash differently"
    # default --hash-bytes 12 -> 12 raw bytes, base64-encoded
    assert len(base64.b64decode(keys[0])) == 12


def test_chash_namespace_registered_on_import():
    """Importing main.py must register the `.chash` Expr namespace (fast, direct guard)."""
    importlib.import_module("main")  # hash-column/src is on pytest pythonpath
    assert hasattr(pl.col("x"), "chash"), (
        "`.chash` Expr namespace not registered — `import polars_hash` is missing from main.py"
    )
