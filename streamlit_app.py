import streamlit as st
import requests
import uuid

st.title("AI Tutor Quiz MVP")

BACKEND = "https://quiz.peterrazeghi.workers.dev"

# ------------------ state ------------------

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

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

# ------------------ helpers ------------------

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
        {"user_id": st.session_state.user_id}
    )
    if err:
        return

    quiz_data, err = post(
        f"{BACKEND}/generate-quiz",
        {
            "topic": data["topic"],
            "start_difficulty": data["start_difficulty"]
        }
    )
    if err:
        return

    st.session_state.next_meta = data
    st.session_state.next_quiz = quiz_data["questions"]

# ------------------ start quiz ------------------

if st.button("Start Quiz"):

    data, err = post(
        f"{BACKEND}/next-topic",
        {"user_id": st.session_state.user_id}
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

            prefetch_next()

# ------------------ error display ------------------

if st.session_state.error:
    st.error(st.session_state.error)


# ------------------ quiz display ------------------

if st.session_state.quiz and st.session_state.index < len(st.session_state.quiz):

    q = st.session_state.quiz[st.session_state.index]

    if not isinstance(q, dict) or "question" not in q:
        st.error("Loading next question...")
        st.stop()

    st.subheader(q["question"])

    # 📸 SHOW IMAGE IF PRESENT (safe)
    if q.get("image") and isinstance(q["image"], str) and q["image"].startswith("http"):
    try:
        st.image(q["image"], use_container_width=True)
    except:
        st.warning("Diagram unavailable for this question.")

    if not st.session_state.show_feedback:

        for letter, text in q["choices"].items():
            if st.button(f"{letter}: {text}", key=f"{st.session_state.index}-{letter}"):

                correct = (letter == q["correct"])

                post(
                    f"{BACKEND}/submit-answer",
                    {
                        "user_id": st.session_state.user_id,
                        "field_id": st.session_state.meta["field_id"],
                        "topic_id": st.session_state.meta["topic_id"],
                        "correct": correct
                    }
                )

                st.session_state.last_correct = correct
                if correct:
                    st.session_state.round_correct += 1
                st.session_state.last_explanation = q["explanation"]
                st.session_state.show_feedback = True
                st.rerun()

    else:
        if st.session_state.last_correct:
            st.success("Correct! 🎉")
        else:
            st.error("Not quite ❌")

        st.write("Explanation:")
        st.info(st.session_state.last_explanation)

        if st.button("Next Question"):
            st.session_state.show_feedback = False
            st.session_state.index += 1
            st.rerun()


# ------------------ finished ------------------

if st.session_state.quiz and st.session_state.index >= len(st.session_state.quiz):

    # If prefetch finished — instant swap
    if st.session_state.next_quiz:

        if st.session_state.round_correct >= 3:
            st.success("Topic mastered! ✅")
        else:
            st.info("Moving on to a new topic ➡️")

        st.info(f"Next up: {st.session_state.next_meta['topic']}")

        st.session_state.quiz = st.session_state.next_quiz
        st.session_state.meta = st.session_state.next_meta

        st.session_state.next_quiz = []
        st.session_state.next_meta = {}

        st.session_state.index = 0
        st.session_state.show_feedback = False
        st.session_state.round_correct = 0

        prefetch_next()
        st.rerun()

    # If prefetch still loading — fetch now (fallback)
    else:
        st.info("Loading next topic...")

        data, err = post(
            f"{BACKEND}/next-topic",
            {"user_id": st.session_state.user_id}
        )

        if not err:
            quiz_data, err = post(
                f"{BACKEND}/generate-quiz",
                {
                    "topic": data["topic"],
                    "start_difficulty": data["start_difficulty"]
                }
            )

            if not err:
                st.session_state.quiz = quiz_data["questions"]
                st.session_state.meta = data
                st.session_state.index = 0
                st.session_state.show_feedback = False
                st.session_state.round_correct = 0

                prefetch_next()
                st.rerun()

