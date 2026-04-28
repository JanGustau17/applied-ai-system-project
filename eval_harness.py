"""
eval_harness.py — Test Harness and Evaluation Script (Stretch Feature 4)

Evaluates the full Game Glitch Investigator AI system on a suite of 20
predefined game scenarios.  Each scenario specifies a guess, secret,
history, and expected outcomes for check_guess, update_score, and the
ai_hint_engine reasoning pattern.

Run from the project root:
    python eval_harness.py

Output: a structured pass/fail report with confidence scores and a
system-level summary line.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from logic_utils import (
    check_guess,
    update_score,
    parse_guess,
    get_hint_temperature,
    ai_hint_engine,
)

# ── Scenario definitions ──────────────────────────────────────────────────────
# Each scenario is a dict with:
#   guess, secret, history, attempt_number, difficulty
#   expected_outcome   — "Win" | "Too High" | "Too Low"
#   expected_pattern   — substring expected in the ai_hint_engine output
#   expected_score_delta — change from score 100 after one call to update_score
#   description        — human-readable label

SCENARIOS = [
    # ── Basic game logic ──────────────────────────────────────────────────
    {
        "description": "Correct guess on attempt 1",
        "guess": 50, "secret": 50, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_outcome": "Win",
        "expected_pattern": "midpoint",  # attempt_number==1 → first_guess pattern
        "expected_score_delta": +80,  # 100 - 10*(1+1) = 80
    },
    {
        "description": "Guess too high",
        "guess": 80, "secret": 50, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_outcome": "Too High",
        "expected_pattern": "midpoint",
        "expected_score_delta": -5,
    },
    {
        "description": "Guess too low",
        "guess": 20, "secret": 50, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_outcome": "Too Low",
        "expected_pattern": "midpoint",
        "expected_score_delta": -5,
    },
    # ── Hint direction correctness ────────────────────────────────────────
    {
        "description": "Too low hint says HIGHER",
        "guess": 1, "secret": 99, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_outcome": "Too Low",
        "expected_pattern": "midpoint",
        "expected_score_delta": -5,
        "check_hint_direction": "HIGHER",
    },
    {
        "description": "Too high hint says LOWER",
        "guess": 99, "secret": 1, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_outcome": "Too High",
        "expected_pattern": "midpoint",
        "expected_score_delta": -5,
        "check_hint_direction": "LOWER",
    },
    # ── AI pattern: first guess ───────────────────────────────────────────
    {
        "description": "AI pattern: first_guess → midpoint advice",
        "guess": 30, "secret": 70, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_outcome": "Too Low",
        "expected_pattern": "midpoint",
        "expected_score_delta": -5,
    },
    # ── AI pattern: very_close ────────────────────────────────────────────
    {
        "description": "AI pattern: very_close → nudge hint",
        "guess": 48, "secret": 50, "history": [30], "attempt_number": 2,
        "difficulty": "Normal",
        "expected_outcome": "Too Low",
        "expected_pattern": "nudge",
        "expected_score_delta": -5,
    },
    # ── AI pattern: bracketed ─────────────────────────────────────────────
    {
        "description": "AI pattern: bracketed → midpoint suggestion",
        "guess": 30, "secret": 60, "history": [20, 80], "attempt_number": 3,
        "difficulty": "Normal",
        "expected_outcome": "Too Low",
        "expected_pattern": "bracket",
        "expected_score_delta": -5,
    },
    # ── AI pattern: moving_away ───────────────────────────────────────────
    {
        "description": "AI pattern: moving_away → course-correct",
        "guess": 20, "secret": 90, "history": [50], "attempt_number": 2,
        "difficulty": "Normal",
        "expected_outcome": "Too Low",
        "expected_pattern": "away",
        "expected_score_delta": -5,
    },
    # ── AI pattern: exact ─────────────────────────────────────────────────
    {
        "description": "AI pattern: exact → celebration",
        "guess": 75, "secret": 75, "history": [50, 100], "attempt_number": 3,
        "difficulty": "Normal",
        "expected_outcome": "Win",
        "expected_pattern": "predicted",
        "expected_score_delta": +60,  # 100 - 10*(3+1) = 60
    },
    # ── Guardrail: parse_guess ────────────────────────────────────────────
    {
        "description": "Guardrail: rejects non-numeric input",
        "guess_raw": "hello", "secret": 50, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_parse_ok": False,
        "expected_outcome": None,
        "expected_pattern": None,
        "expected_score_delta": 0,
    },
    {
        "description": "Guardrail: rejects empty input",
        "guess_raw": "", "secret": 50, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_parse_ok": False,
        "expected_outcome": None,
        "expected_pattern": None,
        "expected_score_delta": 0,
    },
    {
        "description": "Guardrail: accepts float string as int",
        "guess_raw": "47.9", "secret": 50, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_parse_ok": True,
        "expected_outcome": "Too Low",
        "expected_pattern": "midpoint",
        "expected_score_delta": -5,
    },
    # ── Difficulty ranges ─────────────────────────────────────────────────
    {
        "description": "Hard difficulty: AI pattern with Hard tone",
        "guess": 100, "secret": 150, "history": [], "attempt_number": 1,
        "difficulty": "Hard",
        "expected_outcome": "Too Low",
        "expected_pattern": "midpoint",
        "expected_score_delta": -5,
    },
    {
        "description": "Easy difficulty: on_track hint",
        "guess": 12, "secret": 18, "history": [5], "attempt_number": 2,
        "difficulty": "Easy",
        "expected_outcome": "Too Low",
        "expected_pattern": "higher",
        "expected_score_delta": -5,
    },
    # ── Personality modes ─────────────────────────────────────────────────
    {
        "description": "Personality Coach: includes 'AI Coach:' prefix",
        "guess": 50, "secret": 80, "history": [], "attempt_number": 1,
        "difficulty": "Normal", "personality": "Coach",
        "expected_outcome": "Too Low",
        "expected_pattern": "AI Coach",
        "expected_score_delta": -5,
    },
    {
        "description": "Personality Cryptic: includes oracle phrasing",
        "guess": 50, "secret": 80, "history": [], "attempt_number": 1,
        "difficulty": "Normal", "personality": "Cryptic",
        "expected_outcome": "Too Low",
        "expected_pattern": "Oracle",
        "expected_score_delta": -5,
    },
    {
        "description": "Personality Encouraging: includes cheerleader phrasing",
        "guess": 50, "secret": 80, "history": [], "attempt_number": 1,
        "difficulty": "Normal", "personality": "Encouraging",
        "expected_outcome": "Too Low",
        "expected_pattern": "cheerleader",
        "expected_score_delta": -5,
    },
    # ── RAG retrieval ─────────────────────────────────────────────────────
    {
        "description": "RAG: trace shows a retrieved tip (not 'no matching tip')",
        "guess": 100, "secret": 150, "history": [], "attempt_number": 1,
        "difficulty": "Hard",
        "expected_outcome": "Too Low",
        "expected_pattern": "midpoint",
        "expected_score_delta": -5,
        "check_rag_tip": True,
    },
    # ── Lexicographic regression ──────────────────────────────────────────
    {
        "description": "Regression: 9 < 50 must be Too Low (not lexicographic Too High)",
        "guess": 9, "secret": 50, "history": [], "attempt_number": 1,
        "difficulty": "Normal",
        "expected_outcome": "Too Low",
        "expected_pattern": "midpoint",
        "expected_score_delta": -5,
    },
]


# ── Evaluation runner ─────────────────────────────────────────────────────────

def run_scenario(scenario: dict) -> dict:
    """Run one scenario through the full system and return a result dict."""
    result = {
        "description": scenario["description"],
        "checks": [],
        "passed": True,
    }

    personality = scenario.get("personality", "Coach")

    # Handle raw-input guardrail scenarios
    if "guess_raw" in scenario:
        ok, guess_int, err = parse_guess(scenario["guess_raw"])
        expected_ok = scenario.get("expected_parse_ok", True)
        check_result = ok == expected_ok
        result["checks"].append({
            "name": "parse_guess ok",
            "passed": check_result,
            "got": ok,
            "expected": expected_ok,
        })
        if not check_result:
            result["passed"] = False
        if not ok:
            return result
    else:
        guess_int = scenario["guess"]

    secret = scenario["secret"]
    history = scenario["history"]
    attempt_number = scenario["attempt_number"]
    difficulty = scenario["difficulty"]

    # check_guess
    if scenario.get("expected_outcome") is not None:
        outcome, hint_msg = check_guess(guess_int, secret)
        check_result = outcome == scenario["expected_outcome"]
        result["checks"].append({
            "name": "check_guess outcome",
            "passed": check_result,
            "got": outcome,
            "expected": scenario["expected_outcome"],
        })
        if not check_result:
            result["passed"] = False

        # Optional: hint direction
        if "check_hint_direction" in scenario:
            direction_ok = scenario["check_hint_direction"] in hint_msg.upper()
            result["checks"].append({
                "name": "hint direction",
                "passed": direction_ok,
                "got": hint_msg,
                "expected": f"contains '{scenario['check_hint_direction']}'",
            })
            if not direction_ok:
                result["passed"] = False

    # update_score
    if scenario.get("expected_score_delta") is not None and scenario.get("expected_outcome"):
        new_score = update_score(100, scenario["expected_outcome"], attempt_number)
        delta = new_score - 100
        check_result = delta == scenario["expected_score_delta"]
        result["checks"].append({
            "name": "score delta",
            "passed": check_result,
            "got": delta,
            "expected": scenario["expected_score_delta"],
        })
        if not check_result:
            result["passed"] = False

    # ai_hint_engine
    if scenario.get("expected_pattern") is not None:
        hint, trace = ai_hint_engine(
            guess=guess_int,
            secret=secret,
            history=history,
            attempt_number=attempt_number,
            difficulty=difficulty,
            personality=personality,
            return_trace=True,
        )
        pattern_ok = scenario["expected_pattern"].lower() in hint.lower()
        result["checks"].append({
            "name": "ai hint pattern",
            "passed": pattern_ok,
            "got": hint[:80] + ("..." if len(hint) > 80 else ""),
            "expected": f"contains '{scenario['expected_pattern']}'",
        })
        if not pattern_ok:
            result["passed"] = False

        # Optional: RAG tip check
        if scenario.get("check_rag_tip"):
            rag_tip = trace.get("step3_rag_tip", "")
            rag_ok = "no matching tip" not in rag_tip.lower()
            result["checks"].append({
                "name": "RAG tip retrieved",
                "passed": rag_ok,
                "got": rag_tip[:80] if rag_ok else "(no matching tip)",
                "expected": "a non-empty strategy tip",
            })
            if not rag_ok:
                result["passed"] = False

    return result


def print_report(results: list) -> None:
    """Print a structured pass/fail evaluation report."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    confidence = passed / total if total > 0 else 0.0

    print()
    print("=" * 70)
    print("  GAME GLITCH INVESTIGATOR — AI SYSTEM EVALUATION REPORT")
    print("=" * 70)
    print()

    for i, r in enumerate(results, 1):
        status = "PASS" if r["passed"] else "FAIL"
        icon = "✓" if r["passed"] else "✗"
        print(f"  [{icon}] #{i:02d} {status}  {r['description']}")
        if not r["passed"]:
            for c in r["checks"]:
                if not c["passed"]:
                    print(f"        ↳ {c['name']}: got={c['got']}  expected={c['expected']}")

    print()
    print("-" * 70)
    print(f"  Results:    {passed}/{total} passed  |  {failed} failed")
    print(f"  Confidence: {confidence:.1%}")
    if confidence == 1.0:
        print("  Status:     ALL SYSTEMS NOMINAL")
    elif confidence >= 0.9:
        print("  Status:     MINOR ISSUES — review failed cases above")
    else:
        print("  Status:     ATTENTION REQUIRED — significant failures detected")
    print("=" * 70)
    print()


if __name__ == "__main__":
    results = [run_scenario(s) for s in SCENARIOS]
    print_report(results)
    sys.exit(0 if all(r["passed"] for r in results) else 1)
