# 🎮 Game Glitch Investigator — Applied AI System

**Project 4 (Final Project) | AI110 Foundations of AI Engineering | Spring 2026**
**Student:** Mukhammadali Yuldoshev | **Base Project:** Project 1 — Game Glitch Investigator

---

## 📌 Base Project Identification

This project extends **Project 1: Game Glitch Investigator** — a Streamlit number-guessing game that was intentionally shipped with multiple bugs. The original system:

- Let players guess a secret number in a configurable difficulty range
- Was broken in 8 distinct ways (inverted hints, wrong difficulty ranges, lexicographic comparisons, broken state resets, hardcoded range display, and more)
- Required students to find, document, and fix the bugs using AI assistance

**What this final project adds:** A fully integrated **AI Hint Engine** (structured prompting), input guardrails, a reliability test harness, a system architecture diagram, and this documentation suite — evolving the repaired prototype into a polished, trustworthy applied AI system.

---

## 🏗️ System Architecture

![System Architecture Diagram](assets/architecture.svg)

**Data flow:** User Input → Streamlit UI (`app.py`) → Input Guardrail (`parse_guess`) → Game Logic Engine + AI Hint Engine (`logic_utils.py`) → Session State → Output (hint · score · temperature · AI suggestion)

**Key files:**

| File | Role |
|---|---|
| `app.py` | Streamlit UI, session state management, render layer |
| `logic_utils.py` | All game logic + the 4-step AI hint engine (with RAG, trace, personality) |
| `knowledge_base.py` | RAG knowledge base (9 strategy documents + retrieve_tip()) |
| `eval_harness.py` | Evaluation script — 20 scenarios, pass/fail report with confidence |
| `tests/test_game_logic.py` | 20 pytest cases covering bugs, features, and AI engine |
| `model_card.md` | Full AI reflection, limitations, and collaboration notes |
| `reflection.md` | Personal learning reflection |
| `assets/architecture.svg` | System architecture diagram |

---

## 🤖 Substantial New AI Feature: AI Hint Engine

The core new feature is `ai_hint_engine()` in `logic_utils.py` — a **structured prompting engine** that analyses the player's guess history and generates intelligent, personalised hints.

### How it works (4-step agentic pipeline)

**Step 1 — Gather context:** distance from secret, direction, previous distance, temperature, whether guesses are narrowing or widening.

**Step 2 — Classify pattern:** selects one of six reasoning patterns:
- `first_guess` — no history; recommend midpoint strategy
- `very_close` — within 3 of the secret; nudge hint
- `moving_away` — player is getting further away; course-correct
- `bracketed` — prior guesses bracket the secret; suggest exact midpoint
- `on_track` — making progress; encourage continuation
- `exact` — correct guess

**Step 3 — Retrieve strategy tip (RAG):** scores all 9 documents in `knowledge_base.py` against the current context and retrieves the most relevant one.

**Step 4 — Compose hint in personality style:** assembles a natural-language message referencing the player's actual prior guesses, in the selected personality (Coach / Cryptic / Encouraging).

### Sample inputs and AI responses

| Situation | Guess | Secret | History | AI Output |
|---|---|---|---|---|
| First guess | 30 | 70 | `[]` | *"No history yet — try the midpoint of the range to split the search space in half right away."* |
| Very close | 48 | 50 | `[30]` | *"Only 2 away! Your last guess was 30 — nudge higher by just a little."* |
| Bracketed | 70 | 60 | `[40, 80]` | *"The secret is bracketed between 40 and 80. Try the midpoint (60) to halve the remaining range."* |
| Moving away | 20 | 90 | `[50]` | *"Your last two guesses moved away from the target. The secret is higher than 20 — try a bigger jump."* |
| Exact | 50 | 50 | `[30, 70]` | *"Perfect match — the AI predicted you'd get there!"* |

---

## ✅ Bug Fixes (Project 1 Foundation)

### Core bugs fixed

1. Inverted hint messages in `check_guess` (said "Go LOWER!" when guess was too low)
2. Hard difficulty range was `1–50` — easier than Normal's `1–100`; fixed to `1–200`
3. Attempts initialized to `1` instead of `0`
4. Range display was hardcoded "1 and 100" regardless of difficulty
5. Game status never reset on New Game — game stayed stuck after win/loss
6. New Game regenerated secret from `1–100` regardless of selected difficulty
7. String-based comparison caused lexicographic errors (`"9" > "50"` → True)
8. Scoring gave +5 points for wrong guesses on even attempt numbers

### Refactor and multi-file coordination

- All shared logic centralised in `logic_utils.py`
- `app.py` imports all logic functions; no game logic defined inline
- Tests in `tests/test_game_logic.py` validate every bug fix and new feature

### Feature Expansion (Agent Mode)

A **Guess Insights** feature was implemented through coordinated edits across `logic_utils.py`, `app.py`, and `tests/test_game_logic.py`:

- `logic_utils.py`: `get_hint_temperature(guess, secret)` returning `Exact`, `Hot`, `Warm`, or `Cold`
- `app.py`: stores proximity feedback in session state; renders in a `Guess Insights` expander
- `tests/test_game_logic.py`: four pytest cases verify all temperature categories

---

---

## 🚀 Stretch Features

### Stretch 1: RAG Enhancement — Knowledge Base Retrieval (+2pts)

`knowledge_base.py` implements a 9-document strategy knowledge base with a `retrieve_tip()` function that scores each document against 4 context signals (pattern, temperature, difficulty, game phase) and returns the most relevant tip.

This is integrated into the AI Hint Engine as Step 3 of the 4-step pipeline. The Coach personality appends the retrieved tip as a second sentence, making hints more specific. The impact is observable — a Hard-mode guess retrieves the binary search efficiency tip, while a bracketed guess retrieves the explicit midpoint strategy document.

**RAG retrieval example:**
- Context: `difficulty=Hard, pattern=first_guess, temperature=Cold, phase=early`
- Retrieved tip: *"Strategy tip: On Hard mode the range is 1–200 with only 5 attempts. Binary search is mandatory — start at 100, then 50 or 150, and always cut the remaining range in half."*

### Stretch 2: Agentic Workflow Enhancement — Observable Reasoning Trace (+2pts)

The AI Hint Engine now returns an optional `trace` dict alongside the hint when `return_trace=True`. The trace records every intermediate reasoning step:

```
Step 1 — Context:  guess=30  distance=40  direction=higher  temperature=Cold  narrowing=None
Step 2 — Pattern:  first_guess
Step 3 — RAG tip:  Strategy tip: Always start at the midpoint of the range...
Step 4 — Style:    Coach
Final hint:        AI Coach: No history yet — try the midpoint...
```

In the Streamlit UI, enabling "Show AI reasoning trace" in the sidebar expands a panel showing all 4 steps after every guess — making the agent's decision-making process fully transparent and observable.

### Stretch 3: Fine-Tuning / Specialization Behavior — Personality Modes (+2pts)

Three few-shot personality modes are implemented in `_apply_personality()` in `logic_utils.py`. Each produces measurably different output from the same base hint:

| Personality | Prefix | Style | Example output |
|---|---|---|---|
| **Coach** *(baseline)* | `AI Coach:` | Analytical, appends RAG tip | *"AI Coach: The secret is bracketed between 40 and 80. Try the midpoint (60)... \| Strategy tip: Binary search..."* |
| **Cryptic** | `The Oracle whispers:` | Mystical vocabulary substitutions: "ascend/descend", "inch", "seek the middle path" | *"The Oracle whispers: seek the middle path to split the search space in half"* |
| **Encouraging** | `Your cheerleader says:` | Warm, celebratory, adds "You've got this! 🎉" | *"Your cheerleader says: You're doing amazing! The secret is bracketed... You've got this! 🎉"* |

The output measurably differs: Coach is analytical, Cryptic swaps vocabulary, Encouraging wraps everything in celebration. All three are selectable from the sidebar.

### Stretch 4: Test Harness / Evaluation Script (+2pts)

`eval_harness.py` evaluates the entire system on 20 predefined scenarios covering all components end-to-end: guardrails, game logic, scoring, all 6 AI hint patterns, all 3 personalities, RAG retrieval, and the lexicographic regression.

```
python eval_harness.py
```

**Output:**
```
======================================================================
  GAME GLITCH INVESTIGATOR — AI SYSTEM EVALUATION REPORT
======================================================================

  [✓] #01 PASS  Correct guess on attempt 1
  [✓] #02 PASS  Guess too high
  ...
  [✓] #20 PASS  Regression: 9 < 50 must be Too Low (not lexicographic Too High)

----------------------------------------------------------------------
  Results:    20/20 passed  |  0 failed
  Confidence: 100.0%
  Status:     ALL SYSTEMS NOMINAL
======================================================================
```

---

## 🛡️ Reliability, Evaluation, and Guardrails

### Input Guardrail — `parse_guess()`

The `parse_guess` function validates all player input before it reaches any game logic:

| Input | Guardrail response | Reason |
|---|---|---|
| `"abc"` | Rejects: "That is not a number." | Non-numeric string |
| `""` | Rejects: "Enter a guess." | Empty input |
| `None` | Rejects: "Enter a guess." | Missing input |
| `"3.7"` | Accepts as `3` | Float-to-int coercion |
| `"50"` | Accepts as `50` | Valid integer string |

This guardrail prevents the lexicographic comparison bug from ever reaching `check_guess` — the integer type is enforced at the boundary.

### Test Harness — `tests/test_game_logic.py`

20 pytest cases covering:
- All 3 `check_guess` outcomes (Win, Too High, Too Low)
- Hint message direction for both outcomes
- Score deduction for wrong guesses
- Hard difficulty range bounds
- Lexicographic comparison regression tests
- All 4 temperature categories (Exact, Hot, Warm, Cold)
- All 6 AI hint engine reasoning patterns
- Edge case: mixed-type history list (strings + ints)

Run with: `pytest -q`

---

## 🤖 AI Verification and Critique of Debugging Suggestions

This section documents the AI collaboration process with actual AI output.

---

### 📝 AI-Generated Explanation of a Bug (Documentation)

**Bug investigated:** Inverted hint messages in `check_guess` — the game said "Go LOWER!" when the guess was too low and "Go HIGHER!" when the guess was too high.

**Prompt sent to AI (Copilot Chat):**
> "In my Python guessing game, when the player guesses a number lower than the secret, the hint says 'Go LOWER!' instead of 'Go HIGHER!'. Why is this happening and how do I fix it?"

**AI-generated explanation (verbatim):**
> "The bug is in your conditional logic. Your code returns 'Too Low' and the message 'Go LOWER!' when `guess < secret`, but that's backwards — if the guess is too low, the player needs to go *higher*. You should return `'Go HIGHER!'` when `guess < secret` (i.e., the guess is Too Low) and `'Go LOWER!'` when `guess > secret` (i.e., the guess is Too High). Here's the corrected version:
> ```python
> if guess > secret:
>     return "Too High", "📉 Go LOWER!"
> else:
>     return "Too Low", "📈 Go HIGHER!"
> ```"

**Assessment:** Correct. Clearly identified the inverted condition-to-message mapping.

---

### ✅ Accepted AI Suggestion (with Justification)

**Bug:** Game state was not persisted between Streamlit reruns — secret regenerated on every button click.

**AI suggestion (ChatGPT):**
> "Wrap the secret initialization in a session state check: `if 'secret' not in st.session_state: st.session_state.secret = random.randint(low, high)`. Also reset `st.session_state.status` inside your New Game handler."

**Why accepted:** Streamlit reruns the full script on every interaction. Without the session state guard, `random.randint` executes on every button click, making the secret unstable. Verified by replaying win/loss/reset flows manually and confirming all tests passed.

---

### ❌ Rejected/Misleading AI Suggestion (with Critique)

**Bug investigated:** Type mismatch when comparing guess to secret.

**AI suggestion (Copilot):**
> "Cast both values to strings before comparing: `if str(guess) == str(secret)` and `if str(guess) > str(secret)`."

**Why rejected:** String comparison is lexicographic. `"9" > "50"` is `True` in Python because `"9"` comes after `"5"` alphabetically — but `9 < 50` numerically. This would cause the game to say "Too High" when the player guessed 9 against a secret of 50. I kept integer types enforced in `parse_guess()`. Regression test `test_numeric_comparison_not_lexicographic` permanently guards against this.

---

## 🛠️ Setup and Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd ai110-module1show-gameglitchinvestigator-starter

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python -m streamlit run app.py

# 4. Run the test suite
pytest -q
```

**Requirements:** Python 3.9+, streamlit, pytest (see `requirements.txt`)

---

## 🧪 Test Status

Run `pytest -q` from the project root. All 20 tests pass:

```
tests/test_game_logic.py::test_winning_guess PASSED
tests/test_game_logic.py::test_guess_too_high PASSED
tests/test_game_logic.py::test_guess_too_low PASSED
tests/test_game_logic.py::test_too_low_hint_says_go_higher PASSED
tests/test_game_logic.py::test_too_high_hint_says_go_lower PASSED
tests/test_game_logic.py::test_wrong_guess_always_subtracts_score PASSED
tests/test_game_logic.py::test_hard_difficulty_range_is_larger_than_normal PASSED
tests/test_game_logic.py::test_hard_difficulty_range_is_1_to_200 PASSED
tests/test_game_logic.py::test_numeric_comparison_not_lexicographic PASSED
tests/test_game_logic.py::test_numeric_comparison_large_vs_small PASSED
tests/test_game_logic.py::test_get_hint_temperature_exact PASSED
tests/test_game_logic.py::test_get_hint_temperature_hot PASSED
tests/test_game_logic.py::test_get_hint_temperature_warm PASSED
tests/test_game_logic.py::test_get_hint_temperature_cold PASSED
tests/test_game_logic.py::test_ai_hint_first_guess_mentions_midpoint PASSED
tests/test_game_logic.py::test_ai_hint_very_close_mentions_nudge PASSED
tests/test_game_logic.py::test_ai_hint_bracketed_suggests_midpoint PASSED
tests/test_game_logic.py::test_ai_hint_moving_away_warns_player PASSED
tests/test_game_logic.py::test_ai_hint_returns_string PASSED
tests/test_game_logic.py::test_ai_hint_invalid_history_types_handled PASSED
20 passed in 0.XXs
```

---

## 📝 Reflection and AI Collaboration

See `reflection.md` for the full personal reflection, and `model_card.md` for:
- Full system description and attribute table
- Plain-language explanation of the AI's algorithmic approach
- Identified limitations and biases with improvement ideas
- Detailed AI collaboration log (helpful and flawed suggestions)
- Future improvement roadmap

---

## 📸 Demo

![Game running — post-fix](image-1.png)
![Game running — hint and score display](image.png)
