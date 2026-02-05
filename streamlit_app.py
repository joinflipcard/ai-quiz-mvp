import threading
import streamlit as st
import requests
import uuid

# MUST be first Streamlit call
st.set_page_config(
    page_title="Knowledge",
    page_icon="assets/icon.png",   # or icon.ico
    layout="centered",
    initial_sidebar_state="collapsed"
)

# App logo
st.markdown("<div style='text-align:center; margin-bottom: 20px;'>", unsafe_allow_html=True)
st.image("assets/131.png", width=120)
st.markdown("</div>", unsafe_allow_html=True)

BACKEND = "https://quiz.peterrazeghi.workers.dev"

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ------------------ LOGIN ------------------

if "user_id" not in st.session_state:

    st.subheader("Login")

    name = st.text_input("Your name").strip()
    code = st.text_input("Access code", type="password").strip()

    if st.button("Enter"):

        if not name or not code:
            st.warning("Enter name and access code")
            st.stop()

        r = requests.post(
            f"{BACKEND}/login",
            json={"name": name, "code": code},
            timeout=10
        )

        if r.status_code != 200:
            st.error(f"Login failed: {r.text}")
            st.stop()

        st.session_state.user_id = r.json()["user_id"]
        st.rerun()

    st.stop()

# ------------------ PROGRESS ------------------

# Get total correct + attempts (simple accuracy)
stats = requests.get(
    f"{BACKEND}/user-accuracy",
    params={"user_id": st.session_state.user_id},
    timeout=10
).json()

correct = stats.get("correct", 0)
attempts = stats.get("attempts", 0)

accuracy = correct / attempts if attempts else 0

percent = round(accuracy * 100)

st.markdown(f"### Accuracy: {percent}%")

st.progress(accuracy)

# ------------------ STATE ------------------

if "quiz" not in st.session_state:
    st.session_state.quiz = []

if "index" not in st.session_state:
    st.session_state.index = 0

if "meta" not in st.session_state:
    st.session_state.meta = {}

if "error" not in st.session_state:
    st.session_state.error = None

if "show_feedback" not in st.session_state:
    st.session_state.show_feedback = False
    st.session_state.last_correct = False
    st.session_state.last_explanation = ""

if "next_quiz" not in st.session_state:
    st.session_state.next_quiz = []

if "next_meta" not in st.session_state:
    st.session_state.next_meta = {}

if "round_correct" not in st.session_state:
    st.session_state.round_correct = 0

# ------------------ HELPERS ------------------

def post(url, payload, retries=2):
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=90)
            if r.status_code == 200:
                return r.json(), None
            else:
                err = r.text
        except requests.exceptions.ReadTimeout:
            err = "Backend took too long — retrying..."

        if attempt < retries:
            continue

    return None, err

def prefetch_next():
    data, err = post(
        f"{BACKEND}/next-topic",
        {
            "user_id": st.session_state.user_id,
        }
    )

    if err or not data:
        return

    quiz_data, err = post(
        f"{BACKEND}/generate-quiz",
        {
            "topic": data["topic"],
            "start_difficulty": data["start_difficulty"]
        }
    )

    if err or not quiz_data:
        return

    st.session_state.next_meta = data
    st.session_state.next_quiz = quiz_data["questions"]

# ------------------ QUIZ MENU ------------------

st.subheader("Choose a topic")

menu_items = [
    "🎯 General Knowledge",
    "🧪 Science",
    "🏀 Sports",
    "🎬 Entertainment",
    "📜 History",
    "🌍 Geography",
    "📰 Recent News"
]

if "selected_mode" not in st.session_state:
    st.session_state.selected_mode = None

cols = st.columns(2)

for i, label in enumerate(menu_items):
    with cols[i % 2]:
        if st.button(label, use_container_width=True):
            st.session_state.selected_mode = label

# ------------------ PICK YOUR TOPIC ------------------

st.markdown("---")
st.markdown("### Pick your own topic")

custom_topic = st.text_input("Enter any topic you want to learn:")

if st.button("Start custom topic") and custom_topic.strip():
    st.session_state.selected_mode = "custom"
    st.session_state.custom_topic = custom_topic.strip()

st.divider()

# ------------------ START QUIZ FROM MENU ------------------

def start_quiz(topic, difficulty="medium", num_questions=4):
    with st.spinner("Generating questions..."):
        quiz_data, err = post(
            f"{BACKEND}/generate-quiz",
            {
                "topic": topic,
                "start_difficulty": difficulty,
                "num_questions": num_questions
            }
        )

    if err:
        st.error(err)
        return

    st.session_state.quiz = quiz_data["questions"]
    st.session_state.index = 0
    st.session_state.show_feedback = False

    # Non-mastery modes don’t affect topic mastery
    st.session_state.meta = {
        "field_id": None,
        "topic_id": None
    }


# -------- General Knowledge (adaptive mastery) --------

if st.session_state.get("selected_mode") == "🎯 General Knowledge":

    data, err = post(
        f"{BACKEND}/next-topic",
        {"user_id": st.session_state.user_id}
    )

    if err:
        st.error(err)
    else:
        st.session_state.meta = data

        with st.spinner("Generating questions..."):
            quiz_data, err = post(
                f"{BACKEND}/generate-quiz",
                {
                    "topic": data["topic"],
                    "start_difficulty": data["start_difficulty"]
                }
            )

        if err:
            st.error(err)
        else:
            st.session_state.quiz = quiz_data["questions"]
            st.session_state.index = 0
            st.session_state.show_feedback = False

            threading.Thread(target=prefetch_next, daemon=True).start()


# -------- Field Buttons (always 4 smart questions) --------

field_map = {
    "🧪 Science": "Science",
    "🏀 Sports": "Sports",
    "🎬 Entertainment": "Entertainment",
    "📜 History": "History",
    "🌍 Geography": "Geography",
    "📰 Recent News": "Recent News"
}

selected = st.session_state.get("selected_mode")

if selected in field_map:
    start_quiz(field_map[selected], num_questions=4)


# -------- Pick Your Topic --------

if st.session_state.get("selected_mode") == "custom":
    start_quiz(st.session_state.custom_topic, num_questions=4)

# ------------------ ERROR ------------------

if st.session_state.error:
    st.error(st.session_state.error)

# ------------------ QUIZ ------------------

st.markdown("""
<style>
.quiz-card {
    background: #f9fafc;
    padding: 22px;
    border-radius: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,.06);
    margin-bottom: 20px;
}

.quiz-question {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 16px;
}

.feedback-good {
    background:#e8fff2;
    padding:14px;
    border-radius:12px;
}

.feedback-bad {
    background:#ffecec;
    padding:14px;
    border-radius:12px;
}
</style>
""", unsafe_allow_html=True)


if st.session_state.quiz and st.session_state.index < len(st.session_state.quiz):

    q = st.session_state.quiz[st.session_state.index]

    st.markdown(
        f"<div class='quiz-card'><div class='quiz-question'>{q['question']}</div></div>",
        unsafe_allow_html=True
    )

    if not st.session_state.show_feedback:

        if not isinstance(q.get("choices"), dict):
            st.session_state.index += 1
            st.rerun()

        options = [f"{k}. {v}" for k, v in q["choices"].items()]

        selected = st.radio(
            "Choose one:",
            options,
            index=None,
            key=f"radio-{st.session_state.index}"
        )

        if st.button("Submit"):

            if selected is None:
                st.warning("Pick an answer first")
                st.stop()

            letter = selected.split(".")[0].strip().upper()
            correct_key = str(q.get("correct", "")).strip().upper()

            correct = (letter == correct_key)

            requests.post(
                f"{BACKEND}/submit-answer",
                json={
                    "user_id": st.session_state.user_id,
                    "field_id": st.session_state.meta["field_id"],
                    "topic_id": st.session_state.meta["topic_id"],
                    "correct": correct
                },
                timeout=5
            )

            if correct:
                st.session_state.round_correct += 1

            st.session_state.last_correct = correct
            st.session_state.last_explanation = q.get("explanation", "")
            st.session_state.show_feedback = True
            st.rerun()

    else:
        if st.session_state.last_correct:
            st.markdown(
                "<div class='feedback-good'>✅ Correct!</div>",
                unsafe_allow_html=True
            )
        else:
            correct_letter = q.get("correct", "?")
            correct_text = q["choices"].get(correct_letter, "Unknown")

            st.markdown(
                f"<div class='feedback-bad'>❌ Correct answer: {correct_letter}. {correct_text}</div>",
                unsafe_allow_html=True
            )

        st.info(st.session_state.last_explanation)

        if st.button("Next"):
            st.session_state.show_feedback = False
            st.session_state.index += 1
            st.rerun()

# ------------------ FINISHED ------------------

if st.session_state.quiz and st.session_state.index >= len(st.session_state.quiz):

    # ⚡ Fast path — use prefetched next topic
    if st.session_state.next_quiz:

        if st.session_state.round_correct >= 3:
            st.success("Topic mastered 🎉")

            # allow backend to commit mastery before refreshing progress
            import time
            time.sleep(0.3)

        else:
            st.info("Topic not yet mastered — keep practicing 💪")

        st.info(f"Next up: {st.session_state.next_meta['topic']}")

        st.session_state.quiz = st.session_state.next_quiz
        st.session_state.meta = st.session_state.next_meta

        st.session_state.next_quiz = []
        st.session_state.next_meta = {}

        st.session_state.index = 0
        st.session_state.show_feedback = False
        st.session_state.round_correct = 0

        threading.Thread(target=prefetch_next, daemon=True).start()
        st.rerun()

        # 🛟 Fallback — load immediately if prefetch not ready
    else:
        st.info("Loading next topic...")

        data, err = post(
            f"{BACKEND}/next-topic",
            {"user_id": st.session_state.user_id}
        )

        if err or not data:
            st.error("Failed to load next topic — try again")
            st.stop()

        quiz_data, err = post(
            f"{BACKEND}/generate-quiz",
            {
                "topic": data["topic"],
                "start_difficulty": data["start_difficulty"]
            }
        )

        if err or not quiz_data:
            st.error("Question generation took too long — retrying helps")
            st.stop()

        st.session_state.quiz = quiz_data["questions"]
        st.session_state.meta = data
        st.session_state.index = 0
        st.session_state.show_feedback = False
        st.session_state.round_correct = 0

        threading.Thread(target=prefetch_next, daemon=True).start()
        st.rerun()

