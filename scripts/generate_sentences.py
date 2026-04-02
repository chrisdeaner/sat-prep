"""
generate_sentences.py — Generate SAT-style example sentences for vocabulary words.

Creates 3 example sentences per word using Gemini, stored in sentences.json.
These are merged into words.json during the build step. Re-run anytime to
refresh the sentences.

Usage:
  python scripts/generate_sentences.py
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
SENTENCES_PATH = PROJECT_ROOT / "sentences.json"
GEMINI_BATCH_SIZE = 15  # fewer per batch since we're asking for 3 sentences each
GEMINI_DELAY = 4  # seconds between Gemini calls (rate limit)

load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Gemini helpers (shared patterns)
# ---------------------------------------------------------------------------

GEMINI_PROMPT = """\
You are a vocabulary tutor preparing students for the SAT.

For each word below, write exactly 3 example sentences that:
- Use the word in a way a high school student would encounter in SAT reading passages
- Vary in subject matter (e.g., science, history, literature, social commentary)
- Show the word in its SAT-relevant meaning
- Are 1-2 sentences long each

Return a JSON object where each key is the word (lowercase) and the value is
an array of exactly 3 sentences.

Words:
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

def load_words(csv_path: Path = CSV_PATH) -> list[str]:
    """Load all word strings from the CSV."""
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        return [row["word"].strip() for row in reader if row["word"].strip()]


def generate_sentences(words: list[str], sentences_path: Path = SENTENCES_PATH) -> dict[str, list[str]]:
    """
    Generate 3 example sentences per word using Gemini.

    Saves results to sentences.json and returns the full dict.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set in .env")
        sys.exit(1)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.0-flash"

    all_sentences: dict[str, list[str]] = {}

    print(f"📊 Generating example sentences for {len(words)} words...\n")

    for i in range(0, len(words), GEMINI_BATCH_SIZE):
        batch = words[i : i + GEMINI_BATCH_SIZE]
        batch_num = i // GEMINI_BATCH_SIZE + 1
        total_batches = (len(words) + GEMINI_BATCH_SIZE - 1) // GEMINI_BATCH_SIZE

        word_list_str = "\n".join(f"- {w}" for w in batch)
        prompt = GEMINI_PROMPT.format(word_list=word_list_str)

        print(f"🤖 Batch {batch_num}/{total_batches}: {len(batch)} words...")

        try:
            resp = _api_call_with_retry(
                client,
                model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.8,  # some variety in sentence generation
                ),
            )

            if resp.text:
                raw = _clean_json_string(resp.text)
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    for word, sentences in parsed.items():
                        w = word.strip().lower()
                        if isinstance(sentences, list) and len(sentences) >= 1:
                            all_sentences[w] = sentences[:3]
                            print(f"  ✅ {w}: {len(sentences)} sentences")

        except Exception as e:
            print(f"  ❌ Batch failed: {e}")

        if i + GEMINI_BATCH_SIZE < len(words):
            time.sleep(GEMINI_DELAY)

    # Save to sentences.json
    with open(sentences_path, "w") as f:
        json.dump(all_sentences, f, indent=2, ensure_ascii=False)

    missing = [w for w in words if w.lower() not in all_sentences]
    print(f"\n{'='*60}")
    print(f"✅ Generated sentences for {len(all_sentences)}/{len(words)} words")
    print(f"💾 Saved to: {sentences_path}")

    if missing:
        print(f"⚠️  Missing: {', '.join(missing[:10])}{'...' if len(missing) > 10 else ''}")

    return all_sentences


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    words = load_words()
    generate_sentences(words)
