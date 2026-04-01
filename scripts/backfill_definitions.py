"""
backfill_definitions.py — Fill missing definitions in sat_vocabulary.csv.

Strategy:
  1. Try the Free Dictionary API (no key required)
  2. Fall back to Gemini for words the dictionary doesn't cover

Usage:
  python scripts/backfill_definitions.py [--dry-run]
"""

import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "sat_vocabulary.csv"
DICT_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
DICT_API_DELAY = 0.5  # seconds between free API calls
GEMINI_BATCH_SIZE = 25  # words per Gemini request
GEMINI_DELAY = 4  # seconds between Gemini calls (rate limit)

load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Free Dictionary API
# ---------------------------------------------------------------------------

def fetch_definition_free_api(word: str) -> str | None:
    """
    Fetch a concise definition from the Free Dictionary API.

    Returns the first definition found, or None if the word isn't in the
    database or the request fails.
    """
    url = DICT_API_URL.format(word=word.strip().lower())
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None

        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            return None

        # Walk through meanings and grab the first definition
        for entry in data:
            for meaning in entry.get("meanings", []):
                definitions = meaning.get("definitions", [])
                if definitions:
                    defn = definitions[0].get("definition", "").strip()
                    if defn:
                        return defn
        return None

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Gemini fallback
# ---------------------------------------------------------------------------

GEMINI_PROMPT = (
    "You are a vocabulary tutor preparing students for the SAT.\n"
    "For each word below, provide a concise, clear definition (1 sentence max) "
    "that a high school student would understand.\n\n"
    "Return a JSON array of objects, each with 'word' and 'definition' keys.\n"
    "Maintain the same order as the input list.\n\n"
    "Words:\n{word_list}"
)


def _clean_json_string(raw: str) -> str:
    """Strip markdown code blocks if the AI wraps its response."""
    return re.sub(r"```json\s*|```", "", raw).strip()


def _api_call_with_retry(client, model_id: str, contents: str, config, max_retries: int = 3):
    """
    Make a Gemini API call with exponential backoff for transient errors.

    Retries on 429 (rate limit) and 5xx (server error).
    Raises immediately on 4xx client errors.
    """
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


def fetch_definitions_gemini(words: list[str]) -> dict[str, str]:
    """
    Batch-fetch definitions from Gemini for a list of words.

    Returns a dict mapping word → definition.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("  ⚠️  GEMINI_API_KEY not set in .env — skipping Gemini fallback")
        return {}

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.0-flash"
    results: dict[str, str] = {}

    for i in range(0, len(words), GEMINI_BATCH_SIZE):
        batch = words[i : i + GEMINI_BATCH_SIZE]
        word_list_str = "\n".join(f"- {w}" for w in batch)
        prompt = GEMINI_PROMPT.format(word_list=word_list_str)

        print(f"  🤖 Gemini batch {i // GEMINI_BATCH_SIZE + 1}: {len(batch)} words...")

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
                        d = item.get("definition", "").strip()
                        if w and d:
                            results[w] = d

        except Exception as e:
            print(f"  ❌ Gemini batch failed: {e}")

        if i + GEMINI_BATCH_SIZE < len(words):
            time.sleep(GEMINI_DELAY)

    return results


# ---------------------------------------------------------------------------
# Main backfill logic
# ---------------------------------------------------------------------------

def backfill(dry_run: bool = False) -> dict:
    """
    Read the CSV, fill missing definitions, and write back.

    Returns stats dict with counts of what happened.
    """
    # Read CSV
    rows: list[dict] = []
    with open(CSV_PATH, "r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Identify words missing definitions
    missing = [(i, row["word"]) for i, row in enumerate(rows) if not row.get("definition", "").strip()]
    print(f"📊 Total words: {len(rows)}, Missing definitions: {len(missing)}")

    if not missing:
        print("✅ All definitions already filled!")
        return {"total": len(rows), "missing": 0, "filled_api": 0, "filled_gemini": 0, "still_missing": 0}

    # Phase 1: Free Dictionary API
    filled_api = 0
    gemini_queue: list[tuple[int, str]] = []

    print(f"\n🔍 Phase 1: Free Dictionary API ({len(missing)} words)...")
    for idx, word in missing:
        if dry_run:
            gemini_queue.append((idx, word))
            continue

        defn = fetch_definition_free_api(word)
        if defn:
            rows[idx]["definition"] = defn
            filled_api += 1
            print(f"  ✅ {word}: {defn[:60]}...")
        else:
            gemini_queue.append((idx, word))
            print(f"  ❌ {word}: not found")

        time.sleep(DICT_API_DELAY)

    print(f"\n📈 Free API: {filled_api} filled, {len(gemini_queue)} remaining")

    # Phase 2: Gemini fallback
    filled_gemini = 0
    if gemini_queue and not dry_run:
        print(f"\n🤖 Phase 2: Gemini fallback ({len(gemini_queue)} words)...")
        words_for_gemini = [w for _, w in gemini_queue]
        gemini_defs = fetch_definitions_gemini(words_for_gemini)

        for idx, word in gemini_queue:
            defn = gemini_defs.get(word.lower(), "")
            if defn:
                rows[idx]["definition"] = defn
                filled_gemini += 1
                print(f"  ✅ {word}: {defn[:60]}...")

    # Write updated CSV
    if not dry_run and (filled_api > 0 or filled_gemini > 0):
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n💾 Saved updated CSV to {CSV_PATH}")

    still_missing = len(missing) - filled_api - filled_gemini
    stats = {
        "total": len(rows),
        "missing": len(missing),
        "filled_api": filled_api,
        "filled_gemini": filled_gemini,
        "still_missing": still_missing,
    }

    print(f"\n🏁 Done! API: {filled_api}, Gemini: {filled_gemini}, Still missing: {still_missing}")
    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("🔍 DRY RUN — no changes will be made\n")
    backfill(dry_run=dry_run)
