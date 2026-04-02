"""
build_site.py — Convert sat_vocabulary.csv to docs/words.json for the static site.

Merges example sentences from sentences.json if available.

Usage:
  python scripts/build_site.py
"""

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "sat_vocabulary.csv"
SENTENCES_PATH = PROJECT_ROOT / "sentences.json"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "words.json"


def _load_sentences(sentences_path: Path = SENTENCES_PATH) -> dict[str, list[str]]:
    """Load pre-generated sentences from sentences.json if it exists."""
    if sentences_path.exists():
        with open(sentences_path, "r") as f:
            data = json.load(f)
        print(f"📖 Loaded sentences for {len(data)} words")
        return data
    return {}


def csv_to_json(
    csv_path: Path = CSV_PATH,
    output_path: Path = OUTPUT_PATH,
    sentences_path: Path = SENTENCES_PATH,
) -> list[dict]:
    """
    Read sat_vocabulary.csv and write a JSON file for the flashcard site.

    Each word object has: word, definition, score, and optionally sentences.
    Returns the list of word objects.
    """
    sentences = _load_sentences(sentences_path)

    words = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word_key = row["word"].strip().lower()
            entry = {
                "word": row["word"].strip(),
                "definition": row.get("definition", "").strip(),
                "score": int(row.get("score", 1)),
            }
            # Merge sentences if available
            if word_key in sentences:
                entry["sentences"] = sentences[word_key]
            words.append(entry)

    # Sort by score descending (high-frequency first), then alphabetically
    words.sort(key=lambda w: (-w["score"], w["word"]))

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)

    with_sentences = sum(1 for w in words if "sentences" in w)
    print(f"✅ Generated {output_path} with {len(words)} words ({with_sentences} with example sentences)")
    return words


if __name__ == "__main__":
    csv_to_json()
