import random
import streamlit as st
from logic_utils import (
    ai_hint_engine,
    check_guess,
    get_hint_temperature,
    get_range_for_difficulty,
    parse_guess,
    update_score,
)

st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")

st.title("🎮 Game Glitch Investigator")
st.caption("An AI-generated guessing game. Something is off.")

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

# Stretch Feature 3: few-shot personality modes
personality = st.sidebar.selectbox(
    "AI Hint Personality",
    ["Coach", "Cryptic", "Encouraging"],
    index=0,
    help=(
        "Coach: analytical with strategy tips. "
        "Cryptic: mysterious phrasing. "
        "Encouraging: warm and celebratory."
    ),
)

# Stretch Feature 2: toggle for agentic reasoning trace
show_trace = st.sidebar.checkbox(
    "Show AI reasoning trace",
    value=False,
    help="Reveals the agent's intermediate steps: context gathered, pattern selected, RAG tip retrieved.",
)

attempt_limit_map = {
    "Easy": 6,
    "Normal": 8,
    "Hard": 5,
}
attempt_limit = attempt_limit_map[difficulty]

low, high = get_range_for_difficulty(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

if "secret" not in st.session_state:
    st.session_state.secret = random.randint(low, high)

if "attempts" not in st.session_state:
    st.session_state.attempts = 0  # BUG FIX: was 1, but new_game resets to 0 — inconsistent; 0 is the correct starting value

if "score" not in st.session_state:
    st.session_state.score = 0

if "status" not in st.session_state:
    st.session_state.status = "playing"

if "history" not in st.session_state:
    st.session_state.history = []

if "last_hint" not in st.session_state:
    st.session_state.last_hint = None

if "last_temperature" not in st.session_state:
    st.session_state.last_temperature = None

if "ai_hint" not in st.session_state:
    st.session_state.ai_hint = None

if "ai_trace" not in st.session_state:
    st.session_state.ai_trace = None

st.subheader("Make a guess")

st.info(
    f"Guess a number between {low} and {high}. "  # BUG FIX: was hardcoded "1 and 100", ignoring difficulty range
    f"Attempts left: {attempt_limit - st.session_state.attempts}"
)

with st.expander("Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Difficulty:", difficulty)
    st.write("Personality:", personality)
    st.write("History:", st.session_state.history)

raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_input_{difficulty}"
)

col1, col2, col3 = st.columns(3)
with col1:
    submit = st.button("Submit Guess 🚀")
with col2:
    new_game = st.button("New Game 🔁")
with col3:
    show_hint = st.checkbox("Show hint", value=True)

if new_game:
    st.session_state.attempts = 0
    st.session_state.secret = random.randint(low, high)  # BUG FIX: was randint(1, 100), ignored difficulty range
    st.session_state.status = "playing"  # BUG FIX: status was never reset, game stayed stuck after win/loss
    st.session_state.history = []
    st.session_state.last_hint = None
    st.session_state.last_temperature = None
    st.session_state.ai_hint = None
    st.session_state.ai_trace = None
    st.success("New game started.")
    st.rerun()

if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success("You already won. Start a new game to play again.")
    else:
        st.error("Game over. Start a new game to try again.")
    st.stop()

if submit:
    st.session_state.attempts += 1

    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.session_state.history.append(raw_guess)
        st.error(err)
    else:
        st.session_state.history.append(guess_int)

        # BUG FIX: was converting secret to str on even attempts, causing lexicographic comparison (e.g. "9" > "50" = True)
        secret = st.session_state.secret

        outcome, message = check_guess(guess_int, secret)
        st.session_state.last_temperature = get_hint_temperature(guess_int, secret)

        # BUG FIX: hint was only shown inside `if submit:`, so toggling the checkbox
        # after a guess triggered a rerun but never re-displayed the hint. Fix: store
        # the hint in session state so it can be rendered on any rerun.
        st.session_state.last_hint = message

        st.session_state.score = update_score(
            current_score=st.session_state.score,
            outcome=outcome,
            attempt_number=st.session_state.attempts,
        )

        # AI Hint Engine — 4-step agentic structured prompting pipeline
        # Integrates: RAG retrieval (Stretch 1), agentic trace (Stretch 2),
        # personality modes (Stretch 3)
        numeric_history = [g for g in st.session_state.history[:-1] if isinstance(g, int)]
        result = ai_hint_engine(
            guess=guess_int,
            secret=secret,
            history=numeric_history,
            attempt_number=st.session_state.attempts,
            difficulty=difficulty,
            personality=personality,
            return_trace=True,
        )
        ai_hint, ai_trace = result
        st.session_state.ai_hint = ai_hint
        st.session_state.ai_trace = ai_trace

        if outcome == "Win":
            st.balloons()
            st.session_state.status = "won"
            st.success(
                f"You won! The secret was {st.session_state.secret}. "
                f"Final score: {st.session_state.score}"
            )
        else:
            if st.session_state.attempts >= attempt_limit:
                st.session_state.status = "lost"
                st.error(
                    f"Out of attempts! "
                    f"The secret was {st.session_state.secret}. "
                    f"Score: {st.session_state.score}"
                )

if show_hint and st.session_state.last_hint:
    st.warning(st.session_state.last_hint)
    if st.session_state.last_temperature:
        st.caption(f"Temperature: {st.session_state.last_temperature}")

if st.session_state.ai_hint:
    st.info(st.session_state.ai_hint)

# Stretch Feature 2: Agentic reasoning trace — shows intermediate steps
if show_trace and st.session_state.ai_trace:
    trace = st.session_state.ai_trace
    with st.expander("🤖 AI Reasoning Trace (Agentic Steps)", expanded=True):
        st.markdown("**Step 1 — Context gathered:**")
        ctx = trace["step1_context"]
        st.code(
            f"guess={ctx['guess']}  distance={ctx['distance']}  "
            f"direction={ctx['direction']}  temperature={ctx['temperature']}  "
            f"narrowing={ctx['narrowing']}  history_length={ctx['history_length']}",
            language="text",
        )
        st.markdown(f"**Step 2 — Reasoning pattern selected:** `{trace['step2_pattern']}`")
        st.markdown(f"**Step 3 — RAG tip retrieved:**")
        st.info(trace["step3_rag_tip"])
        st.markdown(f"**Step 4 — Personality applied:** `{trace['step4_personality']}`")
        st.markdown(f"**Final hint:** {trace['final_hint']}")

with st.expander("Guess Insights"):
    if st.session_state.history:
        st.write("Recent guesses:", st.session_state.history[-5:])
    else:
        st.write("No guesses yet.")
    if st.session_state.last_temperature:
        st.write("Latest proximity:", st.session_state.last_temperature)
    else:
        st.write("Make a guess to see proximity feedback.")

st.divider()
st.caption("Built by an AI that claims this code is production-ready.")
