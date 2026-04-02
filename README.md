# SAT Prep — Vocabulary Practice App

An interactive SAT prep tool focused on helping students learn, retain, and master the vocabulary most likely to appear on the SAT.

## Overview

The SAT consistently tests a recurring pool of vocabulary words. By analyzing data from 22 official SAT administrations (March 2024 – March 2026), we've identified the highest-frequency words and organized them by priority so students can study smarter, not harder.

This app turns that data into an interactive learning experience with study modes, quizzes, and progress tracking.

## Vocabulary Data

Our word list is sourced from [Mr. John's Test Prep](https://www.mrjohnstestprep.com/vocabulary-trends-from-the-last-two-years-of-official-sats/) and community-reported data from r/SAT and roots2words.com.

| Priority | Words | Description |
|----------|-------|-------------|
| **High-Frequency** | 29 words | Appeared on 3+ SATs — includes definitions |
| **Medium-Frequency** | 64 words | Appeared on exactly 2 SATs |
| **Single-Occurrence** | 163 words | Appeared once across all administrations |

All 256 words are stored in `sat_vocabulary.csv`.

## Project Structure

```
sat-prep/
├── AGENTS.md                          # AI coding guidelines & project conventions
├── README.md                          # This file
├── .gitignore                         # Git ignore rules
├── .env                               # Gemini API key (git-ignored)
├── requirements.txt                   # Python dependencies
├── sat_vocabulary.csv                 # Source of truth — 255 words with definitions & scores
├── scripts/
│   ├── backfill_definitions.py        # Fill missing definitions via Gemini
│   └── build_site.py                  # Generate docs/words.json from CSV
├── tests/
│   ├── test_backfill.py               # Tests for backfill script
│   └── test_build.py                  # Tests for build script
├── developer-documentation/           # Plans, design docs, dev notes
│   └── flashcard-site-plan.md         # Implementation plan
└── docs/                              # GitHub Pages root (static site only)
    ├── index.html                     # Flashcard app (HTML/CSS/JS)
    └── words.json                     # Generated vocabulary data
```

## Getting Started

### Prerequisites

- Python 3.10+
- A Gemini API key (only needed if backfilling definitions)

### 1. Set Up the Environment

```bash
# Clone the repo
git clone https://github.com/<your-username>/sat-prep.git
cd sat-prep

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Flashcard App Locally

```bash
# Serve the static site from the docs/ folder
cd docs
python3 -m http.server 8080
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

### 3. Backfill Missing Definitions

If you add new words to `sat_vocabulary.csv` and they're missing definitions, the backfill script will fill them in automatically:

```bash
# Make sure your venv is activated
source venv/bin/activate

# Set up your Gemini API key (required)
echo "GEMINI_API_KEY=your-key-here" > .env

# Run the backfill script
python scripts/backfill_definitions.py
```

**How it works:**
1. Reads `sat_vocabulary.csv` and finds words with empty `definition` fields
2. Sends words to Gemini in batches with an SAT-focused prompt
3. Writes the definitions back to the CSV

You can preview what would happen without making changes:

```bash
python scripts/backfill_definitions.py --dry-run
```

### 4. Rebuild the Site Data

After updating the CSV (e.g., adding words or editing definitions), regenerate the JSON file:

```bash
python scripts/build_site.py
```

This converts `sat_vocabulary.csv` → `docs/words.json`, sorted by score (high-frequency words first).

### 5. Run Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

## Adding New Words

End-to-end workflow for adding vocabulary to the app:

```bash
# 1. Add words to sat_vocabulary.csv (leave definition blank, set score)

# 2. Backfill definitions via Gemini
python scripts/backfill_definitions.py

# 3. Rebuild the site data
python scripts/build_site.py

# 4. Commit and push (site auto-deploys via GitHub Pages)
git add . && git commit -m "feat: add new vocabulary words" && git push
```

## Deployment

The site is hosted on **GitHub Pages** and auto-deploys on every push to `main`:

1. Push the repo to GitHub
2. In repo **Settings → Pages**, set source to `main` branch, `/docs` folder
3. The site will be live at `https://<username>.github.io/sat-prep/`

## License

This project is licensed under the [MIT License](LICENSE).
