"""
data.py — Load and index SAT vocabulary data on startup.

Reads sat_vocabulary.csv, sentences.json, and alt_meanings.json once,
builds an in-memory index keyed by lowercase word for fast lookups.
"""

import csv
import json
import os
from pathlib import Path


# Project root is one level up from mcp_server/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

CSV_PATH = PROJECT_ROOT / "sat_vocabulary.csv"
SENTENCES_PATH = PROJECT_ROOT / "sentences.json"
ALT_MEANINGS_PATH = PROJECT_ROOT / "alt_meanings.json"


def _score_to_tier(score: int) -> str:
    """Map a numeric frequency score to a human-readable tier."""
    if score >= 4:
        return "high"
    elif score >= 2:
        return "medium"
    else:
        return "low"


def load_vocab_data() -> dict:
    """
    Load all vocabulary data files and return a unified index.

    Returns
    -------
    dict keyed by lowercase word, each value is:
        {
            "word": str (original casing),
            "definition": str,
            "score": int,
            "frequency_tier": "high" | "medium" | "low",
            "sentences": list[str],
            "alt_meaning": { "alt_definition": str, "note": str } | None,
        }
    """
    index: dict = {}

    # --- Load CSV ---
    if CSV_PATH.exists():
        with open(CSV_PATH, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                word = row.get("word", "").strip()
                if not word:
                    continue
                score = int(row.get("score", 1))
                index[word.lower()] = {
                    "word": word,
                    "definition": row.get("definition", "").strip(),
                    "score": score,
                    "frequency_tier": _score_to_tier(score),
                    "sentences": [],
                    "alt_meaning": None,
                }

    # --- Merge sentences ---
    if SENTENCES_PATH.exists():
        with open(SENTENCES_PATH, "r") as f:
            sentences = json.load(f)
        for word_key, sentence_list in sentences.items():
            key = word_key.strip().lower()
            if key in index:
                index[key]["sentences"] = sentence_list

    # --- Merge alt meanings ---
    if ALT_MEANINGS_PATH.exists():
        with open(ALT_MEANINGS_PATH, "r") as f:
            alt_meanings = json.load(f)
        for word_key, alt_data in alt_meanings.items():
            key = word_key.strip().lower()
            if key in index:
                index[key]["alt_meaning"] = {
                    "alt_definition": alt_data.get("alt_definition", ""),
                    "note": alt_data.get("note", ""),
                }

    return index
