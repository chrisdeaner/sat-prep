"""
build_site.py — Convert sat_vocabulary.csv to docs/words.json for the static site.

Usage:
  python scripts/build_site.py
"""

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "sat_vocabulary.csv"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "words.json"


def csv_to_json(csv_path: Path = CSV_PATH, output_path: Path = OUTPUT_PATH) -> list[dict]:
    """
    Read sat_vocabulary.csv and write a JSON file for the flashcard site.

    Each word object has: word, definition, score.
    Returns the list of word objects.
    """
    words = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            words.append({
                "word": row["word"].strip(),
                "definition": row.get("definition", "").strip(),
                "score": int(row.get("score", 1)),
            })

    # Sort by score descending (high-frequency first), then alphabetically
    words.sort(key=lambda w: (-w["score"], w["word"]))

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {output_path} with {len(words)} words")
    return words


if __name__ == "__main__":
    csv_to_json()
