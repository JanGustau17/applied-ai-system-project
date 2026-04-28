# 🎤 Presentation Script — Game Glitch Investigator
**5–7 minutes | AI110 Final Project | Mukhammadali Yuldoshev**

---

## SLIDE 1 — Intro (30 sec)

"Hi, I'm Mukhammadali. My final project is called Game Glitch Investigator — a number-guessing game that I turned into a full applied AI system. I started with a broken game from Project 1 and ended up with a GPT-powered hint engine that retrieves strategy tips from a knowledge base, reasons about game state in 4 observable steps, and degrades gracefully when the API is unavailable. Let me show you how it works."

---

## SLIDE 2 — The Original System (45 sec)

"The base app — Project 1 — was intentionally broken in 8 ways. Hints were inverted: it said Go Lower when you needed to go higher. Hard mode was easier than Normal because the range was wrong. The game stayed stuck after a win because status never reset. And my personal favorite: it was comparing numbers as strings, so 9 was considered greater than 50 because 'nine' comes after 'five' alphabetically.

I fixed all 8 bugs, but the more interesting question was: what happens if I extend this into something more AI-powered?"

---

## SLIDE 3 — System Architecture (60 sec)

*[Show the architecture SVG or diagram on screen]*

"Here's how the system is organized. User input flows into the Streamlit UI, passes through an input guardrail that rejects non-numeric and out-of-range values before they touch any logic, then splits into two engines:

The Game Logic Engine handles check_guess, scoring, and temperature — hot/warm/cold proximity feedback.

The AI Hint Engine is the new part. It runs 4 steps: gather context from the game state, classify the situation into one of 6 reasoning patterns, retrieve the most relevant strategy tip from a 9-document knowledge base — that's the RAG step — and then call GPT-4o-mini with all of that as a structured system prompt to generate the final hint.

Everything flows into session state, and the output includes the hint, the temperature, the score, and optionally the full reasoning trace."

---

## SLIDE 4 — Live Demo (2 min)

*[Switch to the running Streamlit app]*

**Demo 1 — Normal mode, Coach, Show trace ON:**
"I'll start with a guess of 10. Watch the right side — the AI reasoning trace shows Step 1 computed distance and direction, Step 2 classified this as first_guess, Step 3 retrieved the binary search tip from the knowledge base, and Step 4 sent that to GPT-4o-mini to generate this specific hint. The hint isn't a canned string — it's GPT reasoning about this exact game state."

**Demo 2 — Hard mode, Cryptic:**
"Now I'll switch to Hard mode and Cryptic personality. Same game state, completely different output. The system prompt tells GPT to be mysterious — so it says 'ascend' instead of 'go higher' and uses metaphors. The RAG step retrieves a different document too — the binary search efficiency tip specific to Hard mode."

**Demo 3 — Guardrail:**
"Let me type 'hello' as a guess. Rejected — no attempt consumed. Out of range number? Same — rejected at the guardrail before it reaches any game logic."

---

## SLIDE 5 — Reliability (45 sec)

*[Switch to terminal]*

"Reliability was a first-class concern, not an afterthought.

`python eval_harness.py` — 20 predefined scenarios, covering every component. You can see: 20/20 passed, 100% confidence, ALL SYSTEMS NOMINAL.

The pytest suite has 22 cases. The key insight was that testing AI-integrated code requires mocking the model call. I moved the OpenAI import to module level so it's patchable, and each test injects a deterministic response. That means these tests run anywhere, no API key required.

And every live GPT call gets logged to ai_hint.log — model, pattern, personality, response, timestamp. If something looks wrong, I can audit it."

---

## SLIDE 6 — What I Learned (60 sec)

"Three things I'll take from this project.

First: the difference between a demo and an integration. A demo shows GPT responding to a prompt. An integration means GPT's output changes how the system behaves, and that requires guardrails, logging, and tests. All of that was more work than the GPT call itself.

Second: test AI as an external dependency. Mock the model call. Test the routing logic — the pattern selection, the RAG retrieval, the personality routing — independently. Don't write tests that assert on GPT's exact phrasing, because it paraphrases freely and your tests will break.

Third: AI suggestions need verification. Copilot told me to compare numbers as strings. That looked plausible. It was provably wrong once I wrote the test. The habit is: every AI suggestion is a hypothesis. Write the falsifying test first.

This project is what I point to when someone asks me what I know about building AI systems."

---

## LOOM WALKTHROUGH CHECKLIST
*(What to show in your recorded video — keep it under 5 min)*

- [ ] Open the app in browser
- [ ] Submit 2-3 guesses with trace panel open — show hint changing each time
- [ ] Switch personality to Cryptic — show same game state, different output
- [ ] Type a non-numeric input — show guardrail rejection
- [ ] Type an out-of-range number — show second guardrail rejection
- [ ] Run `python eval_harness.py` in terminal — show 20/20 PASS output
- [ ] Point to `ai_hint.log` briefly to show logging exists

**Do NOT show:** file structure, installation steps, code walkthrough
