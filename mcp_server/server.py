"""
server.py — MCP server entry point for SAT Vocab Lookup.

Registers three tools (lookup_word, list_words, quiz_me) and serves
them over stdio transport using the official MCP Python SDK.

Usage:
    python -m mcp_server.server
"""

from mcp.server.fastmcp import FastMCP

from mcp_server.data import load_vocab_data
from mcp_server import tools as tool_fns


# Load all vocabulary data once at startup
WORD_INDEX = load_vocab_data()

# Create the MCP server
mcp = FastMCP(
    "SAT Vocab Lookup",
    instructions=(
        "An SAT vocabulary study tool. Use lookup_word to get definitions, "
        "example sentences, and alternate meanings. Use list_words to browse "
        "the 275-word vocabulary list by frequency tier. Use quiz_me to "
        "generate interactive multiple-choice quizzes."
    ),
)


@mcp.tool()
def lookup_word(word: str) -> dict:
    """Look up an SAT vocabulary word. Returns its definition, frequency score,
    example sentences, and alternate meaning (if any).

    Args:
        word: The vocabulary word to look up (case-insensitive).
    """
    return tool_fns.lookup_word(WORD_INDEX, word)


@mcp.tool()
def list_words(tier: str = "", limit: int = 0) -> dict:
    """List SAT vocabulary words, optionally filtered by frequency tier.

    Args:
        tier: Filter by frequency tier — "high" (3+ SATs), "medium" (2 SATs),
              or "low" (1 SAT). Leave empty for all words.
        limit: Maximum number of words to return. 0 means return all.
    """
    return tool_fns.list_words(
        WORD_INDEX,
        tier=tier if tier else None,
        limit=limit if limit > 0 else None,
    )


@mcp.tool()
def quiz_me(count: int = 5, tier: str = "") -> dict:
    """Generate an SAT vocabulary multiple-choice quiz. Each question shows a
    real example sentence with the target word blanked out and 4 answer options.

    Args:
        count: Number of questions (1-20, default 5).
        tier: Restrict to a frequency tier — "high", "medium", or "low".
              Leave empty for all tiers.
    """
    return tool_fns.quiz_me(
        WORD_INDEX,
        count=count,
        tier=tier if tier else None,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
