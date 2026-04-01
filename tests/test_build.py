"""
Tests for build_site.py

Covers:
  - CSV → JSON conversion
  - Sorting order (score desc, then alpha)
  - Output file creation
"""

import csv
import json
import tempfile
from pathlib import Path

import pytest

sys_path_entry = str(Path(__file__).resolve().parent.parent / "scripts")
import sys
sys.path.insert(0, sys_path_entry)

import build_site as bs


class TestCsvToJson:
    """Tests for csv_to_json()."""

    def _create_test_csv(self, tmp_dir: str) -> Path:
        """Create a minimal test CSV."""
        csv_path = Path(tmp_dir) / "vocab.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["word", "definition", "score"])
            writer.writeheader()
            writer.writerow({"word": "banal", "definition": "Boring and predictable", "score": "1"})
            writer.writerow({"word": "eschew", "definition": "To avoid", "score": "6"})
            writer.writerow({"word": "abridge", "definition": "To shorten", "score": "4"})
            writer.writerow({"word": "abate", "definition": "To reduce", "score": "3"})
        return csv_path

    def test_generates_json_file(self):
        """Should create a JSON file at the output path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)
            output_path = Path(tmp_dir) / "docs" / "words.json"

            bs.csv_to_json(csv_path, output_path)

            assert output_path.exists()

    def test_correct_word_count(self):
        """Should include all words from the CSV."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)
            output_path = Path(tmp_dir) / "docs" / "words.json"

            result = bs.csv_to_json(csv_path, output_path)

            assert len(result) == 4

    def test_sorted_by_score_desc_then_alpha(self):
        """Words should be sorted by score descending, then alphabetically."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)
            output_path = Path(tmp_dir) / "docs" / "words.json"

            result = bs.csv_to_json(csv_path, output_path)

            expected_order = ["eschew", "abridge", "abate", "banal"]
            actual_order = [w["word"] for w in result]
            assert actual_order == expected_order

    def test_json_structure(self):
        """Each word object should have word, definition, and score keys."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)
            output_path = Path(tmp_dir) / "docs" / "words.json"

            result = bs.csv_to_json(csv_path, output_path)

            for word_obj in result:
                assert "word" in word_obj
                assert "definition" in word_obj
                assert "score" in word_obj
                assert isinstance(word_obj["score"], int)

    def test_json_file_is_valid(self):
        """The output file should contain valid JSON."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)
            output_path = Path(tmp_dir) / "docs" / "words.json"

            bs.csv_to_json(csv_path, output_path)

            with open(output_path) as f:
                data = json.load(f)

            assert isinstance(data, list)
            assert len(data) == 4
