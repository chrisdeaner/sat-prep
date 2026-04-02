"""
Tests for generate_sentences.py and build_site.py sentence merging.

Covers:
  - Loading words from CSV
  - Sentence merging into words.json during build
  - Build works without sentences.json
"""

import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys_path_entry = str(Path(__file__).resolve().parent.parent / "scripts")
import sys
sys.path.insert(0, sys_path_entry)

import generate_sentences as gs
import build_site as bs


class TestLoadWords:
    """Tests for generate_sentences.load_words()."""

    def test_loads_word_strings(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "vocab.csv"
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["word", "definition", "score"])
                writer.writeheader()
                writer.writerow({"word": "eschew", "definition": "To avoid", "score": "6"})
                writer.writerow({"word": "banal", "definition": "Boring", "score": "1"})

            words = gs.load_words(csv_path)
            assert words == ["eschew", "banal"]


class TestBuildWithSentences:
    """Tests for build_site.py sentence merging."""

    def _setup(self, tmp_dir: str):
        csv_path = Path(tmp_dir) / "vocab.csv"
        sentences_path = Path(tmp_dir) / "sentences.json"
        output_path = Path(tmp_dir) / "docs" / "words.json"

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["word", "definition", "score"])
            writer.writeheader()
            writer.writerow({"word": "eschew", "definition": "To avoid", "score": "6"})
            writer.writerow({"word": "banal", "definition": "Boring", "score": "1"})

        return csv_path, sentences_path, output_path

    def test_merges_sentences_into_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path, sentences_path, output_path = self._setup(tmp_dir)

            sentences = {
                "eschew": ["Sentence 1.", "Sentence 2.", "Sentence 3."],
                "banal": ["Sentence A.", "Sentence B.", "Sentence C."],
            }
            with open(sentences_path, "w") as f:
                json.dump(sentences, f)

            words = bs.csv_to_json(csv_path, output_path, sentences_path)

            assert "sentences" in words[0]
            assert len(words[0]["sentences"]) == 3

    def test_builds_without_sentences_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path, sentences_path, output_path = self._setup(tmp_dir)
            # Don't create sentences.json

            words = bs.csv_to_json(csv_path, output_path, sentences_path)

            assert "sentences" not in words[0]
            assert words[0]["word"] == "eschew"

    def test_partial_sentences(self):
        """Words without sentences should not have the key."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path, sentences_path, output_path = self._setup(tmp_dir)

            sentences = {"eschew": ["Only eschew has sentences."]}
            with open(sentences_path, "w") as f:
                json.dump(sentences, f)

            words = bs.csv_to_json(csv_path, output_path, sentences_path)

            eschew = next(w for w in words if w["word"] == "eschew")
            banal = next(w for w in words if w["word"] == "banal")

            assert "sentences" in eschew
            assert "sentences" not in banal
