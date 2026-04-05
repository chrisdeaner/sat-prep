"""
Tests for the SAT Vocab MCP server tools.

Validates data loading, word lookup, listing, and quiz generation
against the real vocabulary data files.
"""

import pytest

from mcp_server.data import load_vocab_data, _score_to_tier
from mcp_server.tools import lookup_word, list_words, quiz_me


@pytest.fixture(scope="module")
def index():
    """Load the word index once for all tests in this module."""
    return load_vocab_data()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

class TestDataLoading:
    def test_loads_all_words(self, index):
        assert len(index) == 275  # Current word count

    def test_word_has_required_fields(self, index):
        word = index["eschew"]
        assert word["word"] == "eschew"
        assert word["definition"] != ""
        assert word["score"] == 6
        assert word["frequency_tier"] == "high"
        assert isinstance(word["sentences"], list)

    def test_sentences_loaded(self, index):
        word = index["eschew"]
        assert len(word["sentences"]) == 5

    def test_alt_meanings_loaded(self, index):
        word = index["sanction"]
        assert word["alt_meaning"] is not None
        assert word["alt_meaning"]["alt_definition"] != ""
        assert word["alt_meaning"]["note"] != ""

    def test_word_without_alt_meaning(self, index):
        word = index["eschew"]
        assert word["alt_meaning"] is None


class TestScoreToTier:
    def test_high(self):
        assert _score_to_tier(6) == "high"
        assert _score_to_tier(4) == "high"

    def test_medium(self):
        assert _score_to_tier(3) == "medium"
        assert _score_to_tier(2) == "medium"

    def test_low(self):
        assert _score_to_tier(1) == "low"


# ---------------------------------------------------------------------------
# lookup_word
# ---------------------------------------------------------------------------

class TestLookupWord:
    def test_found(self, index):
        result = lookup_word(index, "eschew")
        assert result["word"] == "eschew"
        assert result["score"] == 6

    def test_case_insensitive(self, index):
        result = lookup_word(index, "ESCHEW")
        assert result["word"] == "eschew"

    def test_not_found(self, index):
        result = lookup_word(index, "xyznotaword")
        assert "error" in result

    def test_whitespace_stripped(self, index):
        result = lookup_word(index, "  eschew  ")
        assert result["word"] == "eschew"


# ---------------------------------------------------------------------------
# list_words
# ---------------------------------------------------------------------------

class TestListWords:
    def test_all_words(self, index):
        result = list_words(index)
        assert result["total"] == 275
        assert result["showing"] == 275

    def test_filter_by_tier(self, index):
        result = list_words(index, tier="high")
        assert result["total"] > 0
        assert all(w["frequency_tier"] == "high" for w in result["words"])

    def test_limit(self, index):
        result = list_words(index, limit=5)
        assert result["showing"] == 5
        assert result["total"] == 275

    def test_sorted_by_score_desc(self, index):
        result = list_words(index, limit=10)
        scores = [w["score"] for w in result["words"]]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# quiz_me
# ---------------------------------------------------------------------------

class TestQuizMe:
    def test_default_count(self, index):
        result = quiz_me(index)
        assert result["count"] == 5
        assert len(result["questions"]) == 5

    def test_custom_count(self, index):
        result = quiz_me(index, count=3)
        assert result["count"] == 3

    def test_max_count_capped(self, index):
        result = quiz_me(index, count=50)
        assert result["count"] <= 20

    def test_question_structure(self, index):
        result = quiz_me(index, count=1)
        q = result["questions"][0]
        assert "sentence_with_blank" in q
        assert "______" in q["sentence_with_blank"]
        assert "options" in q
        assert len(q["options"]) == 4
        assert q["correct_answer"] in q["options"]
        assert q["correct_index"] == q["options"].index(q["correct_answer"])

    def test_filter_by_tier(self, index):
        result = quiz_me(index, count=3, tier="high")
        assert result["count"] == 3
        # Verify all quiz words are from the high tier
        for q in result["questions"]:
            word_data = index[q["correct_answer"].lower()]
            assert word_data["frequency_tier"] == "high"
