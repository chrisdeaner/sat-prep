"""
tools.py — Tool implementations for the SAT Vocab MCP server.

Pure functions that query the in-memory word index.
No side effects, no file I/O, no API calls.
"""

import random


def lookup_word(index: dict, word: str) -> dict:
    """
    Look up a single SAT vocabulary word.

    Parameters
    ----------
    index : dict
        The word index from data.load_vocab_data().
    word : str
        The word to look up (case-insensitive).

    Returns
    -------
    dict with word data, or an error dict if not found.
    """
    key = word.strip().lower()
    if key not in index:
        return {"error": f"Word '{word}' not found in the SAT vocabulary database (275 words)."}
    return index[key]


def list_words(index: dict, tier: str | None = None, limit: int | None = None) -> dict:
    """
    List SAT vocabulary words, optionally filtered by frequency tier.

    Parameters
    ----------
    index : dict
        The word index.
    tier : str or None
        Filter by "high", "medium", or "low". None returns all.
    limit : int or None
        Max number of words to return. None returns all matching.

    Returns
    -------
    dict with total count and list of word summaries.
    """
    words = list(index.values())

    if tier:
        tier_lower = tier.strip().lower()
        words = [w for w in words if w["frequency_tier"] == tier_lower]

    # Sort by score (highest first), then alphabetically
    words.sort(key=lambda w: (-w["score"], w["word"]))

    total = len(words)
    if limit is not None and limit > 0:
        words = words[:limit]

    return {
        "total": total,
        "showing": len(words),
        "words": [
            {
                "word": w["word"],
                "definition": w["definition"],
                "score": w["score"],
                "frequency_tier": w["frequency_tier"],
            }
            for w in words
        ],
    }


def quiz_me(index: dict, count: int = 5, tier: str | None = None) -> dict:
    """
    Generate a multiple-choice vocabulary quiz.

    Each question blanks out the target word in a real example sentence
    and provides 4 answer options from the same tier.

    Parameters
    ----------
    index : dict
        The word index.
    count : int
        Number of questions (default 5, max 20).
    tier : str or None
        Restrict questions to a frequency tier.

    Returns
    -------
    dict with a list of questions.
    """
    count = max(1, min(count, 20))

    # Filter to words that have at least one sentence
    candidates = [
        w for w in index.values()
        if w["sentences"] and len(w["sentences"]) > 0
    ]

    if tier:
        tier_lower = tier.strip().lower()
        candidates = [w for w in candidates if w["frequency_tier"] == tier_lower]

    if len(candidates) < 4:
        return {"error": "Not enough words with sentences to generate a quiz."}

    # Pick question words
    quiz_words = random.sample(candidates, min(count, len(candidates)))

    questions = []
    for word_data in quiz_words:
        target_word = word_data["word"]
        sentence = random.choice(word_data["sentences"])

        # Blank out the target word in the sentence (case-insensitive)
        import re
        blanked = re.sub(
            re.escape(target_word),
            "______",
            sentence,
            flags=re.IGNORECASE,
        )

        # Build 4 options: 1 correct + 3 distractors from same tier
        same_tier = [
            w for w in candidates
            if w["word"].lower() != target_word.lower()
        ]
        distractors = random.sample(same_tier, min(3, len(same_tier)))
        options = [target_word] + [d["word"] for d in distractors]
        random.shuffle(options)

        questions.append({
            "sentence_with_blank": blanked,
            "options": options,
            "correct_answer": target_word,
            "correct_index": options.index(target_word),
            "definition_hint": word_data["definition"],
        })

    return {"count": len(questions), "questions": questions}
