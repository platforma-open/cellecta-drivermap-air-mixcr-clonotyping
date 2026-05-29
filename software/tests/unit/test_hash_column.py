"""Behavioral tests for hash-column/src/main.py.

The hash-column script adds deterministic hash columns to a TSV by concatenating
the chosen input columns and hashing them. These tests guard the parsing of
--calculate specs and the end-to-end CLI behavior (deterministic, collision-
sensitive hashes), since clonotypeKey identity downstream depends on it.

Run from software/:
    uv sync
    uv run pytest
"""

import csv
import subprocess
import sys
from pathlib import Path

import main  # hash-column/src/main.py, on pythonpath via pyproject
import pytest

MAIN_PY = Path(__file__).resolve().parents[2] / "hash-column" / "src" / "main.py"


class TestParseCalculateArgs:
    """parse_calculate_args turns repeated --calculate groups into (inputs, output) tuples."""

    # The common case: trailing element is the output column, the rest are inputs.
    def test_single_calculation(self):
        assert main.parse_calculate_args([["col_a", "col_b", "hash_ab"]]) == [(["col_a", "col_b"], "hash_ab")]

    # Multiple --calculate groups must each map independently.
    def test_multiple_calculations(self):
        assert main.parse_calculate_args([["a", "out1"], ["b", "c", "out2"]]) == [
            (["a"], "out1"),
            (["b", "c"], "out2"),
        ]

    # A group with no input column (only an output name) is a user error -> exit 1.
    def test_missing_input_column_exits(self):
        with pytest.raises(SystemExit):
            main.parse_calculate_args([["only_output"]])

    # Two groups writing the same output column would clobber each other -> exit 1.
    def test_duplicate_output_name_exits(self):
        with pytest.raises(SystemExit):
            main.parse_calculate_args([["a", "dup"], ["b", "dup"]])


def _write_tsv(path: Path, rows: list[dict]) -> None:
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _run_hash(input_table: Path, output_table: Path, *calculate: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(MAIN_PY),
            "--input-table",
            str(input_table),
            "--output-table",
            str(output_table),
            "--calculate",
            *calculate,
        ],
        check=True,
    )


class TestHashColumnCli:
    """End-to-end CLI behavior over a temp TSV."""

    # The hash column is added; equal inputs hash equal, different inputs hash different.
    def test_hash_is_deterministic_and_collision_sensitive(self, tmp_path):
        in_tsv = tmp_path / "in.tsv"
        out_tsv = tmp_path / "out.tsv"
        _write_tsv(
            in_tsv,
            [
                {"cloneId": "1", "vGene": "TRBV1", "jGene": "TRBJ1"},
                {"cloneId": "2", "vGene": "TRBV1", "jGene": "TRBJ1"},  # same v/j as row 1
                {"cloneId": "3", "vGene": "TRBV2", "jGene": "TRBJ1"},  # different v
            ],
        )
        _run_hash(in_tsv, out_tsv, "vGene", "jGene", "key")

        rows = _read_tsv(out_tsv)
        assert [r["cloneId"] for r in rows] == ["1", "2", "3"]
        assert "key" in rows[0]
        # Same (vGene, jGene) -> identical key; different vGene -> different key.
        assert rows[0]["key"] == rows[1]["key"]
        assert rows[0]["key"] != rows[2]["key"]

    # --hash-bytes controls entropy; running twice with the same args is reproducible.
    def test_reproducible_across_runs(self, tmp_path):
        in_tsv = tmp_path / "in.tsv"
        out1 = tmp_path / "out1.tsv"
        out2 = tmp_path / "out2.tsv"
        _write_tsv(in_tsv, [{"a": "x", "b": "y"}])
        _run_hash(in_tsv, out1, "a", "b", "h")
        _run_hash(in_tsv, out2, "a", "b", "h")
        assert _read_tsv(out1)[0]["h"] == _read_tsv(out2)[0]["h"]
