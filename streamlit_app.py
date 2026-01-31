import streamlit as st
import requests

st.title("AI Tutor Quiz MVP")

BACKEND = "https://quiz.peterrazeghi.workers.dev"

# ---------- state ----------
if "quiz" not in st.session_state:
    st.session_state.quiz = []
    st.session_state.index = 0
    st.session_state.topic = None
    st.session_state.error = None


# ---------- helpers ----------
def get_json(url, method="get", payload=None):
    try:
        if method == "get":
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, json=payload, timeout=20)

        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text}"

        return r.json(), None

    except Exception as e:
        return None, str(e)


# ---------- UI ----------
if st.button("Start Quiz"):

    data, err = get_json(f"{BACKEND}/next-topic")

    if err:
        st.session_state.error = err
    else:
        st.session_state.topic = data.get("topic")

        quiz_data, err = get_json(
            f"{BACKEND}/generate-quiz",
            method="post",
            payload={"topic": st.session_state.topic},
        )

        if err:
            st.session_state.error = err
        else:
            st.session_state.quiz = quiz_data.get("questions", [])
            st.session_state.index = 0
            st.session_state.error = None


# ---------- error display ----------
if st.session_state.error:
    st.error(st.session_state.error)


# ---------- quiz display ----------
if st.session_state.quiz and st.session_state.index < len(st.session_state.quiz):

    q = st.session_state.quiz[st.session_state.index]

    st.subheader(q["question"])

    for letter, text in q["options"].items():
        if st.button(f"{letter}: {text}", key=f"{st.session_state.index}-{letter}"):
            st.session_state.index += 1
            st.rerun()


# ---------- finished ----------
if st.session_state.quiz and st.session_state.index >= len(st.session_state.quiz):
    st.success("Quiz finished! Click Start Quiz to continue learning 🚀")
