import threading
import streamlit as st
import requests

# MUST be first Streamlit call
st.set_page_config(
    page_title="Knowledge",
    page_icon="assets/icon.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 🔧 REMOVE STREAMLIT TOP BANNER + FIX OVERLAP
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {
        display: none;
    }
    .block-container {
        padding-top: 1rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

BACKEND = "https://quiz.peterrazeghi.workers.dev"

# ── Basic styling ───────────────────────────────────────────────
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
h2, h3 {
    margin-top: 0.6rem;
    margin-bottom: 0.4rem;
}
.stRadio > div {
    gap: 6px;
}
.stButton button {
    margin-top: 4px;
}
.category-btn button {
    height: 70px;
    font-size: 1.05rem;
    border-radius: 14px;
    font-weight: 600;
}
.quiz-card {
    background: #ffffff;
    padding: 26px;
    border-radius: 18px;
    box-shadow: 0 6px 16px rgba(0,0,0,.08);
    margin-bottom: 18px;
}
.quiz-question {
    font-size: 1.3rem;
    font-weight: 600;
    margin-bottom: 18px;
    line-height: 1.4;
}
.feedback-good  { background:#e9fff3; padding:16px; border-radius:14px; font-weight:600; }
.feedback-bad   { background:#ffecec; padding:16px; border-radius:14px; font-weight:600; }
.stButton button { border-radius: 12px; height: 48px; }
</style>
""", unsafe_allow_html=True)

# ── LOGIN ───────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.subheader("Login")

    name = st.text_input("Your name").strip()
    code = st.text_input("Access code", type="password").strip()

    if st.button("Enter"):
        if not name or not code:
            st.warning("Please enter both name and access code")
            st.stop()

        try:
            r = requests.post(
                f"{BACKEND}/login",
                json={"name": name, "code": code},
                timeout=10
            )
            r.raise_for_status()
            st.session_state.user_id = r.json()["user_id"]
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            st.stop()

    st.stop()

# ── GLOBAL PROGRESS ─────────────────────────────────────────────
if "total_answered" not in st.session_state:
    st.session_state.total_answered = 0
if "total_correct" not in st.session_state:
    st.session_state.total_correct = 0

accuracy = (
    st.session_state.total_correct / st.session_state.total_answered
    if st.session_state.total_answered > 0
    else 0
)

st.markdown(
    f"### Accuracy: **{round(accuracy * 100)}%** "
    f"({st.session_state.total_correct} / {st.session_state.total_answered})"
)
st.progress(accuracy)

# ── STATE INITIALIZATION ────────────────────────────────────────
defaults = {
    "quiz": [],
    "index": 0,
    "meta": {},
    "error": None,
    "show_feedback": False,
    "last_correct": False,
    "last_explanation": "",
    "next_quiz": [],
    "next_meta": {},
    "round_correct": 0,
    "selected_mode": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ── HELPERS ─────────────────────────────────────────────────────
def post(url, payload, retries=2, timeout=90):
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            if r.status_code == 200:
                return r.json(), None
            else:
                return None, r.text
        except requests.exceptions.ReadTimeout:
            if attempt == retries:
                return None, "Backend timeout after retries"
        except Exception as e:
            if attempt == retries:
                return None, str(e)
    return None, "Request failed after retries"


def prefetch_next(topic, num_questions, difficulty):
    quiz_data, err = post(
        f"{BACKEND}/generate-quiz",
        {
            "topic": topic,
            "start_difficulty": difficulty,
            "num_questions": num_questions,
            "user_id": st.session_state.user_id   # ← added here
        }
    )
    if err or not quiz_data or "questions" not in quiz_data:
        return
    st.session_state.next_quiz = quiz_data["questions"]

# ── CATEGORY MENU ───────────────────────────────────────────────
st.markdown("## Choose a category or enter your own topic")

# ⭐ Pinned custom topic (does NOT interfere with General Knowledge)
custom_topic_input = st.text_input(
    "Choose your own topic",
    placeholder="e.g. World Cup history, neuroscience, Taylor Swift eras…"
)

if custom_topic_input.strip():
    st.session_state.selected_mode = "custom"
    st.session_state.custom_topic = custom_topic_input.strip()

st.markdown("---")

# Categories in compact 3x2 grid (no Recent News)
cols = st.columns(3)

with cols[0]:
    if st.button("🎯 General Knowledge", key="cat-general", use_container_width=True):
        st.session_state.selected_mode = "🎯 General Knowledge"

    if st.button("🏀 Sports", key="cat-sports", use_container_width=True):
        st.session_state.selected_mode = "🏀 Sports"

with cols[1]:
    if st.button("🧪 Science", key="cat-science", use_container_width=True):
        st.session_state.selected_mode = "🧪 Science"

    if st.button("🎬 Entertainment", key="cat-entertainment", use_container_width=True):
        st.session_state.selected_mode = "🎬 Entertainment"

with cols[2]:
    if st.button("📜 History", key="cat-history", use_container_width=True):
        st.session_state.selected_mode = "📜 History"

    if st.button("🌍 Geography", key="cat-geo", use_container_width=True):
        st.session_state.selected_mode = "🌍 Geography"

st.divider()

# ── DIFFICULTY SELECTION ────────────────────────────────────────
st.markdown("### Difficulty")
difficulty = st.radio(
    "Choose level:",
    ["Easy", "Medium", "Hard"],
    horizontal=True,
    index=1
)

difficulty_map = {"Easy": "easy", "Medium": "medium", "Hard": "hard"}
selected_difficulty = difficulty_map[difficulty]


def start_quiz(topic, num_questions=4, is_adaptive=False):
    with st.spinner("🧠 Creating your quiz..."):
        payload = {
            "topic": topic,
            "start_difficulty": selected_difficulty,
            "num_questions": num_questions,
            "user_id": st.session_state.user_id   # ← added here
        }
        if is_adaptive:
            payload.pop("start_difficulty", None)

        quiz_data, err = post(f"{BACKEND}/generate-quiz", payload)

    if err:
        st.error(f"Quiz generation failed: {err}")
        return False

    if not quiz_data or "questions" not in quiz_data:
        st.error("Invalid quiz data from server")
        return False

    st.session_state.quiz = quiz_data["questions"]
    st.session_state.index = 0
    st.session_state.show_feedback = False
    st.session_state.round_correct = 0

    if not is_adaptive:
        st.session_state.meta = {"field_id": None, "topic_id": None}

    return True


# ── AUTO-START LOGIC ────────────────────────────────────────────
selected = st.session_state.get("selected_mode")

field_map = {
    "🧪 Science": "Science trivia",
    "🏀 Sports": "sports trivia",
    "🎬 Entertainment": "movie and celebrity trivia",
    "📜 History": "history trivia",
    "🌍 Geography": "world geography trivia",
    "📰 Recent News": "current events trivia"
}

if selected in field_map and not st.session_state.quiz:
    if start_quiz(field_map[selected], num_questions=4):
        threading.Thread(
            target=prefetch_next,
            args=(field_map[selected], 4, selected_difficulty),
            daemon=True
        ).start()
        st.rerun()

if selected == "custom" and not st.session_state.quiz and "custom_topic" in st.session_state:
    if start_quiz(st.session_state.custom_topic, num_questions=4):
        threading.Thread(
            target=prefetch_next,
            args=(st.session_state.custom_topic, 4, selected_difficulty),
            daemon=True
        ).start()
        st.rerun()

# ── ADAPTIVE GENERAL KNOWLEDGE MODE ─────────────────────────────
if selected == "🎯 General Knowledge" and not st.session_state.quiz:
    data, err = post(
        f"{BACKEND}/next-topic",
        {"user_id": st.session_state.user_id}
    )

    if err or not data:
        st.error("Could not load next topic")
    else:
        st.session_state.meta = data
        if start_quiz(data["topic"], num_questions=3, is_adaptive=True):
            threading.Thread(
                target=prefetch_next,
                args=(data["topic"], 3, data["start_difficulty"]),
                daemon=True
            ).start()
            st.rerun()

# ── QUIZ DISPLAY ────────────────────────────────────────────────
if st.session_state.quiz and st.session_state.index < len(st.session_state.quiz):
    q = st.session_state.quiz[st.session_state.index]

    st.markdown(
        f"<div class='quiz-card'><div class='quiz-question'>{q.get('question', '—')}</div></div>",
        unsafe_allow_html=True
    )

    if not st.session_state.show_feedback:
        choices = q.get("choices", {})
        if not isinstance(choices, dict):
            st.session_state.index += 1
            st.rerun()

        options = [f"{k}. {v}" for k, v in choices.items()]

        selected_answer = st.radio(
            "Select an answer:",
            options,
            index=None,
            key=f"radio-{st.session_state.index}"
        )

        if st.button("Submit answer", use_container_width=True):
            if not selected_answer:
                st.warning("Please select an answer first")
                st.stop()

            letter = selected_answer.split(".", 1)[0].strip().upper()
            correct_letter = str(q.get("correct", "")).strip().upper()
            is_correct = (letter == correct_letter)

            # Debug line
            st.info(f"Debug: Sending question_id = {q.get('id')} | correct = {is_correct}")

            # Send to backend
            try:
                response = requests.post(
                    f"{BACKEND}/submit-answer",
                    json={
                        "user_id": st.session_state.user_id,
                        "field_id": st.session_state.meta.get("field_id"),
                        "topic_id": st.session_state.meta.get("topic_id"),
                        "question_id": q.get("id"),
                        "question_text": q.get("question"),  # ← REQUIRED FIX
                        "correct": is_correct
                    },
                    timeout=5
                )

                if response.status_code != 200:
                    st.error(f"Error from backend: {response.text}")

            except Exception as e:
                st.error(f"Request failed: {str(e)}")

            st.session_state.total_answered += 1
            if is_correct:
                st.session_state.total_correct += 1
                st.session_state.round_correct += 1

            st.session_state.last_correct = is_correct
            st.session_state.last_explanation = q.get("explanation", "")
            st.session_state.show_feedback = True
            st.rerun()

    else:
        if st.session_state.last_correct:
            st.markdown("<div class='feedback-good'>✅ Correct!</div>", unsafe_allow_html=True)
        else:
            correct_letter = q.get("correct", "?")
            correct_text = q["choices"].get(correct_letter, "—")
            st.markdown(
                f"<div class='feedback-bad'>❌ Correct answer: {correct_letter}. {correct_text}</div>",
                unsafe_allow_html=True
            )

        if st.session_state.last_explanation:
            st.info(st.session_state.last_explanation)

        if st.button("Next question →", use_container_width=True):
            st.session_state.show_feedback = False
            st.session_state.index += 1
            st.rerun()

# ── ROUND FINISHED ──────────────────────────────────────────────
if st.session_state.quiz and st.session_state.index >= len(st.session_state.quiz):
    score = st.session_state.round_correct
    total = len(st.session_state.quiz)
    percent = int((score / total) * 100) if total > 0 else 0

    st.markdown("### Round complete 🎯")
    st.progress(percent / 100)
    st.markdown(f"**You got {score} out of {total} correct ({percent}%)**")

    if percent >= 75:
        st.success("Great job — moving you forward 🚀")
    else:
        st.info("Nice effort — let’s keep practicing 💪")

    if st.button("Next round ▶", use_container_width=True):
        # Reset round
        st.session_state.round_correct = 0
        st.session_state.show_feedback = False
        st.session_state.index = 0

        selected = st.session_state.get("selected_mode")

        if selected == "🎯 General Knowledge":
            data, err = post(
                f"{BACKEND}/next-topic",
                {"user_id": st.session_state.user_id}
            )

            if err or not data:
                st.error("Couldn't load next topic — try again")
            else:
                st.session_state.meta = data

                if st.session_state.next_quiz:
                    st.session_state.quiz = st.session_state.next_quiz
                    st.session_state.next_quiz = []
                else:
                    start_quiz(data["topic"], num_questions=3, is_adaptive=True)

                threading.Thread(
                    target=prefetch_next,
                    args=(data["topic"], 3, data.get("start_difficulty", selected_difficulty)),
                    daemon=True
                ).start()
                st.rerun()

        else:
            # Non-adaptive modes
            topic = (
                st.session_state.custom_topic
                if selected == "custom"
                else field_map.get(selected)
            )

            if not topic:
                st.session_state.quiz = []
                st.rerun()
            else:
                if st.session_state.next_quiz:
                    st.session_state.quiz = st.session_state.next_quiz
                    st.session_state.next_quiz = []
                else:
                    start_quiz(topic, num_questions=4)

                threading.Thread(
                    target=prefetch_next,
                    args=(topic, 4, selected_difficulty),
                    daemon=True
                ).start()
                st.rerun()