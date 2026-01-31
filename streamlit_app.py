import streamlit as st

st.title("AI Tutor Quiz MVP")

if "count" not in st.session_state:
    st.session_state.count = 0

if st.button("Click me to test"):
    st.session_state.count += 1

st.write("Clicks:", st.session_state.count)
