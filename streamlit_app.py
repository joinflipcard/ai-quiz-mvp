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

BACKEND = "https://quiz.peterrazeghi.workers.dev"

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

# init accuracy tracking
if "total_answered" not in st.session_state:
    st.session_state.total_answered = 0

if "total_correct" not in st.session_state:
    st.session_state.total_correct = 0

# calculate percent (avoid divide by zero)
if st.session_state.total_answered == 0:
    accuracy = 0
else:
    accuracy = st.session_state.total_correct / st.session_state.total_answered

st.markdown(
    f"### Accuracy: {round(accuracy * 100)}%  "
    f"({st.session_state.total_correct} / {st.session_state.total_answered} correct)"
)

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

def prefetch_next(topic, num_questions):
    quiz_data, err = post(
        f"{BACKEND}/generate-quiz",
        {
            "topic": topic,
            "start_difficulty": selected_difficulty,
            "num_questions": num_questions
        }
    )

    if err or not quiz_data:
        return

    st.session_state.next_quiz = quiz_data["questions"]

# ------------------ QUIZ MENU ------------------

st.markdown("## Choose a category")

st.markdown("""
<style>
.category-btn button {
    height: 70px;
    font-size: 1.05rem;
    border-radius: 14px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

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

rows = [
    st.columns(2),
    st.columns(2),
    st.columns(2),
    st.columns(1)
]

i = 0
for row in rows:
    for col in row:
        if i >= len(menu_items):
            break
        with col:
            if st.button(
                menu_items[i],
                key=f"cat-{i}",
                use_container_width=True
            ):
                st.session_state.selected_mode = menu_items[i]
        i += 1

# ------------------ PICK YOUR TOPIC ------------------

st.markdown("---")
st.markdown("### Pick your own topic")

custom_topic = st.text_input("Enter any topic you want to learn:")

if st.button("Start custom topic") and custom_topic.strip():
    st.session_state.selected_mode = "custom"
    st.session_state.custom_topic = custom_topic.strip()

st.divider()

# ------------------ START QUIZ FROM MENU ------------------

st.markdown("### Difficulty")

difficulty = st.radio(
    "Choose level:",
    ["Easy", "Medium", "Hard"],
    horizontal=True,
    index=1
)

difficulty_map = {
    "Easy": "easy",
    "Medium": "medium",
    "Hard": "hard"
}

selected_difficulty = difficulty_map[difficulty]


def start_quiz(topic, num_questions=4):
    with st.spinner("🧠 Creating your quiz..."):
        quiz_data, err = post(
            f"{BACKEND}/generate-quiz",
            {
                "topic": topic,
                "start_difficulty": selected_difficulty,
                "num_questions": num_questions
            }
        )

    if err:
        st.error(err)
        return

    st.session_state.quiz = quiz_data["questions"]
    st.session_state.index = 0
    st.session_state.show_feedback = False
    st.session_state.round_correct = 0

    # non-mastery modes don’t affect topic mastery
    st.session_state.meta = {
        "field_id": None,
        "topic_id": None
    }

    # ⚡ prefetch next round in background
    threading.Thread(
        target=prefetch_next,
        args=(topic, num_questions),
        daemon=True
    ).start()


# ------------------ AUTO START BASED ON MENU ------------------

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
    with st.spinner("🧠 Creating your quiz..."):
        start_quiz(field_map[selected], num_questions=4)
    st.rerun()

if selected == "custom" and not st.session_state.quiz:
    with st.spinner("🧠 Creating your quiz..."):
        start_quiz(st.session_state.custom_topic, num_questions=4)
    st.rerun()


# -------- General Knowledge (adaptive mastery) --------

if st.session_state.get("selected_mode") == "🎯 General Knowledge" and not st.session_state.quiz:

    data, err = post(
        f"{BACKEND}/next-topic",
        {"user_id": st.session_state.user_id}
    )

    if err:
        st.error(err)
    else:
        st.session_state.meta = data

        with st.spinner("🧠 Creating your quiz..."):
            quiz_data, err = post(
                f"{BACKEND}/generate-quiz",
                {
                    "topic": data["topic"],
                    "start_difficulty": data["start_difficulty"],
                    "num_questions": 3
                }
            )

        if err:
            st.error(err)
        else:
            st.session_state.quiz = quiz_data["questions"]
            st.session_state.index = 0
            st.session_state.show_feedback = False
            st.session_state.round_correct = 0

            threading.Thread(
                target=prefetch_next,
                args=(data["topic"], 3),
                daemon=True
            ).start()

# ------------------ ERROR ------------------

if st.session_state.error:
    st.error(st.session_state.error)

# ------------------ QUIZ ------------------

st.markdown("""
<style>
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

.feedback-good {
    background:#e9fff3;
    padding:16px;
    border-radius:14px;
    font-weight:600;
}

.feedback-bad {
    background:#ffecec;
    padding:16px;
    border-radius:14px;
    font-weight:600;
}

.stButton button {
    border-radius: 12px;
    height: 48px;
}
</style>
""", unsafe_allow_html=True)


if st.session_state.quiz and st.session_state.index < len(st.session_state.quiz):

    q = st.session_state.quiz[st.session_state.index]

    st.markdown(
        f"<div class='quiz-card'><div class='quiz-question'>{q.get('question','')}</div></div>",
        unsafe_allow_html=True
    )

    if not st.session_state.show_feedback:

        if not isinstance(q.get("choices"), dict):
            st.session_state.index += 1
            st.rerun()

        options = [f"{k}. {v}" for k, v in q["choices"].items()]

        selected = st.radio(
            "Select an answer:",
            options,
            index=None,
            key=f"radio-{st.session_state.index}"
        )

        if st.button("Submit answer", use_container_width=True):

            if selected is None:
                st.warning("Choose an option first")
                st.stop()

            letter = selected.split(".")[0].strip().upper()
            correct_raw = q.get("correct")

            if not isinstance(correct_raw, str):
                st.session_state.index += 1
                st.session_state.show_feedback = False
                st.rerun()

            correct_key = correct_raw.strip().upper()
            correct = (letter == correct_key)

            requests.post(
                f"{BACKEND}/submit-answer",
                json={
                    "user_id": st.session_state.user_id,
                    "field_id": st.session_state.meta.get("field_id"),
                    "topic_id": st.session_state.meta.get("topic_id"),
                    "correct": correct
                },
                timeout=5
            )

            st.session_state.total_answered += 1
            if correct:
                st.session_state.total_correct += 1
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

        if st.button("Next question →", use_container_width=True):
            st.session_state.show_feedback = False
            st.session_state.index += 1
            st.rerun()
# ------------------ FINISHED ------------------

if st.session_state.quiz and st.session_state.index >= len(st.session_state.quiz):

    score = st.session_state.round_correct
    total = len(st.session_state.quiz)

    percent = int((score / total) * 100) if total else 0

    st.markdown("### Round complete 🎯")
    st.progress(percent / 100)
    st.markdown(f"**You got {score} out of {total} correct ({percent}%)**")

    if percent >= 75:
        st.success("Great job — moving you forward 🚀")
    else:
        st.info("Nice effort — let’s keep practicing 💪")

    st.write("")

    if st.button("Next round ▶", use_container_width=True):

        # reset round state
        st.session_state.round_correct = 0
        st.session_state.show_feedback = False
        st.session_state.index = 0

        selected = st.session_state.get("selected_mode")

        # -------- Adaptive General Knowledge --------
        if selected == "🎯 General Knowledge":

            data, err = post(
                f"{BACKEND}/next-topic",
                {"user_id": st.session_state.user_id}
            )

            if err or not data:
                st.error("Couldn't load next topic — try again")
                st.stop()

            st.session_state.meta = data

            # 👉 use prefetched if available
            if st.session_state.next_quiz:
                st.session_state.quiz = st.session_state.next_quiz
                st.session_state.next_quiz = []
            else:
                quiz_data, err = post(
                    f"{BACKEND}/generate-quiz",
                    {
                        "topic": data["topic"],
                        "start_difficulty": data["start_difficulty"],
                        "num_questions": 3
                    }
                )

                if err:
                    st.error("Generation failed — retry")
                    st.stop()

                st.session_state.quiz = quiz_data["questions"]

            # ⚡ prefetch again
            threading.Thread(
                target=prefetch_next,
                args=(data["topic"], 3),
                daemon=True
            ).start()

            st.rerun()

        # -------- All other modes --------
        else:

            field_map = {
                "🧪 Science": "Science trivia",
                "🏀 Sports": "sports trivia",
                "🎬 Entertainment": "movie and celebrity trivia",
                "📜 History": "history trivia",
                "🌍 Geography": "world geography trivia",
                "📰 Recent News": "current events trivia"
            }

            if selected == "custom":
                topic = st.session_state.custom_topic
            else:
                topic = field_map.get(selected)

            if not topic:
                st.session_state.quiz = []
                st.rerun()

            # 👉 use prefetched if available
            if st.session_state.next_quiz:
                st.session_state.quiz = st.session_state.next_quiz
                st.session_state.next_quiz = []
            else:
                quiz_data, err = post(
                    f"{BACKEND}/generate-quiz",
                    {
                        "topic": topic,
                        "start_difficulty": selected_difficulty,
                        "num_questions": 4
                    }
                )

                if err:
                    st.error("Generation failed — retry")
                    st.stop()

                st.session_state.quiz = quiz_data["questions"]

            # ⚡ prefetch again
            threading.Thread(
                target=prefetch_next,
                args=(topic, 4),
                daemon=True
            ).start()

            st.rerun()
