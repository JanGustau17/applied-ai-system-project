# 💭 Reflection: Game Glitch Investigator

## 1. What was broken when you started?

The game had multiple behavior bugs that made it feel random and unfair. The two most visible issues were inverted hints ("Go LOWER" when the guess was already too low) and inconsistent game state after New Game. I also found scoring problems where wrong guesses could increase points, and a difficulty mismatch where Hard was smaller than Normal. Another bug came from comparing values as strings during some runs, which produced lexicographic behavior instead of numeric behavior. Once I tracked each issue to a specific function, the fixes became straightforward and testable.

## 2. How did you use AI as a teammate?

I used Copilot Chat in VS Code plus direct prompt comparisons with ChatGPT and Gemini for bug explanations.

### ✅ Helpful AI Output (Accepted)

**Prompt I gave:** "In my Streamlit game, the secret number changes every time I click Submit. How do I keep it stable?"

**AI response (ChatGPT):** "Streamlit reruns the full script on every interaction. Wrap the secret initialization in a session state guard: `if 'secret' not in st.session_state: st.session_state.secret = random.randint(low, high)`. Also make sure to reset `st.session_state.status` inside your New Game handler, otherwise the game stays stuck after a win or loss."

**Why I accepted it:** This was exactly right. Streamlit's rerun model means unguarded variables reset on every click. The session state guard fixed the secret stability, and resetting `status` fixed the stuck-game bug. I verified both by replaying win/loss/reset flows manually and confirming all tests passed.

### ❌ Misleading AI Output (Rejected)

**Prompt I gave:** "I'm getting a type error when comparing guess and secret. How do I fix it?"

**AI response (Copilot):** "Cast both values to strings before comparing to avoid type mismatches: `if str(guess) == str(secret)` and `if str(guess) > str(secret)`."

**Why I rejected it:** String comparison is lexicographic, not numeric. In Python, `"9" > "50"` is `True` because `"9"` comes after `"5"` alphabetically — even though `9 < 50`. Applying this suggestion would cause the game to report "Too High" for a guess of `9` against a secret of `50`, which is completely wrong. I rejected it and instead ensured `parse_guess()` always returns an integer and `check_guess()` always receives integers. I added the test `test_numeric_comparison_not_lexicographic` to permanently guard against this bug.

## 3. Debugging and testing your fixes

I considered a bug fixed only after both manual behavior checks and `pytest` checks passed. For example, I added regression tests for hint direction and score penalties, then confirmed they failed before code changes and passed after updates. I also added tests for the new "temperature" hint feature (`Exact`, `Hot`, `Warm`, `Cold`) so feature expansion was covered automatically. During manual verification, I used Developer Debug Info to validate guesses against the secret in real time. AI helped draft initial test cases, but I rewrote several assertions to target behavior rather than implementation details.

## 4. What did you learn about Streamlit and state?

The secret kept changing because Streamlit reruns the script from top to bottom on every interaction, including each button click. If a value is not protected in `st.session_state`, it can be regenerated and appear unstable to the player. I would explain reruns as "the file executes again like fresh code, but `session_state` is your persistent memory between reruns." The key fix was to initialize the secret only when `"secret"` is not already in session state. I also reset it intentionally on New Game using the current difficulty range so state changes are controlled and predictable.

## 5. Looking ahead: your developer habits

I want to keep the habit of writing a small regression test immediately after reproducing a bug, because it prevents backsliding when refactoring. Next time I will compare two AI outputs earlier, instead of accepting the first "looks plausible" answer. In this project, GPT provided a shorter fix for hint inversion while Gemini gave a clearer explanation of Streamlit reruns; combining both gave the best result. For the score bug, GPT's suggestion ("subtract fixed penalty for all wrong guesses") was more Pythonic than a branch-heavy alternative, and Gemini's explanation of why parity-based scoring was unstable was clearer. This project changed my mindset from "AI writes code for me" to "AI proposes drafts, and I verify every claim with tests and runtime checks."
