"""
generate_alt_meanings.py — Identify words with SAT-relevant secondary meanings.

Sends the full word list to Gemini and asks it to flag words that have
notable alternate meanings the SAT might test. Stores results in
alt_meanings.json, which gets merged into words.json during build.

Usage:
  python scripts/generate_alt_meanings.py
"""

import csv
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "sat_vocabulary.csv"
ALT_MEANINGS_PATH = PROJECT_ROOT / "alt_meanings.json"
GEMINI_BATCH_SIZE = 30
GEMINI_DELAY = 4

load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------

GEMINI_PROMPT = """\
You are an expert SAT vocabulary tutor.

For each word below, determine if it has a SECONDARY or ALTERNATE meaning that
the SAT might test — specifically meanings that students commonly overlook.

Examples of what to flag:
- "check" — commonly known as a bank check, but SAT tests "to restrain or hold back"
- "qualify" — commonly known as "to meet requirements", but SAT tests "to limit or modify a statement"
- "sanction" — can mean both "to approve" AND "to penalize" (opposite meanings!)
- "table" — commonly a piece of furniture, but SAT tests "to postpone discussion of"

Only flag words that genuinely have a notable secondary meaning the SAT might
test. Do NOT flag words where the common meaning IS the SAT-tested meaning.

For each flagged word, provide:
- "word": the word
- "alt_definition": a concise secondary definition (1 sentence, SAT-relevant)
- "note": a brief note explaining why this is tricky (1 sentence)

Return a JSON array of objects. Only include words that have a notable
secondary meaning. If none of the words qualify, return an empty array [].

Words (with their primary definitions):
{word_list}
"""


def _clean_json_string(raw: str) -> str:
    """Strip markdown code blocks if the AI wraps its response."""
    return re.sub(r"```json\s*|```", "", raw).strip()


def _api_call_with_retry(client, model_id: str, contents: str, config, max_retries: int = 3):
    """Gemini API call with exponential backoff for transient errors."""
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model_id,
                contents=contents,
                config=config,
            )
        except Exception as e:
            err = str(e).lower()
            if "429" in str(e) or "resource_exhausted" in err or "rate" in err:
                wait = (2 ** attempt) * 10
                print(f"  ⏳ Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif any(code in str(e) for code in ("500", "502", "503")):
                wait = (2 ** attempt) * 5
                print(f"  ⏳ Server error, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {max_retries} retries")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def load_words_with_definitions(csv_path: Path = CSV_PATH) -> list[dict]:
    """Load words and their definitions from the CSV."""
    with open(csv_path, "r", newline="") as f:
        return [
            {"word": row["word"].strip(), "definition": row.get("definition", "").strip()}
            for row in csv.DictReader(f)
            if row["word"].strip()
        ]


def generate_alt_meanings(
    words: list[dict],
    alt_meanings_path: Path = ALT_MEANINGS_PATH,
) -> dict[str, dict]:
    """
    Identify words with SAT-relevant secondary meanings via Gemini.

    Returns a dict mapping word → {"alt_definition": ..., "note": ...}.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set in .env")
        sys.exit(1)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.0-flash"

    all_alt_meanings: dict[str, dict] = {}

    print(f"📊 Scanning {len(words)} words for secondary meanings...\n")

    for i in range(0, len(words), GEMINI_BATCH_SIZE):
        batch = words[i : i + GEMINI_BATCH_SIZE]
        batch_num = i // GEMINI_BATCH_SIZE + 1
        total_batches = (len(words) + GEMINI_BATCH_SIZE - 1) // GEMINI_BATCH_SIZE

        word_list_str = "\n".join(
            f"- {w['word']}: {w['definition']}" for w in batch
        )
        prompt = GEMINI_PROMPT.format(word_list=word_list_str)

        print(f"🔍 Batch {batch_num}/{total_batches}: {len(batch)} words...")

        try:
            resp = _api_call_with_retry(
                client,
                model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )

            if resp.text:
                raw = _clean_json_string(resp.text)
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    for item in parsed:
                        w = item.get("word", "").strip().lower()
                        alt_def = item.get("alt_definition", "").strip()
                        note = item.get("note", "").strip()
                        if w and alt_def:
                            all_alt_meanings[w] = {
                                "alt_definition": alt_def,
                                "note": note,
                            }
                            print(f"  ⚠️  {w}: {alt_def}")
                            print(f"      ({note})")

        except Exception as e:
            print(f"  ❌ Batch failed: {e}")

        if i + GEMINI_BATCH_SIZE < len(words):
            time.sleep(GEMINI_DELAY)

    # Save results
    with open(alt_meanings_path, "w") as f:
        json.dump(all_alt_meanings, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"✅ Found {len(all_alt_meanings)} words with notable secondary meanings")
    print(f"💾 Saved to: {alt_meanings_path}")

    return all_alt_meanings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    words = load_words_with_definitions()
    generate_alt_meanings(words)
