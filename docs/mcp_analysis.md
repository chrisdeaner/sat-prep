# MCP Server Candidates — NextDNS & SAT Prep

## What Makes a Good MCP Tool?

An MCP tool is worth building when it's **reusable across contexts** — i.e., you'd want to call it from Claude, Gemini, a script, or another app without copy-pasting code. The best candidates are:

- Self-contained operations with clear inputs → outputs
- Things you'd otherwise have to open a specific app to do
- Data lookups or transformations that are useful conversationally

---

## 🏆 High-Value Candidates

### 1. `domain-classifier` (from NextDNS)

**What it does:** Takes a domain name → returns a verdict (Safe / Suspicious / Adult), category, and one-line description. Uses Gemini + Google Search grounding under the hood.

**Why it's great for MCP:**
- Standalone: give it `"faphaven.com"` → get back `{ verdict: "Adult/Dangerous", category: "Adult", context: "Adult content streaming platform" }`
- Useful from *any* context — not just the Streamlit dashboard
- An LLM chatting with you could call this tool to answer "is this domain safe?" without you opening the app

**Source:** [backend.py — `_research_single_domain()` + `_classify_batch()`](file:///Users/chrisdeaner/work/vibes/nextdns/backend.py#L547-L641)

**MCP Tool Shape:**
```
Tool: classify_domain
Inputs:  { domain: string, api_key?: string }
Outputs: { domain, category, verdict, context }
```

---

### 2. `vocab-lookup` (from SAT Prep)

**What it does:** Look up any SAT vocabulary word → get its definition, frequency score, example sentences, and alternate meanings.

**Why it's great for MCP:**
- You have 275 words with rich data (definitions, 3 example sentences each, alt meanings for 25+ words)
- A student chatting with an LLM could say "explain eschew" and the LLM would call this tool to get authoritative, SAT-specific data instead of making something up
- Zero API cost — it's just a JSON/CSV lookup

**Source files:**
- [sat_vocabulary.csv](file:///Users/chrisdeaner/work/vibes/sat-prep/sat_vocabulary.csv) — word, definition, score
- [sentences.json](file:///Users/chrisdeaner/work/vibes/sat-prep/sentences.json) — 3 example sentences per word
- [alt_meanings.json](file:///Users/chrisdeaner/work/vibes/sat-prep/alt_meanings.json) — tricky secondary meanings

**MCP Tool Shape:**
```
Tool: lookup_word
Inputs:  { word: string }
Outputs: { word, definition, score, frequency_tier, sentences[], alt_meaning? }

Tool: list_words
Inputs:  { tier?: "high" | "medium" | "low", limit?: number }
Outputs: { words: [{ word, definition, score }] }

Tool: quiz_me
Inputs:  { count?: number, tier?: "high" | "medium" | "low" }
Outputs: { questions: [{ word, options[], correct_index, sentence_hint }] }
```

> [!TIP]
> The `quiz_me` tool is especially powerful — it turns the static data into an interactive experience that works in *any* LLM chat, not just on the flashcard site.

---

### 3. `domain-list-manager` (from NextDNS)

**What it does:** Query, add to, or remove from the safe/adult domain pattern lists. Check if a domain matches any existing pattern.

**Why it's great for MCP:**
- You could ask "is `cdn.example.com` in my safe list?" without opening the Streamlit app
- You could say "add `analytics.example.com` to the safe list" conversationally
- Pairs naturally with the `domain-classifier` tool above

**Source:** [backend.py — `load_domains_list()`, `save_domains_df()`, `promote_domain_verdicts()`](file:///Users/chrisdeaner/work/vibes/nextdns/backend.py#L246-L794)

**MCP Tool Shape:**
```
Tool: check_domain
Inputs:  { domain: string }
Outputs: { status: "adult" | "safe" | "unknown", matched_pattern?: string }

Tool: add_domain_pattern
Inputs:  { pattern: string, list: "adult" | "safe" }
Outputs: { success: boolean, total_patterns: number }
```

---

## 📊 Medium-Value Candidates

### 4. `dns-activity-query` (from NextDNS)

**What it does:** Query the ingested DNS log data — daily activity counts, domains accessed on a specific date, date range summary.

**Why it's great for MCP:**
- "What adult domains were accessed last Tuesday?" becomes a simple tool call
- Useful for reporting/monitoring without opening the dashboard

**Source:** [backend.py — `get_daily_activity_data()`](file:///Users/chrisdeaner/work/vibes/nextdns/backend.py#L419-L442)

**MCP Tool Shape:**
```
Tool: dns_activity
Inputs:  { date?: string, date_range?: { start, end } }
Outputs: { dates: [{ date, count, domains[] }] }
```

---

### 5. `vocab-content-generator` (from SAT Prep)

**What it does:** Generate new SAT-style example sentences, definitions, or alternate meaning analysis for vocabulary words using Gemini.

**Why it's great for MCP:**
- "Generate 3 new practice sentences for 'ubiquitous'" — callable from any context
- Could be used to expand the word list or create study materials on-the-fly

**Source:** [generate_sentences.py](file:///Users/chrisdeaner/work/vibes/sat-prep/scripts/generate_sentences.py), [backfill_definitions.py](file:///Users/chrisdeaner/work/vibes/sat-prep/scripts/backfill_definitions.py), [generate_alt_meanings.py](file:///Users/chrisdeaner/work/vibes/sat-prep/scripts/generate_alt_meanings.py)

**MCP Tool Shape:**
```
Tool: generate_sentences
Inputs:  { words: string[], count_per_word?: number }
Outputs: { results: { [word]: string[] } }

Tool: generate_definition
Inputs:  { word: string }
Outputs: { word, definition }
```

---

## ❌ What Wouldn't Be Worth Extracting

| Functionality | Why Not |
|---|---|
| **Log file upload/ingestion** (`prefilter_log`, `ingest_logs`) | Too tightly coupled to file I/O and the Streamlit upload flow. MCP tools should be quick request→response, not "process a 500MB CSV" |
| **The Streamlit UI itself** | MCP is about headless tools, not UI |
| **`build_site.py`** | It's a build step (CSV → JSON merge), not something you'd call conversationally |
| **Timeframe tracking** | Internal bookkeeping, not useful as a standalone tool |

---

## Recommended Starting Point

If I were picking **one MCP server to build first**, I'd go with **`vocab-lookup`** from SAT Prep:

1. **Zero external dependencies** — no API keys needed, just reads local files
2. **Instant value** — any LLM conversation can become an SAT study session
3. **Simple to implement** — load CSV + JSON on startup, expose 2-3 tools
4. **Good learning project** — straightforward enough to learn MCP patterns without fighting complexity

Then follow up with `domain-classifier` since it's the most powerful but needs Gemini API key management.

---

## Questions for You

1. **Which of these resonate most with how you'd actually use them?** The analysis above is based on technical fit, but your workflow matters more.
2. **Do you want these as separate MCP servers or one combined server?** Separate is cleaner architecturally, but combined is simpler to manage.
3. **Ready to build one?** I can scaffold the first MCP server whenever you want to go.
