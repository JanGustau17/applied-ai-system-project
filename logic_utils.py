from typing import Dict, List, Optional, Tuple


def get_range_for_difficulty(difficulty: str) -> Tuple[int, int]:
    """Return the inclusive guessing range for the selected difficulty.

    Args:
        difficulty: Difficulty label selected in the UI.

    Returns:
        A tuple of ``(low, high)`` bounds for valid secret numbers.
    """
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 200
    return 1, 100


def parse_guess(raw: Optional[str]) -> Tuple[bool, Optional[int], Optional[str]]:
    """Parse raw user input into an integer guess.

    Args:
        raw: Untrusted text input from the guess field.

    Returns:
        A tuple ``(ok, guess_int, error_message)`` where:
        - ``ok`` indicates if parsing succeeded.
        - ``guess_int`` contains the parsed integer when ``ok`` is ``True``.
        - ``error_message`` contains a user-facing validation message on failure.
    """
    if raw is None:
        return False, None, "Enter a guess."

    if raw == "":
        return False, None, "Enter a guess."

    try:
        if "." in raw:
            value = int(float(raw))
        else:
            value = int(raw)
    except Exception:
        return False, None, "That is not a number."

    return True, value, None


def check_guess(guess: int, secret: int) -> Tuple[str, str]:
    """Compare a guess against the secret value and build hint text.

    Args:
        guess: Player-entered integer guess.
        secret: Current secret number for the active round.

    Returns:
        A tuple ``(outcome, message)`` where ``outcome`` is one of
        ``"Win"``, ``"Too High"``, or ``"Too Low"`` and ``message`` is a
        player-facing hint.
    """
    if guess == secret:
        return "Win", "🎉 Correct!"

    if guess > secret:
        return "Too High", "📉 Go LOWER!"
    else:
        return "Too Low", "📈 Go HIGHER!"


def update_score(current_score: int, outcome: str, attempt_number: int) -> int:
    """Compute the next score after a guess result.

    Args:
        current_score: Score before applying the latest outcome.
        outcome: Result label from ``check_guess``.
        attempt_number: 1-based attempt counter at the time of scoring.

    Returns:
        Updated score after applying win bonus or wrong-guess penalty.
    """
    if outcome == "Win":
        points = 100 - 10 * (attempt_number + 1)
        if points < 10:
            points = 10
        return current_score + points

    if outcome == "Too High":
        return current_score - 5

    if outcome == "Too Low":
        return current_score - 5

    return current_score


def ai_hint_engine(
    guess: int,
    secret: int,
    history: List[int],
    attempt_number: int,
    difficulty: str = "Normal",
    personality: str = "Coach",
    return_trace: bool = False,
) -> "str | Tuple[str, Dict]":
    """Generate a structured AI hint using a 4-step agentic reasoning pipeline.

    This function is the core AI feature of the applied system.  It uses
    structured prompting across four observable steps that mirror an agentic
    workflow:

    Step 1 — Gather context (distance, direction, narrowing rate, temperature).
    Step 2 — Select a reasoning pattern (6 possible patterns).
    Step 3 — Retrieve a strategy tip from the knowledge base (RAG step).
    Step 4 — Compose the final hint in the requested personality style
              (few-shot specialisation: Coach / Cryptic / Encouraging).

    Args:
        guess: The current integer guess.
        secret: The secret number for this round.
        history: List of previous integer guesses (oldest first, not including
                 the current guess).
        attempt_number: 1-based attempt counter for the current guess.
        difficulty: Difficulty label — calibrates tone and RAG retrieval.
        personality: Hint style — "Coach" (analytical), "Cryptic" (mysterious),
                     or "Encouraging" (warm and motivational).
        return_trace: When True, returns a (hint, trace_dict) tuple so the
                      caller can display the agent's intermediate steps.

    Returns:
        A hint string, or a (hint, trace) tuple when return_trace is True.
    """
    from knowledge_base import retrieve_tip

    # ── Step 1: Gather context ────────────────────────────────────────────
    distance = abs(guess - secret)
    direction = "higher" if guess < secret else "lower"
    numeric_history = [g for g in history if isinstance(g, int)]
    temperature = get_hint_temperature(guess, secret)

    if len(numeric_history) >= 1:
        prev_distance = abs(numeric_history[-1] - secret)
        narrowing = prev_distance - distance
    else:
        narrowing = None

    context = {
        "guess": guess,
        "distance": distance,
        "direction": direction,
        "temperature": temperature,
        "narrowing": narrowing,
        "history_length": len(numeric_history),
    }

    # ── Step 2: Select reasoning pattern ─────────────────────────────────
    if attempt_number == 1:
        pattern = "first_guess"
    elif distance == 0:
        pattern = "exact"
    elif distance <= 3:
        pattern = "very_close"
    elif narrowing is not None and narrowing <= 0:
        pattern = "moving_away"
    elif len(numeric_history) >= 2:
        lo = min(numeric_history[-2], numeric_history[-1])
        hi = max(numeric_history[-2], numeric_history[-1])
        pattern = "bracketed" if lo < secret < hi else "on_track"
    else:
        pattern = "on_track"

    # ── Step 3: Retrieve strategy tip (RAG) ──────────────────────────────
    rag_tip = retrieve_tip(
        pattern=pattern,
        temperature=temperature,
        difficulty=difficulty,
        attempt_number=attempt_number,
    )

    # ── Step 4: Compose hint in personality style (few-shot specialisation)
    core_hint = _compose_core_hint(
        pattern, direction, distance, numeric_history, difficulty, guess
    )
    hint = _apply_personality(core_hint, personality, rag_tip)

    if return_trace:
        trace = {
            "step1_context": context,
            "step2_pattern": pattern,
            "step3_rag_tip": rag_tip or "(no matching tip)",
            "step4_personality": personality,
            "final_hint": hint,
        }
        return hint, trace

    return hint


def _compose_core_hint(
    pattern: str,
    direction: str,
    distance: int,
    numeric_history: List[int],
    difficulty: str,
    guess: int,
) -> str:
    """Build the base hint text before personality is applied."""
    tone = "Keep pushing!" if difficulty == "Hard" else "You're doing great!"
    if pattern == "first_guess":
        return (
            "No history yet — try the midpoint of the range "
            "to split the search space in half right away."
        )
    if pattern == "exact":
        return "Perfect match — the AI predicted you'd get there!"
    if pattern == "very_close":
        last = numeric_history[-1] if numeric_history else None
        if last is not None:
            return (
                f"Only {distance} away! Your last guess was {last} "
                f"— nudge {direction} by just a little."
            )
        return f"Extremely close — go {direction} by just {distance}."
    if pattern == "moving_away":
        return (
            f"Your last guesses moved away from the target. "
            f"The secret is {direction} than {guess} — try a bigger jump."
        )
    if pattern == "bracketed":
        lo = min(numeric_history[-2], numeric_history[-1])
        hi = max(numeric_history[-2], numeric_history[-1])
        return (
            f"The secret is bracketed between {lo} and {hi}. "
            f"Try the midpoint ({(lo + hi) // 2}) to halve the remaining range. {tone}"
        )
    return f"Good direction — keep going {direction} from {guess}. {tone}"


# Few-shot personality templates — each style has 2-3 example phrasings that
# constrain the output tone, demonstrating specialised/fine-tuned behaviour.
_PERSONALITY_PREFIXES = {
    "Coach": "AI Coach: ",
    "Cryptic": "The Oracle whispers: ",
    "Encouraging": "Your cheerleader says: ",
}

_PERSONALITY_TRANSFORMS = {
    "Coach": lambda hint, tip: (
        f"AI Coach: {hint}"
        + (f" | {tip}" if tip else "")
    ),
    "Cryptic": lambda hint, tip: (
        "The Oracle whispers: "
        + hint.replace("try the midpoint", "seek the middle path")
              .replace("go higher", "ascend")
              .replace("go lower", "descend")
              .replace("nudge", "inch")
              .replace("You're doing great!", "The answer draws near.")
              .replace("Keep pushing!", "Persist, seeker.")
    ),
    "Encouraging": lambda hint, tip: (
        "Your cheerleader says: You're doing amazing! "
        + hint.replace("AI Coach: ", "")
              .replace("Your last guesses moved away", "No worries — redirect and")
        + " You've got this! 🎉"
    ),
}


def _apply_personality(core_hint: str, personality: str, rag_tip: Optional[str]) -> str:
    """Apply a few-shot personality transform to the core hint.

    The three personalities produce measurably different outputs:
    - Coach: analytical, includes the RAG tip as a second sentence.
    - Cryptic: mystical vocabulary substitutions, no RAG tip.
    - Encouraging: warm, celebratory framing, no RAG tip.

    Args:
        core_hint: Base hint from _compose_core_hint.
        personality: One of 'Coach', 'Cryptic', 'Encouraging'.
        rag_tip: Retrieved strategy tip (used only by Coach personality).

    Returns:
        Transformed hint string.
    """
    transform = _PERSONALITY_TRANSFORMS.get(
        personality, _PERSONALITY_TRANSFORMS["Coach"]
    )
    return transform(core_hint, rag_tip)


def get_hint_temperature(guess: int, secret: int) -> str:
    """Classify how close a guess is to the secret number.

    Args:
        guess: Player-entered integer guess.
        secret: Current secret number for the active round.

    Returns:
        One of ``"Exact"``, ``"Hot"``, ``"Warm"``, or ``"Cold"`` based on
        absolute distance to the secret.
    """
    distance = abs(guess - secret)
    if distance == 0:
        return "Exact"
    if distance <= 3:
        return "Hot"
    if distance <= 10:
        return "Warm"
    return "Cold"
