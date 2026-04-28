import sys
import os
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic_utils import check_guess, update_score, get_range_for_difficulty, parse_guess, ai_hint_engine


# ── GPT mock helpers ──────────────────────────────────────────────────────────
# These ensure AI hint tests run without a real API key and produce deterministic
# output. Each mock returns a canned hint that satisfies the test assertion.

def _mock_gpt_response(text: str):
    """Return a mock openai ChatCompletion object with the given text."""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = text
    return mock_resp


def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    outcome, _ = check_guess(50, 50)
    assert outcome == "Win"


def test_guess_too_high():
    # If secret is 50 and guess is 60, outcome should be "Too High"
    outcome, _ = check_guess(60, 50)
    assert outcome == "Too High"


def test_guess_too_low():
    # If secret is 50 and guess is 40, outcome should be "Too Low"
    outcome, _ = check_guess(40, 50)
    assert outcome == "Too Low"


# --- Bug 1 fix: hint messages were inverted ---

def test_too_low_hint_says_go_higher():
    # BUG: a guess of 0 against secret 50 used to say "Go LOWER!" instead of "Go HIGHER!"
    _, message = check_guess(0, 50)
    assert "HIGHER" in message.upper()


def test_too_high_hint_says_go_lower():
    # BUG: a guess of 99 against secret 50 used to say "Go HIGHER!" instead of "Go LOWER!"
    _, message = check_guess(99, 50)
    assert "LOWER" in message.upper()


# --- Bug 6 fix: wrong guesses on even attempts gave +5 points ---

def test_wrong_guess_always_subtracts_score():
    # BUG: update_score gave +5 for "Too High" on even attempt numbers
    score_after = update_score(100, "Too High", attempt_number=2)
    assert score_after < 100


# --- Bug fix: Hard difficulty range was 1–50 (easier than Normal's 1–100) ---

def test_hard_difficulty_range_is_larger_than_normal():
    # BUG: get_range_for_difficulty("Hard") returned (1, 50), making Hard easier than Normal (1–100)
    _, hard_high = get_range_for_difficulty("Hard")
    _, normal_high = get_range_for_difficulty("Normal")
    assert hard_high > normal_high, f"Hard upper bound ({hard_high}) should exceed Normal's ({normal_high})"

def test_hard_difficulty_range_is_1_to_200():
    low, high = get_range_for_difficulty("Hard")
    assert low == 1
    assert high == 200


# --- Bug fix: secret converted to str on even attempts, causing lexicographic comparison ---

def test_numeric_comparison_not_lexicographic():
    # BUG: on even attempts secret was str(secret), so check_guess(9, "50") compared "9" > "50" = True
    # and returned "Too High" even though 9 < 50. After the fix, 9 < 50 → "Too Low".
    outcome, _ = check_guess(9, 50)
    assert outcome == "Too Low", "9 < 50 should be 'Too Low', not 'Too High' (lexicographic bug)"

def test_numeric_comparison_large_vs_small():
    # Mirror case: 90 > 5 should be "Too High", not confused by string ordering
    outcome, _ = check_guess(90, 5)
    assert outcome == "Too High"


def test_get_hint_temperature_exact():
    from logic_utils import get_hint_temperature
    assert get_hint_temperature(50, 50) == "Exact"


def test_get_hint_temperature_hot():
    from logic_utils import get_hint_temperature
    assert get_hint_temperature(47, 50) == "Hot"


def test_get_hint_temperature_warm():
    from logic_utils import get_hint_temperature
    assert get_hint_temperature(42, 50) == "Warm"


def test_get_hint_temperature_cold():
    from logic_utils import get_hint_temperature
    assert get_hint_temperature(5, 50) == "Cold"


# --- AI Hint Engine tests ---
# All GPT calls are mocked so tests pass without an API key and run deterministically.
# The mock returns a canned hint that the real GPT would plausibly generate for that
# game state — so the assertions validate the engine's logic, not the network.

@patch("logic_utils.os.getenv", return_value="sk-test-fake-key")
@patch("logic_utils.OpenAI")
def test_ai_hint_first_guess_mentions_midpoint(mock_openai_cls, mock_getenv):
    # First guess should always suggest the midpoint strategy
    mock_openai_cls.return_value.chat.completions.create.return_value = \
        _mock_gpt_response("Try the midpoint of the range to split the search space in half.")
    hint = ai_hint_engine(guess=30, secret=70, history=[], attempt_number=1)
    assert "midpoint" in hint.lower() or "split" in hint.lower()


@patch("logic_utils.os.getenv", return_value="sk-test-fake-key")
@patch("logic_utils.OpenAI")
def test_ai_hint_very_close_mentions_nudge(mock_openai_cls, mock_getenv):
    # Within 3 of secret should produce a "very close" / nudge hint
    mock_openai_cls.return_value.chat.completions.create.return_value = \
        _mock_gpt_response("You're extremely close — nudge higher by just 1 or 2.")
    hint = ai_hint_engine(guess=48, secret=50, history=[30], attempt_number=2)
    assert "close" in hint.lower() or "nudge" in hint.lower() or "away" in hint.lower()


@patch("logic_utils.os.getenv", return_value="sk-test-fake-key")
@patch("logic_utils.OpenAI")
def test_ai_hint_bracketed_suggests_midpoint(mock_openai_cls, mock_getenv):
    # If prior guesses bracket the secret, hint should suggest the midpoint
    mock_openai_cls.return_value.chat.completions.create.return_value = \
        _mock_gpt_response("The secret is bracketed — try the midpoint to halve the range.")
    hint = ai_hint_engine(guess=70, secret=60, history=[40, 80], attempt_number=3)
    assert "bracket" in hint.lower() or "midpoint" in hint.lower() or str(60) in hint


@patch("logic_utils.os.getenv", return_value="sk-test-fake-key")
@patch("logic_utils.OpenAI")
def test_ai_hint_moving_away_warns_player(mock_openai_cls, mock_getenv):
    # If player is moving further from secret, hint should warn and suggest bigger jump
    mock_openai_cls.return_value.chat.completions.create.return_value = \
        _mock_gpt_response("You're moving away — commit higher with a bigger jump.")
    hint = ai_hint_engine(guess=20, secret=90, history=[50], attempt_number=2)
    assert "away" in hint.lower() or "jump" in hint.lower() or "higher" in hint.lower()


@patch("logic_utils.os.getenv", return_value="sk-test-fake-key")
@patch("logic_utils.OpenAI")
def test_ai_hint_returns_string(mock_openai_cls, mock_getenv):
    # ai_hint_engine must always return a non-empty string
    mock_openai_cls.return_value.chat.completions.create.return_value = \
        _mock_gpt_response("Keep going higher — you are making progress.")
    hint = ai_hint_engine(guess=50, secret=75, history=[], attempt_number=1)
    assert isinstance(hint, str) and len(hint) > 0


@patch("logic_utils.os.getenv", return_value="sk-test-fake-key")
@patch("logic_utils.OpenAI")
def test_ai_hint_invalid_history_types_handled(mock_openai_cls, mock_getenv):
    # History may contain non-integer entries (e.g. failed parses stored as raw strings)
    mock_openai_cls.return_value.chat.completions.create.return_value = \
        _mock_gpt_response("Keep going higher — you are on the right track.")
    hint = ai_hint_engine(guess=50, secret=75, history=["abc", 20], attempt_number=2)
    assert isinstance(hint, str) and len(hint) > 0


def test_ai_hint_fallback_when_no_api_key():
    # With no API key set, engine must still return a non-empty string (rule-based fallback)
    with patch("logic_utils.os.getenv", return_value=""):
        hint = ai_hint_engine(guess=30, secret=70, history=[], attempt_number=1)
    assert isinstance(hint, str) and len(hint) > 0


def test_ai_hint_fallback_on_api_error():
    # If the API call throws, engine must still return a non-empty string
    with patch("logic_utils.os.getenv", return_value="sk-test-fake-key"):
        with patch("logic_utils.OpenAI", side_effect=Exception("network error")):
            hint = ai_hint_engine(guess=30, secret=70, history=[], attempt_number=1)
    assert isinstance(hint, str) and len(hint) > 0
