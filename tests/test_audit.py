"""
Tests for audit_definitions.py

Covers:
  - Loading words from CSV
  - Applying corrections to CSV
  - Corrections file cleanup after apply
"""

import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys_path_entry = str(Path(__file__).resolve().parent.parent / "scripts")
import sys
sys.path.insert(0, sys_path_entry)

import audit_definitions as ad


class TestLoadWords:
    """Tests for load_words()."""

    def _create_csv(self, tmp_dir: str) -> Path:
        csv_path = Path(tmp_dir) / "vocab.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["word", "definition", "score"])
            writer.writeheader()
            writer.writerow({"word": "eschew", "definition": "To avoid", "score": "6"})
            writer.writerow({"word": "banal", "definition": "Boring", "score": "1"})
        return csv_path

    def test_loads_all_words(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_csv(tmp_dir)
            words = ad.load_words(csv_path)
            assert len(words) == 2

    def test_word_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_csv(tmp_dir)
            words = ad.load_words(csv_path)
            assert words[0]["word"] == "eschew"
            assert words[0]["definition"] == "To avoid"


class TestApplyCorrections:
    """Tests for apply_corrections()."""

    def _setup(self, tmp_dir: str):
        csv_path = Path(tmp_dir) / "vocab.csv"
        corrections_path = Path(tmp_dir) / "corrections.json"

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["word", "definition", "score"])
            writer.writeheader()
            writer.writerow({"word": "warranted", "definition": "To protect from danger", "score": "1"})
            writer.writerow({"word": "eschew", "definition": "To avoid", "score": "6"})

        return csv_path, corrections_path

    def test_applies_correction(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path, corrections_path = self._setup(tmp_dir)

            corrections = [
                {"word": "warranted", "issue": "Archaic", "suggested_definition": "Justified or deserved."}
            ]
            with open(corrections_path, "w") as f:
                json.dump(corrections, f)

            ad.apply_corrections(csv_path, corrections_path)

            words = ad.load_words(csv_path)
            assert words[0]["definition"] == "Justified or deserved."

    def test_leaves_uncorrected_words_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path, corrections_path = self._setup(tmp_dir)

            corrections = [
                {"word": "warranted", "issue": "Archaic", "suggested_definition": "Justified."}
            ]
            with open(corrections_path, "w") as f:
                json.dump(corrections, f)

            ad.apply_corrections(csv_path, corrections_path)

            words = ad.load_words(csv_path)
            assert words[1]["definition"] == "To avoid"  # eschew unchanged

    def test_deletes_corrections_file_after_apply(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path, corrections_path = self._setup(tmp_dir)

            with open(corrections_path, "w") as f:
                json.dump([{"word": "warranted", "issue": "x", "suggested_definition": "y"}], f)

            ad.apply_corrections(csv_path, corrections_path)

            assert not corrections_path.exists()

    def test_empty_corrections_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path, corrections_path = self._setup(tmp_dir)

            with open(corrections_path, "w") as f:
                json.dump([], f)

            ad.apply_corrections(csv_path, corrections_path)

            words = ad.load_words(csv_path)
            assert words[0]["definition"] == "To protect from danger"
