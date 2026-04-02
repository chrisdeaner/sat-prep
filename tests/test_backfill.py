"""
Tests for backfill_definitions.py

Covers:
  - Gemini JSON cleaning
  - CSV round-trip (backfill logic with mocked Gemini)
  - Dry run behavior
"""

import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module under test
sys_path_entry = str(Path(__file__).resolve().parent.parent / "scripts")
import sys
sys.path.insert(0, sys_path_entry)

import backfill_definitions as bf


# ---------------------------------------------------------------------------
# JSON cleaning tests
# ---------------------------------------------------------------------------

class TestCleanJsonString:
    """Tests for _clean_json_string()."""

    def test_strips_code_fences(self):
        raw = '```json\n[{"word": "test"}]\n```'
        result = bf._clean_json_string(raw)
        assert result == '[{"word": "test"}]'

    def test_plain_json_unchanged(self):
        raw = '[{"word": "test"}]'
        result = bf._clean_json_string(raw)
        assert result == raw


# ---------------------------------------------------------------------------
# Backfill integration tests (mocked Gemini)
# ---------------------------------------------------------------------------

class TestBackfill:
    """Integration tests for the backfill() function with mocked Gemini."""

    def _create_test_csv(self, tmp_dir: str) -> Path:
        """Create a test CSV with some missing definitions."""
        csv_path = Path(tmp_dir) / "sat_vocabulary.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["word", "definition", "score"])
            writer.writeheader()
            writer.writerow({"word": "eschew", "definition": "To deliberately avoid", "score": "6"})
            writer.writerow({"word": "capacious", "definition": "", "score": "3"})
            writer.writerow({"word": "banal", "definition": "", "score": "1"})
        return csv_path

    def test_backfill_fills_missing_definitions(self):
        """Should fill empty definitions using Gemini."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)

            def mock_gemini(words):
                return {
                    "capacious": "Having a lot of space; roomy.",
                    "banal": "Lacking originality; predictable and dull.",
                }

            with patch.object(bf, "CSV_PATH", csv_path):
                with patch.object(bf, "fetch_definitions_gemini", side_effect=mock_gemini):
                    stats = bf.backfill(dry_run=False)

            assert stats["total"] == 3
            assert stats["missing"] == 2
            assert stats["filled"] == 2
            assert stats["still_missing"] == 0

            # Verify CSV was updated
            with open(csv_path, "r") as f:
                rows = list(csv.DictReader(f))
            assert rows[0]["definition"] == "To deliberately avoid"  # unchanged
            assert rows[1]["definition"] == "Having a lot of space; roomy."
            assert rows[2]["definition"] == "Lacking originality; predictable and dull."

    def test_no_missing_definitions(self):
        """Should do nothing when all definitions are present."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "sat_vocabulary.csv"
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["word", "definition", "score"])
                writer.writeheader()
                writer.writerow({"word": "eschew", "definition": "To avoid", "score": "6"})

            with patch.object(bf, "CSV_PATH", csv_path):
                stats = bf.backfill(dry_run=False)

            assert stats["missing"] == 0
            assert stats["filled"] == 0

    def test_dry_run_does_not_modify_csv(self):
        """Dry run should not modify the CSV file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)

            with patch.object(bf, "CSV_PATH", csv_path):
                stats = bf.backfill(dry_run=True)

            assert stats["filled"] == 0
            assert stats["still_missing"] == 2

            # CSV should be unchanged
            with open(csv_path, "r") as f:
                rows = list(csv.DictReader(f))
            assert rows[1]["definition"] == ""
            assert rows[2]["definition"] == ""

    def test_partial_gemini_response(self):
        """Should handle Gemini returning definitions for only some words."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)

            def mock_gemini(words):
                return {"capacious": "Having a lot of space; roomy."}  # banal missing

            with patch.object(bf, "CSV_PATH", csv_path):
                with patch.object(bf, "fetch_definitions_gemini", side_effect=mock_gemini):
                    stats = bf.backfill(dry_run=False)

            assert stats["filled"] == 1
            assert stats["still_missing"] == 1
