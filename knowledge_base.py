"""
knowledge_base.py — RAG (Retrieval-Augmented Generation) layer for the
Game Glitch Investigator AI Hint Engine.

This module simulates a document retrieval system.  A small corpus of
game-strategy "documents" is stored as structured records.  The
retrieve_tip() function scores each document against the current game
context and returns the most relevant one — exactly like a RAG pipeline
retrieves a chunk from a vector store before passing it to a generator.

The scoring function uses keyword matching across four context signals:
  • pattern  — the reasoning pattern selected by ai_hint_engine
  • attempt  — early / mid / late game phase
  • temperature — how close the player is (Exact / Hot / Warm / Cold)
  • difficulty — Easy / Normal / Hard
"""

from typing import Dict, List, Optional


KNOWLEDGE_BASE: List[Dict] = [
    {
        "id": "binary_search_intro",
        "tags": ["first_guess", "early", "strategy"],
        "tip": (
            "Strategy tip: Always start at the midpoint of the range. "
            "Binary search halves the remaining possibilities with every guess, "
            "giving you the fastest path to the answer."
        ),
    },
    {
        "id": "binary_search_bracketed",
        "tags": ["bracketed", "strategy", "mid"],
        "tip": (
            "Strategy tip: You have bracketed the secret! Pick the midpoint "
            "of your two boundary guesses — this is binary search in action "
            "and guarantees finding the answer in O(log n) steps."
        ),
    },
    {
        "id": "oscillation_warning",
        "tags": ["moving_away", "warning", "mid", "late"],
        "tip": (
            "Strategy tip: Avoid oscillating back and forth. "
            "Once you know a direction, commit to it and move in "
            "larger increments until you overshoot, then bracket and close in."
        ),
    },
    {
        "id": "hot_zone_precision",
        "tags": ["very_close", "Hot", "Exact", "late"],
        "tip": (
            "Strategy tip: You're in the hot zone! Adjust by just 1–2 at a time. "
            "Big jumps now will overshoot the target and waste attempts."
        ),
    },
    {
        "id": "cold_zone_aggression",
        "tags": ["on_track", "Cold", "early", "mid"],
        "tip": (
            "Strategy tip: You're still far from the target (Cold). "
            "Be aggressive — jump by 20–30% of the remaining range "
            "to narrow the search space quickly."
        ),
    },
    {
        "id": "hard_mode_efficiency",
        "tags": ["Hard", "strategy", "early"],
        "tip": (
            "Strategy tip: On Hard mode the range is 1–200 with only 5 attempts. "
            "Binary search is mandatory — start at 100, then 50 or 150, "
            "and always cut the remaining range in half."
        ),
    },
    {
        "id": "easy_mode_exploration",
        "tags": ["Easy", "on_track", "early"],
        "tip": (
            "Strategy tip: On Easy mode (range 1–20) you have 6 attempts. "
            "Start at 10, then move by 5, and close in. "
            "You can afford to explore a little."
        ),
    },
    {
        "id": "late_game_patience",
        "tags": ["late", "warm", "Warm", "on_track"],
        "tip": (
            "Strategy tip: Late in the game, patience beats speed. "
            "Move in small, deliberate steps and track which guesses "
            "gave you 'Warm' versus 'Hot' readings."
        ),
    },
    {
        "id": "general_direction",
        "tags": ["on_track", "Too Low", "Too High"],
        "tip": (
            "Strategy tip: Always remember the direction of your last hint. "
            "If the hint said 'Go HIGHER', every subsequent guess must be "
            "above your current guess — never go back below it."
        ),
    },
]


def retrieve_tip(
    pattern: str,
    temperature: str,
    difficulty: str,
    attempt_number: int,
) -> Optional[str]:
    """Retrieve the most relevant strategy tip for the current game context.

    This is the RAG retrieval step.  Each knowledge base document is scored
    by counting how many of its tags match the current context signals.  The
    document with the highest score is returned.  Ties are broken by document
    order (earlier documents are preferred, acting as a recency/relevance
    prior).

    Args:
        pattern: Reasoning pattern from ai_hint_engine (e.g. 'bracketed').
        temperature: Proximity label from get_hint_temperature (e.g. 'Hot').
        difficulty: Difficulty label (Easy / Normal / Hard).
        attempt_number: 1-based attempt counter used to derive game phase.

    Returns:
        The tip string of the best-matching document, or None if no document
        scores above zero (should not happen with the current corpus).
    """
    phase = _game_phase(attempt_number, difficulty)

    context_signals = {pattern, temperature, difficulty, phase}

    best_score = -1
    best_tip: Optional[str] = None

    for doc in KNOWLEDGE_BASE:
        score = len(set(doc["tags"]) & context_signals)
        if score > best_score:
            best_score = score
            best_tip = doc["tip"]

    return best_tip if best_score > 0 else None


def _game_phase(attempt_number: int, difficulty: str) -> str:
    """Map attempt number to a qualitative game phase label.

    Args:
        attempt_number: 1-based attempt count.
        difficulty: Difficulty label used to determine total attempts.

    Returns:
        One of 'early', 'mid', or 'late'.
    """
    limit_map = {"Easy": 6, "Normal": 8, "Hard": 5}
    limit = limit_map.get(difficulty, 8)
    ratio = attempt_number / limit
    if ratio <= 0.33:
        return "early"
    if ratio <= 0.66:
        return "mid"
    return "late"
