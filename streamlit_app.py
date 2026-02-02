import threading
import streamlit as st
import requests
import uuid

if "mastered_topics" not in st.session_state:
    st.session_state.mastered_topics = set()

BACKEND = "https://quiz.peterrazeghi.workers.dev"

st.title("Knowledge")

GOAL = 173   # total topics target (adjust later)

def fetch_mastered_count():
    try:
        r = requests.get(
            f"{BACKEND}/mastered-count",
            params={"user_id": st.session_state.user_id},
            timeout=5
        )
        data = r.json()
        return int(data.get("count", 0))
    except:
        return 0

mastered_count = fetch_mastered_count()

st.progress(mastered_count / GOAL if GOAL else 0)
st.caption(f"{mastered_count} of {GOAL} topics mastered")

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


def get_mastered_count():
    r = requests.get(f"{BACKEND}/all-topics", timeout=20)
    return len(r.json())


def prefetch_next():
    data, err = post(
        f"{BACKEND}/next-topic",
        {
            "user_id": st.session_state.user_id
        }
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

# ------------------ error display ------------------

if st.session_state.error:
    st.error(st.session_state.error)

# ------------------ quiz display + visuals + answers ------------------

if st.session_state.quiz and st.session_state.index < len(st.session_state.quiz):

    q = st.session_state.quiz[st.session_state.index]

    if not isinstance(q, dict):
        st.info("Loading question...")
        st.stop()

    # 🧠 Question
    st.markdown(q.get("question", ""))

    # 🖼️ Direct Wikimedia render (bypasses Streamlit CDN bug)
    image_url = q.get("image")
    st.write("DEBUG image_url:", image_url)
    st.write("DEBUG topic:", st.session_state.meta.get("topic"))

    if isinstance(image_url, str) and image_url.startswith("http"):
        st.components.v1.html(
            f"""
            <div style="text-align:center;margin:20px 0;">
                <img src="{image_url}" style="max-width:100%;height:auto;" />
            </div>
            """,
            height=420,
        )

    # ------------------ answers ------------------

    if not st.session_state.show_feedback:

        for letter, text in q.get("choices", {}).items():

            if st.button(
                f"{letter}. {text}",
                key=f"{st.session_state.index}-{letter}",
                use_container_width=True
            ):

                correct = (letter == q.get("correct"))

                try:
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
                except:
                    pass

                if correct:
                    st.session_state.round_correct += 1

                st.session_state.last_correct = correct
                st.session_state.last_explanation = q.get("explanation", "")
                st.session_state.show_feedback = True
                st.rerun()

    else:
        if st.session_state.last_correct:
            st.success("Correct! 🎉")
        else:
            st.error("Not quite ❌")

        st.info(st.session_state.last_explanation)

        if st.button("Next Question"):
            st.session_state.show_feedback = False
            st.session_state.index += 1
            st.rerun()

# ------------------ finished ------------------

if st.session_state.quiz and st.session_state.index >= len(st.session_state.quiz):

    st.success("Topic completed 🎯")

    # If prefetch ready → fast swap
    if st.session_state.next_quiz and st.session_state.next_meta:

        next_topic = st.session_state.next_meta.get("topic", "New topic")

        st.info(f"Next up: {next_topic}")

        st.session_state.quiz = st.session_state.next_quiz
        st.session_state.meta = st.session_state.next_meta

        st.session_state.next_quiz = []
        st.session_state.next_meta = {}

    # Otherwise fetch immediately (safe fallback)
    else:
        data, _ = post(
            f"{BACKEND}/next-topic",
            {"user_id": st.session_state.user_id}
        )

        quiz_data, _ = post(
            f"{BACKEND}/generate-quiz",
            {
                "topic": data["topic"],
                "start_difficulty": data["start_difficulty"]
            }
        )

        st.session_state.quiz = quiz_data["questions"]
        st.session_state.meta = data

    # Reset round state
    st.session_state.index = 0
    st.session_state.show_feedback = False
    st.session_state.round_correct = 0

    # Prefetch again
    threading.Thread(target=prefetch_next, daemon=True).start()
    st.rerun()
