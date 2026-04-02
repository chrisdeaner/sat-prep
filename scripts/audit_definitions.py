"""
audit_definitions.py — Review all definitions for SAT accuracy using Gemini.

Sends words + definitions in batches to Gemini, which flags any that are:
  - Archaic or obsolete meanings
  - Wrong part of speech for SAT context
  - Too narrow, technical, or niche
  - Simply incorrect or misleading

Workflow:
  1. Run:   python scripts/audit_definitions.py
     → Reviews all definitions, saves flagged corrections to corrections.json
  2. Edit:  Review corrections.json, delete any you disagree with
  3. Apply: python scripts/audit_definitions.py --apply
     → Applies corrections.json to sat_vocabulary.csv

Options:
  --force    Re-audit words even if corrections.json already exists
  --apply    Apply corrections.json to the CSV (skips audit)
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
CORRECTIONS_PATH = PROJECT_ROOT / "corrections.json"
BATCH_SIZE = 30  # words per Gemini call
GEMINI_DELAY = 4  # seconds between calls

load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Gemini audit prompt
# ---------------------------------------------------------------------------

AUDIT_PROMPT = """\
You are an expert SAT vocabulary tutor reviewing definitions for accuracy.

For each word and its current definition below, evaluate whether the definition
is appropriate for SAT prep. Flag definitions that are:
- Archaic, obsolete, or rarely-used meanings
- Wrong part of speech for typical SAT usage (e.g., noun form when SAT tests the adjective)
- Too narrow, technical, or niche
- Simply incorrect or misleading
- Poorly worded or confusing for a high school student

Return a JSON array of objects. Include ONLY words that need correction.
Each object must have:
- "word": the word
- "issue": brief explanation of what's wrong (1 sentence)
- "suggested_definition": your improved definition (concise, 1 sentence, SAT-appropriate)

If ALL definitions in the batch are fine, return an empty array: []

Words to review:
{word_list}
"""


# ---------------------------------------------------------------------------
# Helpers (shared patterns from backfill_definitions.py)
# ---------------------------------------------------------------------------

def _clean_json_string(raw: str) -> str:
    """Strip markdown code blocks if the AI wraps its response."""
    return re.sub(r"```json\s*|```", "", raw).strip()


def _api_call_with_retry(client, model_id, contents, config, max_retries=3):
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
# Core audit logic
# ---------------------------------------------------------------------------

def load_words(csv_path: Path = CSV_PATH) -> list[dict]:
    """Load all words from the CSV."""
    with open(csv_path, "r", newline="") as f:
        return list(csv.DictReader(f))


def audit_batch(client, model_id: str, words: list[dict]) -> list[dict]:
    """
    Send a batch of words to Gemini for review.

    Returns a list of correction dicts (only flagged words).
    """
    from google.genai import types

    word_list = "\n".join(
        f"- {w['word']}: {w['definition']}" for w in words
    )
    prompt = AUDIT_PROMPT.format(word_list=word_list)

    try:
        resp = _api_call_with_retry(
            client, model_id,
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
                return parsed
        return []

    except Exception as e:
        print(f"  ❌ Batch audit failed: {e}")
        return []


def run_audit(csv_path: Path = CSV_PATH, corrections_path: Path = CORRECTIONS_PATH) -> list[dict]:
    """
    Audit all definitions and save flagged corrections to a JSON file.

    Returns the list of all corrections.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set in .env")
        sys.exit(1)

    from google import genai
    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.0-flash"

    words = load_words(csv_path)
    print(f"📊 Auditing {len(words)} definitions...\n")

    all_corrections = []

    for i in range(0, len(words), BATCH_SIZE):
        batch = words[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(words) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"🔍 Batch {batch_num}/{total_batches} ({len(batch)} words)...")

        corrections = audit_batch(client, model_id, batch)

        for c in corrections:
            print(f"  ⚠️  {c.get('word', '?')}: {c.get('issue', 'no reason')}")
            print(f"      Current:   {next((w['definition'] for w in batch if w['word'].lower() == c.get('word', '').lower()), '?')}")
            print(f"      Suggested: {c.get('suggested_definition', '?')}")

        if not corrections:
            print(f"  ✅ All definitions look good")

        all_corrections.extend(corrections)

        if i + BATCH_SIZE < len(words):
            time.sleep(GEMINI_DELAY)

    # Save corrections file
    with open(corrections_path, "w") as f:
        json.dump(all_corrections, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"📋 Audit complete: {len(all_corrections)} definitions flagged")
    print(f"💾 Saved to: {corrections_path}")

    if all_corrections:
        print(f"\nNext steps:")
        print(f"  1. Review {corrections_path}")
        print(f"  2. Delete any corrections you disagree with")
        print(f"  3. Run: python scripts/audit_definitions.py --apply")

    return all_corrections


# ---------------------------------------------------------------------------
# Apply corrections
# ---------------------------------------------------------------------------

def apply_corrections(csv_path: Path = CSV_PATH, corrections_path: Path = CORRECTIONS_PATH):
    """
    Apply corrections from corrections.json to the CSV.
    """
    if not corrections_path.exists():
        print(f"❌ No corrections file found at {corrections_path}")
        print(f"   Run the audit first: python scripts/audit_definitions.py")
        sys.exit(1)

    with open(corrections_path, "r") as f:
        corrections = json.load(f)

    if not corrections:
        print("✅ No corrections to apply!")
        return

    # Build lookup: word (lowercase) → new definition
    correction_map = {}
    for c in corrections:
        word = c.get("word", "").strip().lower()
        defn = c.get("suggested_definition", "").strip()
        if word and defn:
            correction_map[word] = defn

    # Read and update CSV
    rows = load_words(csv_path)
    fieldnames = list(rows[0].keys()) if rows else ["word", "definition", "score"]

    applied = 0
    for row in rows:
        word_lower = row["word"].strip().lower()
        if word_lower in correction_map:
            old_def = row["definition"]
            row["definition"] = correction_map[word_lower]
            applied += 1
            print(f"  ✏️  {row['word']}")
            print(f"      Was: {old_def}")
            print(f"      Now: {row['definition']}")

    # Write updated CSV
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Clean up corrections file
    corrections_path.unlink()

    print(f"\n✅ Applied {applied} corrections to {csv_path}")
    print(f"🗑️  Deleted {corrections_path}")
    print(f"\nDon't forget to rebuild the site:")
    print(f"  python scripts/build_site.py")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply_corrections()
    else:
        force = "--force" in sys.argv
        if CORRECTIONS_PATH.exists() and not force:
            print(f"⚠️  {CORRECTIONS_PATH} already exists.")
            print(f"   Review it and run: python scripts/audit_definitions.py --apply")
            print(f"   Or re-audit with:  python scripts/audit_definitions.py --force")
            sys.exit(0)
        run_audit()
