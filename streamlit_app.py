import streamlit as st
import requests

st.title("AI Tutor Quiz MVP")

BACKEND = "http://localhost:8000"   # change later if hosted

if "quiz" not in st.session_state:
    st.session_state.quiz = []
    st.session_state.index = 0

if st.button("Start Quiz"):
    topic = requests.get(f"{BACKEND}/next-topic").json()["topic"]

    quiz = requests.post(
        f"{BACKEND}/generate-quiz",
        json={"topic": topic}
    ).json()["questions"]

    st.session_state.quiz = quiz
    st.session_state.index = 0

if st.session_state.quiz:
    q = st.session_state.quiz[st.session_state.index]

    st.subheader(q["question"])

    for letter, text in q["options"].items():
        if st.button(f"{letter}: {text}"):
            st.session_state.index += 1
            st.rerun()
