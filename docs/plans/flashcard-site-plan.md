# SAT Vocabulary Flashcard Site — Implementation Plan

## Overview

A mobile-first, static flashcard website for SAT vocabulary practice. The site shows a word on the front of a card, and reveals the definition on tap/click. Hosted on **GitHub Pages** with zero backend — all data is baked into the site at build time.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  LOCAL (one-time)                     │
│                                                      │
│  sat_vocabulary.csv ──► backfill_definitions.py       │
│       (227 missing)      │                           │
│                          ├─► Free Dictionary API     │
│                          └─► Gemini API (fallback)   │
│                          │                           │
│                          ▼                           │
│               sat_vocabulary.csv (complete)           │
│                          │                           │
│                          ▼                           │
│               build.py (generates site)              │
│                          │                           │
│                          ▼                           │
│               docs/index.html (static site)          │
└──────────────────────────────────────────────────────┘
                           │
                           ▼
               GitHub Pages (serves docs/)
```

### Two-Phase Workflow

| Phase | What | When | Tools |
|-------|------|------|-------|
| **Phase 1: Data Prep** | Backfill missing definitions into CSV | Run locally, once (or when words change) | Python, Free Dictionary API, Gemini |
| **Phase 2: Static Site** | Generate HTML/CSS/JS flashcard app from CSV | Run locally to build, then push to GitHub | Python build script or pure JS that loads a JSON file |

---

## Phase 1: Definition Backfill Script

### `scripts/backfill_definitions.py`

A Python script that fills in missing definitions:

1. Read `sat_vocabulary.csv`
2. For each word with an empty `definition` column:
   - **Try** the [Free Dictionary API](https://dictionaryapi.dev/): `GET https://api.dictionaryapi.dev/api/v2/entries/en/{word}`
   - **If not found**, queue for Gemini batch processing
3. Batch-call Gemini for any remaining words (using the retry/client pattern from the NextDNS project)
4. Write updated CSV back

**Dependencies:** `requests`, `google-genai`, `python-dotenv`

**Rate limiting:** Free Dictionary API has no key but is rate-limited; we'll add a ~0.5s delay between calls. Gemini uses the existing `_api_call_with_retry` pattern.

---

## Phase 2: Static Flashcard Site

### Option A: Pure Static (Recommended) ✅

The simplest approach — a single `index.html` with inline CSS/JS that loads vocabulary data from a `words.json` file.

```
docs/                    ← GitHub Pages serves this folder
├── index.html           ← Main app (HTML + inline CSS + JS)
└── words.json           ← Generated from CSV by build script
```

A small `scripts/build_site.py` converts `sat_vocabulary.csv` → `docs/words.json`. The HTML/CSS/JS are hand-written and committed directly.

**Pros:**
- Zero build tools, zero dependencies at runtime
- Instant deploy — just push to GitHub
- Easy to maintain and extend
- `words.json` is fetched at page load (tiny file, ~30KB)

**Cons:**
- Need to re-run `build_site.py` when words change (but this is rare)

### Option B: Fully Inlined

Bake the word data directly into `index.html` as a `<script>` tag. No separate JSON file.

**Pros:** Single file, works offline, no fetch needed
**Cons:** Harder to maintain, messier HTML

### Recommendation: **Option A** — it's clean, simple, and the JSON fetch is negligible.

---

## Site Design

### Mobile-First Flashcard UI

The site is designed primarily for phone use (thumb-friendly, single-column, large tap targets).

#### Core Interaction
1. **Card shows the word** (large, centered text)
2. **Tap/click the card** → card flips with a CSS 3D animation to reveal the definition
3. **Swipe or tap "Next"** → advance to the next card
4. **Tap "Previous"** → go back

#### UI Components

| Component | Description |
|-----------|-------------|
| **Header** | App title, current position (e.g., "12 / 256") |
| **Flashcard** | Large card with flip animation. Front = word, Back = definition + part of speech |
| **Navigation** | Previous / Next buttons below the card |
| **Filter Bar** | Filter by frequency tier (High / Medium / Single / All) |
| **Shuffle Toggle** | Randomize card order (weighted — higher score words appear more often) |

#### Design Principles
- **Dark mode by default** (easier on eyes for study sessions)
- **Large, readable typography** (Inter or system font stack)
- **Smooth 3D card flip** animation (CSS `transform: rotateY(180deg)`)
- **Touch-friendly** — minimum 44px tap targets, generous padding
- **No scrolling needed** — everything fits in viewport
- **Progressive enhancement** — works without JS for basic content, JS adds interactivity

#### Color Palette (Dark Mode)
```
Background:    #0f0f13 (near-black)
Card Face:     #1a1a2e (dark navy)
Card Back:     #16213e (slightly lighter navy)
Accent:        #e94560 (vibrant coral-red)
Text Primary:  #eaeaea
Text Secondary:#a0a0b0
```

---

## Folder Structure (Final)

```
sat-prep/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env                          ← Gemini API key (git-ignored)
├── sat_vocabulary.csv            ← Source of truth
├── requirements.txt              ← Python deps
├── scripts/
│   ├── backfill_definitions.py   ← Phase 1: fill missing definitions
│   └── build_site.py             ← Phase 2: CSV → JSON for the site
├── tests/
│   ├── test_backfill.py
│   └── test_build.py
└── docs/                         ← GitHub Pages root
    ├── index.html                ← Flashcard app
    └── words.json                ← Generated vocabulary data
```

---

## GitHub Pages Setup

1. In the repo settings, set GitHub Pages source to **"Deploy from a branch"**
2. Set branch to `main` and folder to `/docs`
3. The site will be live at `https://<username>.github.io/sat-prep/`

---

## Implementation Order

1. **Set up Python venv** and `requirements.txt`
2. **Build `backfill_definitions.py`** + tests → fill all 227 missing definitions
3. **Build `build_site.py`** + tests → generate `docs/words.json`
4. **Build `docs/index.html`** — the flashcard UI (HTML/CSS/JS)
5. **Polish & test** on mobile (responsive design, animations)
6. **Push to GitHub** and enable Pages

---

## Decisions Made

- **All 256 words are shown**, but shuffle uses **weighted random selection** — words with a higher `score` (frequency count) are more likely to be drawn. Implementation: use the score as a weight in a weighted random sampling algorithm (e.g., cumulative distribution or `score / totalScore` probability).
- **GitHub remote:** Create a new repo named `sat-prep` under the user's GitHub account. Enable GitHub Pages on `main` branch, `/docs` folder.

---

## Future Features (out of scope for v1)

- Score tracking / spaced repetition
- Quiz mode (multiple choice)
- Progress persistence (localStorage)
- Example sentences
- Keyboard shortcuts for desktop users
