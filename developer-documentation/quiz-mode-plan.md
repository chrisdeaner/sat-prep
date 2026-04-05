# Quiz Mode — Implementation Plan

## Goal

Add an interactive multiple-choice quiz mode to the existing SAT Vocab Flash site (`docs/index.html`). This lets students test themselves directly on the site — no AI client or MCP server needed. Just open the URL and go.

---

## Current State

The flashcard site is a single `index.html` file (~787 lines) that:
- Loads `words.json` (275 words with definitions, sentences, scores, alt meanings)
- Renders flip cards with weighted shuffle and tier filtering
- Uses a dark theme with Inter font, accent color `#e94560`, glassmorphism cards
- Is mobile-first with swipe navigation, keyboard support
- Hosted on GitHub Pages

All quiz logic will reuse the same `words.json` — no new data files needed.

---

## Design

### Mode Switching

Add a **mode toggle** in the header area — two pill buttons: **Study** (flashcards) and **Quiz**.

- Clicking Quiz enters quiz mode; clicking Study returns to flashcards
- The current filter selection (All / High / Medium / Single) persists across modes
- State resets when switching modes (new quiz generated, flashcard deck reshuffled)

### Quiz Screen

Each question shows:
1. **Progress bar** — e.g., "Question 3 of 10" with a visual progress indicator
2. **Example sentence** with the target word blanked out (`______`)
3. **4 answer options** as tappable buttons, styled like the existing filter pills but larger
4. **Feedback** — after selecting:
   - Correct: option turns green, brief celebration animation
   - Wrong: selected option turns red, correct answer highlights green, definition shown
5. **Next button** appears after answering to advance

### Results Screen

After all questions:
1. **Score** — e.g., "8 / 10" with a percentage ring or bar
2. **Word-by-word breakdown** — which you got right/wrong, with definitions for missed words
3. **Actions**: "Try Again" (same settings), "New Quiz" (reshuffle), "Back to Study"

### Quiz Settings

Before starting, show a compact config panel:
- **Number of questions**: 5, 10, 15, 20 (pill buttons, default 10)
- **Tier filter**: reuses the existing filter pills (All / High / Medium / Single)
- **Start Quiz** button

---

## Technical Approach

### Architecture

Everything stays in a single `index.html` file to match the existing pattern. The `App` object gets extended with quiz state and methods:

```
App (existing)
├── words[], filtered[], currentIndex, activeFilter
├── init(), applyFilter(), weightedShuffle()
├── next(), prev(), flip()
├── render(), renderCard(), bindEvents()
│
└── Quiz (new)
    ├── quizState: { questions[], currentQ, answers[], score }
    ├── generateQuiz(count, filterFn)
    ├── renderQuizSetup()
    ├── renderQuizQuestion()
    ├── handleAnswer(selectedIndex)
    ├── renderQuizResults()
    └── bindQuizEvents()
```

### Quiz Generation Logic

Port the same algorithm from `mcp_server/tools.py`:
1. Filter words to those with ≥1 sentence
2. Apply tier filter
3. Randomly select `count` words
4. For each word:
   - Pick a random sentence, blank out the target word (case-insensitive regex)
   - Pick 3 distractors from the same filtered pool
   - Shuffle the 4 options
5. Return array of question objects

### CSS Additions

New styles needed (extend existing design tokens):

| Element | Style Notes |
|---------|-------------|
| Mode toggle | Same style as filter pills, slightly larger, fixed position in header |
| Question card | Same card dimensions/bg as flashcard, but with different internal layout |
| Answer buttons | Pill-shaped, full-width, stacked vertically, ~48px tall, border style |
| Answer feedback | Green (`#2ecc71`) for correct, red (`#e74c3c`) for wrong, with transitions |
| Progress bar | Thin bar below header, accent gradient fill, animates on advance |
| Results score | Large centered number, accent gradient text (matches header h1) |
| Results breakdown | Scrollable list, checkmark/X icons, compact rows |

### Animations

- Answer selection: subtle scale pulse on tap
- Correct answer: brief green glow + confetti-like particle burst (CSS-only)
- Wrong answer: shake animation on selected option
- Question transition: slide-left (reuse existing `exitLeft`/`enterCard` keyframes)
- Score reveal: count-up animation on the final number

---

## Proposed Changes

### [MODIFY] [index.html](file:///Users/chrisdeaner/work/vibes/sat-prep/docs/index.html)

All changes are in this single file:

**CSS additions (~120 lines):**
- Mode toggle styles
- Quiz question layout
- Answer button states (default, hover, correct, wrong, disabled)
- Progress bar
- Results screen
- Feedback animations

**HTML changes:**
- Add mode toggle buttons to the header template (in `render()`)

**JS additions (~200 lines):**
- `generateQuiz(count, filterFn)` — builds question array from `words.json`
- `renderQuizSetup()` — shows settings panel (count + tier)
- `renderQuizQuestion()` — renders current question with blanked sentence + options
- `handleAnswer(index)` — processes answer, shows feedback, updates score
- `renderQuizResults()` — shows final score + breakdown
- `bindQuizEvents()` — event listeners for quiz mode interactions

**JS modifications:**
- `render()` — add mode toggle to header, conditionally render flashcard or quiz
- `bindEvents()` — add mode toggle click handler

**Estimated total: ~320 new lines, ~20 modified lines.**

---

## What's NOT Changing

- `words.json` format — no changes needed
- `build_site.py` — no changes needed
- Flashcard mode — all existing functionality preserved
- Mobile responsiveness — quiz mode follows same mobile-first approach
- No new files or dependencies

---

## Verification Plan

### Manual Testing
- [ ] Mode toggle switches cleanly between Study and Quiz
- [ ] Quiz setup shows correct word counts per tier
- [ ] Questions display with blanked sentences and 4 options
- [ ] Correct/wrong feedback animations work
- [ ] Score tallies correctly
- [ ] Results breakdown shows all questions with right/wrong status
- [ ] "Try Again" and "New Quiz" work
- [ ] Works on mobile (touch targets, no overflow, swipe doesn't interfere)
- [ ] Keyboard navigation works (1-4 keys or A-D for options, Enter for next)
- [ ] Filter persists when switching modes

### Browser Testing
- [ ] Test in Chrome, Safari, Firefox
- [ ] Test on iPhone Safari (primary target for a high schooler)

### Edge Cases
- [ ] Quiz with tier that has < 4 words (should show error/fallback)
- [ ] All questions answered correctly
- [ ] All questions answered wrong
- [ ] Switching modes mid-quiz resets state
