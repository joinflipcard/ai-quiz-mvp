import threading
import streamlit as st
import requests
import uuid

# MUST be first Streamlit call
st.set_page_config(
    page_title="Knowledge",
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

# Get mastered topics count from backend (persistent per user)
count_res = requests.get(
    f"{BACKEND}/mastered-count",
    params={"user_id": st.session_state.user_id},
    timeout=10
).json()

mastered_count = count_res["count"]

# Get total topics once per session
if "total_topics" not in st.session_state:
    r = requests.get(f"{BACKEND}/all-topics")
    st.session_state.total_topics = len(r.json())

total_topics = st.session_state.total_topics

st.markdown(f"### Progress: {mastered_count} / {total_topics} topics mastered")

# Grey bar fills blue as mastery grows
st.progress(mastered_count / total_topics if total_topics else 0)

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

def post(url, payload):
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code != 200:
            return None, r.text
        return r.json(), None
    except Exception as e:
        return None, str(e)

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

# ------------------ DIFFICULTY SELECT ------------------

difficulty = st.radio(
    "Difficulty:",
    ["Easy", "Medium", "Hard"],
    index=1   # default = Medium
)

difficulty_map = {
    "Easy": "easy",
    "Medium": "medium",
    "Hard": "hard"
}

selected_difficulty = difficulty_map[difficulty]

# ------------------ START QUIZ ------------------

if st.button("Start Quiz"):

    data, err = post(
        f"{BACKEND}/next-topic",
        {
            "user_id": st.session_state.user_id,
        }
    )

    if err:
        st.session_state.error = err
    else:
        st.session_state.meta = data

        with st.spinner("Generating questions..."):
            quiz_data, err = post(
                f"{BACKEND}/generate-quiz",
                {
                    "topic": data["topic"],
                    "start_difficulty": selected_difficulty
                }
            )

        if err:
            st.session_state.error = err
        else:
            st.session_state.quiz = quiz_data["questions"]
            st.session_state.index = 0
            st.session_state.show_feedback = False
            st.session_state.error = None

            threading.Thread(target=prefetch_next, daemon=True).start()


st.divider()

# ------------------ PRACTICE ANY TOPIC ------------------

st.subheader("Practice any topic")

custom_topic = st.text_input("Enter a topic you want to practice:")

if st.button("Practice topic") and custom_topic.strip():

    with st.spinner("Generating questions..."):
        quiz_data, err = post(
            f"{BACKEND}/generate-quiz",
            {
                "topic": custom_topic.strip(),
                "start_difficulty": "medium"
            }
        )

    if err:
        st.error(err)
    else:
        st.session_state.quiz = quiz_data["questions"]
        st.session_state.index = 0
        st.session_state.show_feedback = False

        # Practice mode (does not affect mastery)
        st.session_state.meta = {
            "field_id": None,
            "topic_id": None
        }

# ------------------ ERROR ------------------

if st.session_state.error:
    st.error(st.session_state.error)

# ------------------ QUIZ ------------------

# Force blue radio buttons
st.markdown("""
<style>
div[role="radiogroup"] input[type="radio"] {
    accent-color: #1f77ff;
}
</style>
""", unsafe_allow_html=True)


if st.session_state.quiz and st.session_state.index < len(st.session_state.quiz):

    q = st.session_state.quiz[st.session_state.index]

    st.markdown(f"### {q['question']}")
    st.write("")

    if not st.session_state.show_feedback:

        options = [f"{k}. {v}" for k, v in q["choices"].items()]

        selected = st.radio(
            "Choose an answer:",
            options,
            index=None,
            key=f"radio-{st.session_state.index}"
        )

        if st.button("Submit answer"):

            if selected is None:
                st.warning("Please choose an answer first")
                st.stop()

            letter = selected.split(".")[0].strip().upper()
            correct_key = q["correct"].strip().upper()

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
            st.session_state.last_explanation = q["explanation"]
            st.session_state.show_feedback = True
            st.rerun()

    else:
        if st.session_state.last_correct:
            st.success("Correct! 🎉")
        else:
            correct_letter = q["correct"].strip().upper()

            # Safe lookup (handles AI formatting issues)
            if correct_letter in q["choices"]:
                correct_text = q["choices"][correct_letter]
            else:
                # fallback if AI returned full text instead of letter
                correct_text = "Unknown"
                for k, v in q["choices"].items():
                    if v.strip().lower() == correct_letter.lower():
                        correct_letter = k
                        correct_text = v
                        break

            st.error(f"Correct answer: {correct_letter}. {correct_text}")

        st.info(st.session_state.last_explanation)

        if st.button("Next Question"):
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

        data = requests.post(
            f"{BACKEND}/next-topic",
            json={"user_id": st.session_state.user_id},
            timeout=20
        ).json()

        quiz_data = requests.post(
            f"{BACKEND}/generate-quiz",
            json={
                "topic": data["topic"],
                "start_difficulty": data["start_difficulty"]
            },
            timeout=20
        ).json()

        st.session_state.quiz = quiz_data["questions"]
        st.session_state.meta = data
        st.session_state.index = 0
        st.session_state.show_feedback = False
        st.session_state.round_correct = 0

        threading.Thread(target=prefetch_next, daemon=True).start()
        st.rerun()

