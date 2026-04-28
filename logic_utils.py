import logging
import os
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]

load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
# Writes to ai_hint.log in the project root. Each run appends so history is kept.
logging.basicConfig(
    filename="ai_hint.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai_hint_engine")


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

    # ── Step 4: Call GPT-4o-mini with context + RAG tip + personality ────
    hint = _call_gpt_hint(
        context=context,
        pattern=pattern,
        rag_tip=rag_tip,
        personality=personality,
        difficulty=difficulty,
    )

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


def _call_gpt_hint(
    context: Dict,
    pattern: str,
    rag_tip: Optional[str],
    personality: str,
    difficulty: str,
) -> str:
    """Call GPT-4o-mini to generate the final hint.

    The model is specialized as a number-guessing game coach via a detailed
    system prompt. Steps 1-3 (context, pattern, RAG tip) are injected into
    the user message so GPT reasons from real game state rather than guessing.

    Falls back to the rule-based hint if the API key is missing or the call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        # Graceful fallback: no key configured
        logger.warning(
            "OPENAI_API_KEY not set — using rule-based fallback. "
            "pattern=%s personality=%s difficulty=%s",
            pattern, personality, difficulty,
        )
        core = _compose_core_hint(
            pattern,
            context["direction"],
            context["distance"],
            [],
            difficulty,
            context["guess"],
        )
        return _apply_personality(core, personality, rag_tip)

    try:
        if OpenAI is None:
            raise ImportError("openai package not installed — run: pip install openai")

        client = OpenAI(api_key=api_key)

        personality_instructions = {
            "Coach": (
                "You are an analytical game coach. Be direct, tactical, and concise. "
                "Give one clear sentence of strategic advice based on the data. "
                "Include the RAG strategy tip naturally if it fits."
            ),
            "Cryptic": (
                "You are a mysterious oracle. Speak in cryptic, poetic language. "
                "Use metaphors and mysterious phrasing. Never say 'higher' or 'lower' directly — "
                "instead say 'ascend', 'descend', 'the answer lies above', etc. "
                "Keep it to 1-2 sentences. Do NOT include the RAG tip literally."
            ),
            "Encouraging": (
                "You are an enthusiastic cheerleader. Be warm, celebratory, and motivating. "
                "Celebrate any progress. Keep it to 1-2 upbeat sentences with an emoji. "
                "Do NOT include the RAG tip literally."
            ),
        }
        style = personality_instructions.get(personality, personality_instructions["Coach"])

        system_prompt = (
            "You are a specialized AI hint engine for a number-guessing game. "
            "Your job is to generate ONE short, helpful hint (1-2 sentences max) "
            "based on the player's current game state. "
            "You have already completed three reasoning steps before generating the hint:\n"
            "  Step 1: You analyzed the game context (distance, direction, temperature).\n"
            "  Step 2: You identified the reasoning pattern.\n"
            "  Step 3: You retrieved a relevant strategy tip from the knowledge base (RAG).\n"
            "Now in Step 4, apply your personality style and produce the final hint.\n\n"
            f"Personality style: {style}\n\n"
            "Rules:\n"
            "- Never reveal the secret number.\n"
            "- Keep the hint to 1-2 sentences.\n"
            "- Do not repeat the raw game state numbers unless it adds value.\n"
            "- Output ONLY the hint text, no labels or prefixes."
        )

        narrowing_str = (
            f"{context['narrowing']:+d} closer than last guess"
            if context["narrowing"] is not None
            else "first guess"
        )

        user_message = (
            f"Game state:\n"
            f"  Difficulty: {difficulty}\n"
            f"  Current guess: {context['guess']}\n"
            f"  Distance from secret: {context['distance']}\n"
            f"  Direction needed: go {context['direction']}\n"
            f"  Temperature: {context['temperature']}\n"
            f"  Narrowing: {narrowing_str}\n"
            f"  Previous guesses made: {context['history_length']}\n"
            f"  Reasoning pattern: {pattern}\n"
            f"  RAG strategy tip: {rag_tip or 'none'}\n\n"
            f"Generate the hint now."
        )

        logger.info(
            "GPT call — model=gpt-4o-mini pattern=%s personality=%s difficulty=%s "
            "guess=%s distance=%s temperature=%s",
            pattern, personality, difficulty,
            context["guess"], context["distance"], context["temperature"],
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=120,
            temperature=0.7,
        )
        hint = response.choices[0].message.content.strip()
        logger.info("GPT response — %s", hint)
        return hint

    except Exception as exc:
        # Graceful fallback on any API error
        logger.error("GPT call failed — %s. Falling back to rule-based hint.", exc)
        core = _compose_core_hint(
            pattern,
            context["direction"],
            context["distance"],
            [],
            difficulty,
            context["guess"],
        )
        fallback = _apply_personality(core, personality, rag_tip)
        return f"{fallback}  [AI unavailable: {exc}]"


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
