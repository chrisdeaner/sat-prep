# MCP Server — SAT Vocab Lookup

## Purpose

An MCP server that exposes the SAT vocabulary dataset as tools any LLM client can call. Instead of a student needing to open the flashcard site, any AI conversation becomes an SAT study session — with authoritative, curated data instead of generated-on-the-fly answers.

**Zero external dependencies** — no API keys needed. The server reads the existing local data files on startup.

---

## Data Sources

| File | Contents |
|------|----------|
| `sat_vocabulary.csv` | 275 words with definitions and frequency scores (1–6) |
| `sentences.json` | 3 SAT-style example sentences per word |
| `alt_meanings.json` | ~25 words with tricky secondary meanings + notes |

---

## Tools

### `lookup_word`

Look up a single vocabulary word and get all available data.

```
Inputs:  { word: string }
Outputs: {
  word: string,
  definition: string,
  score: number,
  frequency_tier: "high" | "medium" | "low",
  sentences: string[],
  alt_meaning?: { alt_definition: string, note: string }
}
```

**Frequency tier mapping:**
- High: score ≥ 4 (appeared on 3+ SATs)
- Medium: score 2–3
- Low: score 1

**Example call:** `lookup_word({ word: "eschew" })`
```json
{
  "word": "eschew",
  "definition": "To deliberately avoid or keep away from",
  "score": 6,
  "frequency_tier": "high",
  "sentences": [
    "Many health-conscious individuals eschew processed foods...",
    "The politician decided to eschew controversial topics...",
    "Although he appreciated modern technology, the author tried to eschew its influence..."
  ]
}
```

---

### `list_words`

Browse the vocabulary list, optionally filtered by frequency tier.

```
Inputs:  { tier?: "high" | "medium" | "low", limit?: number }
Outputs: { total: number, words: [{ word, definition, score, frequency_tier }] }
```

Default: returns all words sorted by score (highest first). Use `limit` to cap results.

---

### `quiz_me`

Generate a multiple-choice vocabulary quiz from the dataset.

```
Inputs:  { count?: number, tier?: "high" | "medium" | "low" }
Outputs: {
  questions: [{
    word: string,
    sentence_hint: string,
    options: string[],
    correct_index: number
  }]
}
```

- Default `count`: 5
- Each question uses a real example sentence with the target word blanked out
- 4 answer options drawn from the same tier to keep difficulty consistent
- Shuffled option order so correct answer isn't always in the same position

> [!TIP]
> This is the highest-value tool — it turns static data into an interactive experience that works in *any* LLM chat, not just on the flashcard site.

---

## Architecture

```
sat-prep/
├── mcp_server/
│   ├── __init__.py
│   ├── server.py          # MCP server entry point
│   ├── tools.py           # Tool implementations (lookup, list, quiz)
│   └── data.py            # Load & index CSV/JSON data on startup
├── sat_vocabulary.csv     # (existing)
├── sentences.json         # (existing)
└── alt_meanings.json      # (existing)
```

- **`data.py`** — Reads all three data files at startup, builds an in-memory index keyed by word (lowercased). Single load, no file I/O per request.
- **`tools.py`** — Pure functions that query the in-memory index. No side effects, no API calls.
- **`server.py`** — Registers tools with the MCP SDK and handles transport (stdio).

---

## Implementation Notes

- Use the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- Transport: **stdio** (standard for local MCP servers)
- All data is read-only — no writes to the CSV/JSON files
- Word matching should be case-insensitive and strip whitespace
- If a word isn't found, return a clear error message (not an empty result)
- The `quiz_me` tool should use `random` for option selection and ordering, seeded per-call for variety
