import threading
import streamlit as st
import requests
import uuid
import pandas as pd

BACKEND = "https://quiz.peterrazeghi.workers.dev"

st.title("Knowledge")

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

if "total_topics" not in st.session_state:
    r = requests.get(f"{BACKEND}/all-topics")
    st.session_state.total_topics = len(r.json())

if "mastered_topics" not in st.session_state:
    st.session_state.mastered_topics = set()

total_topics = st.session_state.total_topics
mastered_count = len(st.session_state.mastered_topics)

st.markdown(
    f"### Progress: {mastered_count} / {total_topics} topics mastered"
)

progress_ratio = mastered_count / total_topics if total_topics else 0

# grey background → blue fill grows automatically
st.progress(progress_ratio)

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
            "exclude": list(st.session_state.mastered_topics)
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

# ------------------ START QUIZ ------------------

if st.button("Start Quiz"):

    data, err = post(
        f"{BACKEND}/next-topic",
        {
            "user_id": st.session_state.user_id,
            "exclude": list(st.session_state.mastered_topics)
        }
    )

    if err:
        st.session_state.error = err
    else:
        st.session_state.meta = data

        quiz_data, err = post(
            f"{BACKEND}/generate-quiz",
            {
                "topic": data["topic"],
                "start_difficulty": data["start_difficulty"]
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

# ------------------ ERROR ------------------

if st.session_state.error:
    st.error(st.session_state.error)

# ------------------ QUIZ ------------------

if st.session_state.quiz and st.session_state.index < len(st.session_state.quiz):

    q = st.session_state.quiz[st.session_state.index]

    st.markdown(f"### {q['question']}")

    if not st.session_state.show_feedback:

        for letter, text in q["choices"].items():

            if st.button(f"{letter}. {text}", key=f"{st.session_state.index}-{letter}"):

                correct = (letter == q["correct"])

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
        st.success("Correct! 🎉" if st.session_state.last_correct else "Not quite ❌")
        st.info(st.session_state.last_explanation)

        if st.button("Next Question"):
            st.session_state.show_feedback = False
            st.session_state.index += 1
            st.rerun()

# ------------------ FINISHED ------------------

if st.session_state.quiz and st.session_state.index >= len(st.session_state.quiz):

    if st.session_state.next_quiz:

        if st.session_state.round_correct >= 3:
            st.success("Topic mastered 🎉")

            mastered_id = st.session_state.meta.get("topic_id")
            if mastered_id:
                st.session_state.mastered_topics.add(mastered_id)

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

    else:
        st.info("Loading next topic...")

        data = requests.post(
            f"{BACKEND}/next-topic",
            json={
                "user_id": st.session_state.user_id,
                "exclude": list(st.session_state.mastered_topics)
            },
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
