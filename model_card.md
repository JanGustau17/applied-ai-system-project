# Model Card — Game Glitch Investigator (Applied AI System)

## 1. System Overview

**Base project:** Project 1 — Game Glitch Investigator (Module 1)
**Original goal:** A Streamlit number-guessing game intentionally filled with bugs (inverted hints, wrong difficulty ranges, lexicographic comparisons, broken state). The assignment was to find, document, and fix those bugs using AI assistance.
**Extended into (Project 4):** A full applied AI system that adds a structured-prompting AI Hint Engine on top of the fixed game, plus input guardrails, a reliability test suite, and this model card.

---

## 2. System Description and Attributes

The system has no external model API. The "AI" component is implemented as a **structured prompting engine** (`ai_hint_engine` in `logic_utils.py`) that:

- Gathers context: current guess, secret distance, direction, guess history, attempt number, difficulty level
- Runs a multi-step reasoning pattern selector (first_guess / very_close / moving_away / bracketed / on_track / exact)
- Composes a natural-language hint that references the player's actual prior guesses

**Inputs used by the AI component:**

| Attribute | Type | Purpose |
|---|---|---|
| `guess` | int | The player's current guess |
| `secret` | int | The hidden target number |
| `history` | list[int] | All previous integer guesses this round |
| `attempt_number` | int | How many guesses have been made |
| `difficulty` | str | Easy / Normal / Hard — tunes encouragement tone |

**Output:** A single natural-language hint string rendered in the Streamlit UI as an info box.

---

## 3. Algorithmic Approach (Plain Language)

The AI hint engine works like a small decision tree with memory:

1. It first checks whether there is any guess history at all. If this is the first guess, it always suggests the binary search midpoint strategy — this is the mathematically optimal first move.
2. If the current guess is within 3 of the secret, it switches to a "very close" pattern and tells the player exactly how far they are and in which direction to nudge.
3. If the player's guesses are moving *further* from the secret (not closer), it detects this using the previous distance minus the current distance, flags it as "moving away," and tells the player to make a bigger jump.
4. If two previous guesses bracket the secret (one above, one below), it detects the bracket and suggests the exact midpoint of those two guesses — essentially teaching the binary search strategy.
5. Otherwise, it falls back to an encouraging on-track message.

This is a rule-based reasoning system that mimics structured prompting: rather than sending a prompt to a language model, it follows a deterministic prompt-like flow where each "step" narrows down the response type before composing the output.

---

## 4. Limitations and Biases

**Small reasoning space:** The engine only looks at the most recent guess for distance comparison and the most recent two guesses for bracket detection. A player making a complex zig-zag pattern might not get the most useful advice.

**No real learning:** The system does not adapt based on whether the player followed previous hints. It treats every turn as stateless except for the history list passed in.

**Difficulty tone is minimal:** Hard difficulty only changes the encouragement phrase ("Keep pushing!" vs "You're doing great!"), not the actual strategy advice. A more sophisticated system might adjust the binary search threshold based on the difficulty range.

**Numeric input only:** The guardrail (`parse_guess`) rejects non-numeric input entirely rather than trying to interpret natural language like "fifty" or "about 70". This is intentional for correctness but limits accessibility.

**Improvement ideas:**
- Add a streak detector: if the player has guessed the same number multiple times, explicitly warn them.
- Widen the history window to detect oscillation patterns (guessing above and below alternately without converging).
- For Hard difficulty, suggest a tighter midpoint bracket (e.g., binary search with ±5 tolerance).

---

## 5. AI Collaboration During Development

**How AI was used:**

I used Copilot Chat and ChatGPT at three stages: (a) explaining why bugs existed in the starter code, (b) suggesting fixes for Streamlit session state, and (c) helping me think through the structure of the hint engine's reasoning patterns.

**Helpful AI suggestion (accepted):**
When I asked ChatGPT how to design the hint engine, it suggested: *"Think of it like a structured prompt chain: first gather context, then classify the situation, then compose the output. Each step should depend only on the outputs of prior steps."* This framing directly shaped the three-step architecture of `ai_hint_engine` (context → pattern → composition).

**Flawed AI suggestion (rejected):**
Copilot suggested I compare guess and secret as strings to handle potential type mismatches. This was incorrect because Python string comparison is lexicographic: `"9" > "50"` evaluates to `True` even though `9 < 50`. I rejected this and instead enforced integer types at the parse stage via `parse_guess()`. A regression test (`test_numeric_comparison_not_lexicographic`) was added to permanently catch this class of bug.

**Verification approach:**
Every AI suggestion was tested before being committed. For bug fixes: I confirmed tests failed before the fix and passed after. For the hint engine: I ran manual spot-checks covering all six reasoning patterns and wrote six pytest cases verifying the expected pattern triggers.

---

## 6. Stretch Feature Documentation

### RAG Knowledge Base (`knowledge_base.py`)

The RAG retrieval component uses a 9-document corpus indexed by semantic tags. The `retrieve_tip()` function computes a relevance score by counting tag overlaps between each document and the current context (pattern, temperature, difficulty, game phase). The highest-scoring document is returned and appended to Coach-mode hints.

**Impact demonstration:** Switching from Normal to Hard retrieves a different document (binary search efficiency vs. general midpoint advice), and a bracketed pattern retrieves the explicit bracket-midpoint strategy, not the general direction tip. This is observable in the agentic trace under Step 3.

### Agentic Workflow (`return_trace=True`)

The `ai_hint_engine` function exposes its full reasoning chain via `return_trace=True`. The trace dict contains: `step1_context` (6 computed variables), `step2_pattern` (selected pattern label), `step3_rag_tip` (retrieved document text), `step4_personality` (style applied), and `final_hint` (composed output). This makes the agent's decision-making fully observable and auditable.

### Personality Modes (Few-Shot Specialisation)

The `_PERSONALITY_TRANSFORMS` dict in `logic_utils.py` implements three few-shot styles as lambda functions. Coach is the baseline analytical style. Cryptic applies vocabulary substitutions ("ascend" for "go higher", "seek the middle path" for "try the midpoint"). Encouraging wraps the hint in celebratory framing. All three produce measurably different outputs from identical inputs — verifiable in the evaluation harness scenarios #16–18.

### Evaluation Harness (`eval_harness.py`)

`eval_harness.py` covers 20 scenarios across 8 categories: basic game logic, hint direction correctness, all 6 AI patterns, guardrail edge cases, difficulty ranges, all 3 personalities, RAG retrieval, and the lexicographic regression. It prints a structured pass/fail report with a confidence score and system status line. All 20 scenarios pass at 100% confidence.

---

## 6. System Limitations and Future Improvements

**Current limitations:**
- The hint engine is deterministic and rule-based, not a generative model. This makes it reliable and testable but limits expressiveness.
- The game only supports one active round per browser session; there is no persistent scoreboard across sessions.
- There is no accessibility support for screen readers in the Streamlit UI.

**Future improvements:**
- Integrate an actual LLM API (e.g., Claude or OpenAI) to generate more varied, context-aware hints using the same structured prompt as a system message. The current rule-based engine can serve as the ground-truth evaluator to check whether the LLM hints are directionally correct — a form of self-checking guardrail.
- Add a high-score leaderboard persisted to a local SQLite database.
- Add a "explain your reasoning" mode where the player writes why they chose their guess, and the AI responds to their reasoning specifically.
