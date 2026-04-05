"""
generate_sentences.py — Generate SAT-style example sentences for vocabulary words.

Ensures each word has 5 example sentences in sentences.json. Keeps existing
sentences and only generates new ones to fill the gap. Deduplicates so no
sentence appears twice for the same word.

Usage:
  python scripts/generate_sentences.py           # backfill to 5 per word
  python scripts/generate_sentences.py --force    # regenerate all from scratch
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

TARGET_SENTENCES = 5  # desired number of sentences per word
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "sat_vocabulary.csv"
SENTENCES_PATH = PROJECT_ROOT / "sentences.json"
GEMINI_BATCH_SIZE = 10  # words per batch
GEMINI_DELAY = 4  # seconds between Gemini calls (rate limit)

load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Gemini helpers (shared patterns)
# ---------------------------------------------------------------------------

GEMINI_PROMPT = """\
You are a vocabulary tutor preparing students for the SAT.

For each word below, write exactly {count} NEW example sentences that:
- Use the word in a way a high school student would encounter in SAT reading passages
- Vary in subject matter (e.g., science, history, literature, social commentary)
- Show the word in its SAT-relevant meaning
- Are 1-2 sentences long each
- Do NOT repeat or closely paraphrase any of the existing sentences listed below

{existing_context}

Return a JSON object where each key is the word (lowercase) and the value is
an array of exactly {count} NEW sentences.

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


def load_existing_sentences(sentences_path: Path = SENTENCES_PATH) -> dict[str, list[str]]:
    """Load existing sentences.json, or return empty dict if it doesn't exist."""
    if sentences_path.exists():
        with open(sentences_path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    return {}


def _deduplicate(sentences: list[str]) -> list[str]:
    """Remove duplicate sentences (case-insensitive comparison)."""
    seen: set[str] = set()
    unique: list[str] = []
    for s in sentences:
        normalized = s.strip().lower()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(s)
    return unique


def generate_sentences(
    words: list[str],
    sentences_path: Path = SENTENCES_PATH,
    force: bool = False,
) -> dict[str, list[str]]:
    """
    Ensure each word has TARGET_SENTENCES example sentences.

    - If force=False (default): keeps existing sentences, only generates
      new ones for words that have fewer than TARGET_SENTENCES.
    - If force=True: regenerates all sentences from scratch.

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

    # Load existing data
    if force:
        all_sentences: dict[str, list[str]] = {}
        print("🔄 Force mode — regenerating all sentences from scratch.\n")
    else:
        all_sentences = load_existing_sentences(sentences_path)
        print(f"📂 Loaded {len(all_sentences)} words from existing sentences.json\n")

    # Figure out which words need more sentences
    words_needing_sentences: list[dict] = []
    for w in words:
        key = w.lower()
        existing = all_sentences.get(key, [])
        needed = TARGET_SENTENCES - len(existing)
        if needed > 0:
            words_needing_sentences.append({
                "word": w,
                "key": key,
                "existing": existing,
                "needed": needed,
            })

    if not words_needing_sentences:
        print(f"✅ All {len(words)} words already have {TARGET_SENTENCES} sentences. Nothing to do.")
        return all_sentences

    print(f"📊 {len(words_needing_sentences)} words need more sentences:\n"
          f"   {sum(w['needed'] for w in words_needing_sentences)} total sentences to generate\n")

    # Process in batches
    for i in range(0, len(words_needing_sentences), GEMINI_BATCH_SIZE):
        batch = words_needing_sentences[i : i + GEMINI_BATCH_SIZE]
        batch_num = i // GEMINI_BATCH_SIZE + 1
        total_batches = (len(words_needing_sentences) + GEMINI_BATCH_SIZE - 1) // GEMINI_BATCH_SIZE

        # Build the word list and existing context for the prompt
        word_list_str = "\n".join(f"- {item['word']} (need {item['needed']} new)" for item in batch)

        # Include existing sentences so Gemini knows what to avoid
        existing_lines = []
        for item in batch:
            if item["existing"]:
                existing_lines.append(f"\nExisting sentences for \"{item['word']}\" (DO NOT repeat these):")
                for s in item["existing"]:
                    existing_lines.append(f"  - {s}")
        existing_context = "\n".join(existing_lines) if existing_lines else "No existing sentences."

        # All words in this batch need the same count? Not necessarily.
        # Use per-word counts in the prompt.
        prompt = GEMINI_PROMPT.format(
            count="the specified number of",
            word_list=word_list_str,
            existing_context=existing_context,
        )

        print(f"🤖 Batch {batch_num}/{total_batches}: {len(batch)} words...")

        try:
            resp = _api_call_with_retry(
                client,
                model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.8,
                ),
            )

            if resp.text:
                raw = _clean_json_string(resp.text)
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    for item in batch:
                        new_sentences = parsed.get(item["key"], parsed.get(item["word"], []))
                        if isinstance(new_sentences, list) and len(new_sentences) >= 1:
                            # Merge existing + new, then deduplicate
                            combined = item["existing"] + new_sentences
                            combined = _deduplicate(combined)
                            all_sentences[item["key"]] = combined[:TARGET_SENTENCES]
                            print(f"  ✅ {item['key']}: {len(item['existing'])} existing + "
                                  f"{len(new_sentences)} new → {len(all_sentences[item['key']])} total")
                        else:
                            # Keep whatever we had
                            if item["existing"]:
                                all_sentences[item["key"]] = item["existing"]
                            print(f"  ⚠️  {item['key']}: no new sentences returned")

        except Exception as e:
            print(f"  ❌ Batch failed: {e}")
            # Preserve existing sentences for words in the failed batch
            for item in batch:
                if item["existing"] and item["key"] not in all_sentences:
                    all_sentences[item["key"]] = item["existing"]

        if i + GEMINI_BATCH_SIZE < len(words_needing_sentences):
            time.sleep(GEMINI_DELAY)

    # Save to sentences.json
    with open(sentences_path, "w") as f:
        json.dump(all_sentences, f, indent=2, ensure_ascii=False)

    # Report
    complete = sum(1 for w in words if len(all_sentences.get(w.lower(), [])) >= TARGET_SENTENCES)
    missing = [w for w in words if len(all_sentences.get(w.lower(), [])) < TARGET_SENTENCES]

    print(f"\n{'='*60}")
    print(f"✅ {complete}/{len(words)} words have {TARGET_SENTENCES}+ sentences")
    print(f"💾 Saved to: {sentences_path}")

    if missing:
        print(f"⚠️  Still incomplete: {', '.join(missing[:10])}{'...' if len(missing) > 10 else ''}")
        print(f"   Re-run this script to retry failed words.")

    return all_sentences


# ---------------------------------------------------------------------------
# Grow mode — add 1 sentence to N random words
# ---------------------------------------------------------------------------

def grow_sentences(
    words: list[str],
    count: int = 30,
    sentences_path: Path = SENTENCES_PATH,
) -> dict[str, list[str]]:
    """
    Add 1 new sentence to a random subset of words.

    Args:
        count: Number of words to grow. 0 means all words.
    """
    import random

    all_sentences = load_existing_sentences(sentences_path)
    print(f"📂 Loaded {len(all_sentences)} words from existing sentences.json\n")

    # Pick words to grow — all of them, or a random subset
    candidates = [w for w in words if w.lower() in all_sentences]
    if not candidates:
        print("❌ No existing sentences to grow. Run without --grow first.")
        return all_sentences

    if count == 0 or count >= len(candidates):
        selected = candidates
    else:
        selected = random.sample(candidates, count)

    print(f"🌱 Growing: adding 1 sentence to {len(selected)} words\n")

    # Temporarily bump each selected word's need to +1
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set in .env")
        sys.exit(1)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.0-flash"

    grow_items = []
    for w in selected:
        key = w.lower()
        existing = all_sentences.get(key, [])
        grow_items.append({"word": w, "key": key, "existing": existing, "needed": 1})

    for i in range(0, len(grow_items), GEMINI_BATCH_SIZE):
        batch = grow_items[i : i + GEMINI_BATCH_SIZE]
        batch_num = i // GEMINI_BATCH_SIZE + 1
        total_batches = (len(grow_items) + GEMINI_BATCH_SIZE - 1) // GEMINI_BATCH_SIZE

        word_list_str = "\n".join(f"- {item['word']} (need 1 new)" for item in batch)

        existing_lines = []
        for item in batch:
            if item["existing"]:
                existing_lines.append(f'\nExisting sentences for "{item["word"]}" (DO NOT repeat these):')
                for s in item["existing"]:
                    existing_lines.append(f"  - {s}")
        existing_context = "\n".join(existing_lines) if existing_lines else "No existing sentences."

        prompt = GEMINI_PROMPT.format(
            count="exactly 1",
            word_list=word_list_str,
            existing_context=existing_context,
        )

        print(f"🤖 Batch {batch_num}/{total_batches}: {len(batch)} words...")

        try:
            resp = _api_call_with_retry(
                client,
                model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.9,  # slightly higher for variety
                ),
            )

            if resp.text:
                raw = _clean_json_string(resp.text)
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    for item in batch:
                        new_sentences = parsed.get(item["key"], parsed.get(item["word"], []))
                        if isinstance(new_sentences, list) and len(new_sentences) >= 1:
                            combined = item["existing"] + new_sentences
                            combined = _deduplicate(combined)
                            all_sentences[item["key"]] = combined
                            print(f"  ✅ {item['key']}: {len(item['existing'])} → {len(combined)}")
                        else:
                            print(f"  ⚠️  {item['key']}: no new sentence returned")

        except Exception as e:
            print(f"  ❌ Batch failed: {e}")

        if i + GEMINI_BATCH_SIZE < len(grow_items):
            time.sleep(GEMINI_DELAY)

    # Save
    with open(sentences_path, "w") as f:
        json.dump(all_sentences, f, indent=2, ensure_ascii=False)

    total_sentences = sum(len(s) for s in all_sentences.values())
    print(f"\n{'='*60}")
    print(f"🌱 Grew sentence pool — now {total_sentences} total sentences across {len(all_sentences)} words")
    print(f"💾 Saved to: {sentences_path}")

    return all_sentences


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate SAT vocabulary example sentences.")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate all sentences from scratch")
    parser.add_argument("--grow", type=int, nargs="?", const=30, default=None,
                        help="Add 1 new sentence to N random words (default: 30, 0 = all)")
    args = parser.parse_args()

    words = load_words()

    if args.grow is not None:
        grow_sentences(words, count=args.grow)
    else:
        generate_sentences(words, force=args.force)
