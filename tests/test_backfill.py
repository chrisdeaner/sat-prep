"""
Tests for backfill_definitions.py

Covers:
  - Free Dictionary API parsing (success + failure)
  - Gemini JSON cleaning
  - CSV round-trip (backfill logic with mocked APIs)
"""

import csv
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
sys_path_entry = str(Path(__file__).resolve().parent.parent / "scripts")
import sys
sys.path.insert(0, sys_path_entry)

import backfill_definitions as bf


# ---------------------------------------------------------------------------
# Free Dictionary API tests
# ---------------------------------------------------------------------------

class TestFetchDefinitionFreeApi:
    """Tests for fetch_definition_free_api()."""

    def test_successful_lookup(self):
        """Should return the first definition from a valid API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "word": "eschew",
                "meanings": [
                    {
                        "partOfSpeech": "verb",
                        "definitions": [
                            {"definition": "To deliberately avoid or keep away from."}
                        ],
                    }
                ],
            }
        ]

        with patch("backfill_definitions.requests.get", return_value=mock_response):
            result = bf.fetch_definition_free_api("eschew")

        assert result == "To deliberately avoid or keep away from."

    def test_word_not_found(self):
        """Should return None when the API returns 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("backfill_definitions.requests.get", return_value=mock_response):
            result = bf.fetch_definition_free_api("xyznotaword")

        assert result is None

    def test_empty_meanings(self):
        """Should return None when the response has no meanings."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"word": "test", "meanings": []}]

        with patch("backfill_definitions.requests.get", return_value=mock_response):
            result = bf.fetch_definition_free_api("test")

        assert result is None

    def test_network_error(self):
        """Should return None on network failure."""
        with patch("backfill_definitions.requests.get", side_effect=Exception("timeout")):
            result = bf.fetch_definition_free_api("hello")

        assert result is None


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
# Backfill integration test (mocked APIs)
# ---------------------------------------------------------------------------

class TestBackfill:
    """Integration test for the backfill() function with mocked APIs."""

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
        """Should fill empty definitions using the free API."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)

            # Mock the CSV path
            with patch.object(bf, "CSV_PATH", csv_path):
                # Mock free API: capacious found, banal not found
                def mock_free_api(word):
                    if word == "capacious":
                        return "Having a lot of space; roomy."
                    return None

                # Mock Gemini: banal found
                def mock_gemini(words):
                    return {"banal": "Lacking originality; unimaginative."}

                with patch.object(bf, "fetch_definition_free_api", side_effect=mock_free_api):
                    with patch.object(bf, "fetch_definitions_gemini", side_effect=mock_gemini):
                        with patch.object(bf, "DICT_API_DELAY", 0):  # no delay in tests
                            stats = bf.backfill(dry_run=False)

            # Verify stats
            assert stats["total"] == 3
            assert stats["missing"] == 2
            assert stats["filled_api"] == 1
            assert stats["filled_gemini"] == 1
            assert stats["still_missing"] == 0

            # Verify CSV was updated
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert rows[0]["definition"] == "To deliberately avoid"  # unchanged
            assert rows[1]["definition"] == "Having a lot of space; roomy."
            assert rows[2]["definition"] == "Lacking originality; unimaginative."

    def test_dry_run_does_not_modify_csv(self):
        """Dry run should not modify the CSV file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = self._create_test_csv(tmp_dir)

            with patch.object(bf, "CSV_PATH", csv_path):
                with patch.object(bf, "DICT_API_DELAY", 0):
                    stats = bf.backfill(dry_run=True)

            assert stats["filled_api"] == 0
            assert stats["filled_gemini"] == 0

            # CSV should be unchanged
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert rows[1]["definition"] == ""
            assert rows[2]["definition"] == ""
