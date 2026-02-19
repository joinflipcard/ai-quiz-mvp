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

# ── BASIC STYLING (POLISHED) ─────────────────────────────────────
st.markdown("""
<style>
/* page spacing */
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}

/* headings */
h2, h3 {
    margin-top: 0.6rem;
    margin-bottom: 0.4rem;
    font-weight: 600;
}

/* question text */
.quiz-question {
    font-size: 1.35rem;
    font-weight: 600;
    margin-bottom: 20px;
    line-height: 1.45;
    word-break: break-word;
}

/* radio spacing */
.stRadio > div {
    gap: 8px;
}

/* allow long answers to wrap cleanly */
.stRadio label {
    white-space: normal !important;
    word-break: break-word !important;
    overflow-wrap: anywhere !important;
    line-height: 1.5 !important;
    margin-bottom: 6px !important;
}

/* buttons */
.stButton button {
    margin-top: 6px;
    border-radius: 14px;
    height: 48px;
    font-weight: 600;
}

/* primary card */
.main-card {
    background: #ffffff;
    padding: 26px;
    border-radius: 20px;
    box-shadow: 0 8px 22px rgba(0,0,0,.08);
    margin-bottom: 20px;
}

/* feedback blocks */
.feedback-good {
    background: #e9fff3;
    padding: 16px;
    border-radius: 14px;
    font-weight: 600;
    margin-top: 16px;
}

.feedback-bad {
    background: #ffecec;
    padding: 16px;
    border-radius: 14px;
    font-weight: 600;
    margin-top: 16px;
}

/* info explanation spacing */
.stAlert {
    margin-top: 14px;
}

/* reduce emoji visual weight */
.feedback-good,
.feedback-bad {
    letter-spacing: 0.2px;
}

/* mobile safety */
@media (max-width: 640px) {
    .quiz-question {
        font-size: 1.25rem;
    }

    .stButton button {
        height: 46px;
    }
}
</style>
""", unsafe_allow_html=True)

# ── MAIN CONTENT CARD WRAPPER ─────────────────────────────────────
# Single place where questions / placeholder / answers render

def begin_main_card():
    st.markdown(
        """
        <div style="
            background:#ffffff;
            padding:24px;
            border-radius:18px;
            box-shadow:0 6px 18px rgba(0,0,0,.08);
            margin-top:18px;
            margin-bottom:18px;
        ">
        """,
        unsafe_allow_html=True
    )

def end_main_card():
    st.markdown("</div>", unsafe_allow_html=True)

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

# ── MAIN CARD: DEFAULT PLACEHOLDER + PRIMARY CONTROLS ──────────
# Single, clean entry point. No redundancy.

# ── Persistent user defaults (set once, reused everywhere) ────
if "user_mode" not in st.session_state:
    st.session_state.user_mode = "quiz"        # quiz | tutorial

if "user_difficulty" not in st.session_state:
    st.session_state.user_difficulty = "medium"  # easy | medium | hard


# ── TOP CONTROLS: MODE + DIFFICULTY (SLIDING STYLE) ────────────
top_cols = st.columns([1.2, 1.2, 3.6])

with top_cols[0]:
    st.session_state.user_mode = st.selectbox(
        "Mode",
        ["Quiz", "Tutorial"],
        index=0 if st.session_state.user_mode == "quiz" else 1,
        label_visibility="collapsed"
    ).lower()

with top_cols[1]:
    st.session_state.user_difficulty = st.selectbox(
        "Difficulty",
        ["Easy", "Medium", "Hard"],
        index=["easy", "medium", "hard"].index(st.session_state.user_difficulty),
        label_visibility="collapsed"
    ).lower()

with top_cols[2]:
    st.empty()


# ── MAIN CARD PLACEHOLDER (same location as questions) ─────────
if (
    not st.session_state.get("quiz")
    and not st.session_state.get("free_text_mode")
    and not st.session_state.get("selected_mode")
):
    begin_main_card()

    st.markdown(
        "<div class='quiz-question'>Ready when you are</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='font-size:1.05rem;color:#555;margin-top:10px;'>"
        "Choose a category, enter a topic, or start a concept challenge to begin."
        "</p>",
        unsafe_allow_html=True
    )

    end_main_card()


# ── PRIMARY SELECTION BAR (HORIZONTAL, CLEAN) ──────────────────
# All entry paths live here. No duplicate CTAs elsewhere.

# ── Blue primary button styling (Chrome-extension style) ──────
st.markdown(
    """
    <style>
    .stButton > button {
        background-color: #2563eb; /* clean chrome-style blue */
        color: white;
        border: none;
        border-radius: 14px;
        height: 48px;
        font-weight: 600;
        transition: background-color 0.15s ease;
    }
    .stButton > button:hover {
        background-color: #1e4fd8;
        color: white;
    }
    .stButton > button:active {
        background-color: #1a45bd;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ── Mode selection handler (FULL RESET – FIXES BUG) ────────────
def select_mode(mode):
    # navigation
    st.session_state.selected_mode = mode
    st.session_state.quiz = []
    st.session_state.index = 0
    st.session_state.round_correct = 0

    # feedback (quiz + concept)
    st.session_state.show_feedback = False
    st.session_state.last_correct = False
    st.session_state.last_explanation = ""
    st.session_state.last_verdict = ""

    # concept / free-text mode
    st.session_state.free_text_mode = False
    st.session_state.is_grading = False

    # 🔥 explain-more state (CRITICAL RESET)
    st.session_state.show_simple_explanation = False
    st.session_state.simple_explanation = ""
    st.session_state.is_simplifying = False

    # remove lingering input
    if "free_text_answer" in st.session_state:
        del st.session_state["free_text_answer"]


# ── BUTTON GRID ───────────────────────────────────────────────
row1 = st.columns(4)
row2 = st.columns(2)

with row1[0]:
    if st.button("General Knowledge", use_container_width=True):
        select_mode("general")

with row1[1]:
    if st.button("Sports", use_container_width=True):
        select_mode("sports")

with row1[2]:
    if st.button("Science", use_container_width=True):
        select_mode("science")

with row1[3]:
    if st.button("History", use_container_width=True):
        select_mode("history")

with row2[0]:
    if st.button("Pick a Topic", use_container_width=True):
        select_mode("custom")

with row2[1]:
    if st.button("Concepts", use_container_width=True):
        select_mode("concept")

# ── STATE INITIALIZATION ────────────────────────────────────────
defaults = {
    "quiz": [],
    "index": 0,
    "meta": {},
    "error": None,
    "show_feedback": False,
    "last_correct": False,
    "last_explanation": "",
    "last_verdict": "",
    "next_quiz": [],
    "next_meta": {},
    "round_correct": 0,
    "selected_mode": None,

    # ── Explain more simply feature ──
    "show_simple_explanation": False,
    "simple_explanation": "",
    "is_simplifying": False,
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
            "user_id": st.session_state.user_id
        }
    )
    if err or not quiz_data or "questions" not in quiz_data:
        return
    st.session_state.next_quiz = quiz_data["questions"]


# ── MODE EXIT HELPERS ───────────────────────────────────────────
# Ensures Concept Challenge does NOT block quizzes

def exit_concept_mode():
    st.session_state.free_text_mode = False
    st.session_state.is_grading = False
    st.session_state.show_feedback = False

    # Remove lingering widget state
    if "free_text_answer" in st.session_state:
        del st.session_state["free_text_answer"]

# ── START QUIZ FUNCTION ─────────────────────────────────────────
def start_quiz(topic, difficulty, num_questions=4, is_adaptive=False, mode="quiz"):
    with st.spinner("Creating your quiz..."):
        payload = {
            "topic": topic,
            "start_difficulty": difficulty,
            "num_questions": num_questions,
            "user_id": st.session_state.user_id,
            "mode": mode
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


# ── CATEGORY AUTO-START (NO EXTRA CLICKS) ───────────────────────
# This MUST be placed AFTER start_quiz is defined

category_topic_map = {
    "general": "general knowledge",
    "sports": "sports",
    "science": "science",
    "history": "history",
}

selected = st.session_state.get("selected_mode")

if (
    selected in category_topic_map
    and not st.session_state.quiz
    and not st.session_state.get("free_text_mode")
):
    topic = category_topic_map[selected]
    mode = st.session_state.user_mode
    difficulty = st.session_state.user_difficulty

    if start_quiz(
        topic=topic,
        difficulty=difficulty,
        num_questions=4 if mode == "quiz" else 6,
        mode=mode
    ):
        st.rerun()

# ── PICK A TOPIC FLOW ───────────────────────────────────────────

if st.session_state.get("selected_mode") == "custom":

    begin_main_card()

    st.markdown("<div class='quiz-question'>Pick a topic</div>", unsafe_allow_html=True)

    custom_topic = st.text_input(
        "Enter any topic",
        placeholder="e.g. World Cup history, neuroscience, Taylor Swift eras…",
        key="custom_topic_input"
    )

    if custom_topic.strip():

        if st.button(
            f"Start {st.session_state.user_mode.title()}",
            use_container_width=True,
            key="start_custom_topic"
        ):
            if start_quiz(
                topic=custom_topic.strip(),
                difficulty=st.session_state.user_difficulty,
                num_questions=4 if st.session_state.user_mode == "quiz" else 6,
                mode=st.session_state.user_mode
            ):
                st.rerun()

    end_main_card()

# ── CONCEPT CHALLENGE ENTRY ─────────────────────────────────────

if st.session_state.get("selected_mode") == "concept":

    begin_main_card()

    st.markdown("<div class='quiz-question'>Concept Challenge</div>", unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:1.05rem;color:#555;'>"
        "Explain ideas in your own words. No multiple choice."
        "</p>",
        unsafe_allow_html=True
    )

    if st.button("Start concept challenge", use_container_width=True):

        # ── CLEAR ANY PRIOR QUIZ / FEEDBACK STATE ─────────
        st.session_state.quiz = []
        st.session_state.index = 0
        st.session_state.round_correct = 0

        st.session_state.show_feedback = False
        st.session_state.last_correct = False
        st.session_state.last_verdict = ""
        st.session_state.last_explanation = ""

        # ── CLEAR EXPLAIN-MORE STATE (CRITICAL) ───────────
        st.session_state.show_simple_explanation = False
        st.session_state.simple_explanation = ""
        st.session_state.is_simplifying = False

        # ── CLEAR FREE-TEXT STATE ─────────────────────────
        st.session_state.free_text_mode = False
        st.session_state.is_grading = False

        if "free_text_answer" in st.session_state:
            del st.session_state["free_text_answer"]

        # ── FETCH NEXT CONCEPT ───────────────────────────
        with st.spinner("Selecting next concept..."):
            data, err = post(
                f"{BACKEND}/next-concept",
                {"user_id": st.session_state.user_id}
            )

        if err:
            st.error(f"Failed to load concept: {err}")
            end_main_card()
            st.stop()

        if data.get("done"):
            st.success("You’ve mastered all available concepts.")
            end_main_card()
            st.stop()

        # ── SET NEW CONCEPT STATE ────────────────────────
        st.session_state.concept_id = data["concept_id"]
        st.session_state.concept_name = data["concept"]
        st.session_state.core_idea = data["core_idea"]
        st.session_state.ideal_explanation = data["ideal_explanation"]
        st.session_state.concept_difficulty = data["difficulty"]

        # ── ACTIVATE FREE-TEXT MODE (AFTER RESET) ────────
        st.session_state.free_text_mode = True
        st.session_state.is_grading = False
        st.session_state.show_feedback = False

        st.rerun()

    end_main_card()

# ── MAIN CONTENT CARD WRAPPER ─────────────────────────────────────
# Ensures questions, answers, feedback always render in one place

def begin_main_card():
    st.markdown(
        """
        <div style="
            background:#ffffff;
            padding:24px;
            border-radius:18px;
            box-shadow:0 6px 18px rgba(0,0,0,.08);
            margin-top:18px;
            margin-bottom:18px;
        ">
        """,
        unsafe_allow_html=True
    )

def end_main_card():
    st.markdown("</div>", unsafe_allow_html=True)

# ── FREE-TEXT QUESTION MODE ────────────────────────────────────
# Uses native keyboard dictation on iOS (no custom mic needed)

if st.session_state.get("free_text_mode"):

    begin_main_card()

    concept = st.session_state.get("concept_name", "Concept")
    core_idea = st.session_state.get("core_idea", "")
    ideal_explanation = st.session_state.get("ideal_explanation", "")

    # ── CONCEPT PROMPT ─────────────────────────────
    st.markdown(
        f"<div class='quiz-question'>{concept}</div>",
        unsafe_allow_html=True
    )

    st.markdown("### Your answer")

    answer_text = st.text_area(
        "Explain in your own words:",
        key="free_text_answer",
        height=140,
        placeholder="Type your answer or use the keyboard mic to speak…"
    )

    # ── SUBMIT (allow blank) ───────────────────────
    if st.button("Submit answer", use_container_width=True, key="submit_concept"):
        st.session_state.is_grading = True
        st.rerun()

    # ── GRADING STATE ──────────────────────────────
    if st.session_state.get("is_grading"):

        with st.spinner("🧠 Evaluating your answer..."):
            try:
                r = requests.post(
                    f"{BACKEND}/check-answer",
                    json={
                        "user_id": st.session_state.user_id,
                        "concept_id": st.session_state.concept_id,
                        "concept": concept,
                        "core_idea": core_idea,
                        "ideal_explanation": ideal_explanation,
                        # ✅ Always send non-empty text
                        "answer_text": (
                            st.session_state.free_text_answer.strip()
                            if st.session_state.free_text_answer.strip()
                            else "I don't know."
                        )
                    },
                    timeout=30
                )
                r.raise_for_status()
                result = r.json()

            except Exception as e:
                st.error(f"Grading failed: {str(e)}")
                st.session_state.is_grading = False
                end_main_card()
                st.stop()

        # ── STORE RESULT ───────────────────────────
        st.session_state.last_correct = result.get("correct", False)
        st.session_state.last_explanation = result.get("ideal_explanation", "")
        st.session_state.last_verdict = result.get("verdict", "")
        st.session_state.show_feedback = True
        st.session_state.is_grading = False
        st.rerun()

    # ── FEEDBACK ──────────────────────────────────
    if st.session_state.get("show_feedback"):

        if st.session_state.last_correct:
            st.markdown("<div class='feedback-good'>✅ Correct</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='feedback-bad'>❌ Not quite</div>", unsafe_allow_html=True)

        if st.session_state.last_verdict:
            st.info(st.session_state.last_verdict)

        if st.session_state.last_explanation:
            st.markdown("**Ideal explanation:**")
            st.markdown(st.session_state.last_explanation)

        # 👉 Explain more simply
        if st.button(
            "Explain this more simply",
            use_container_width=True,
            key="explain_more_btn"
        ):
            st.session_state.is_simplifying = True
            st.session_state.show_simple_explanation = False

        # EXIT CONCEPT MODE
        if st.button("Next →", use_container_width=True, key="next_concept"):
            st.session_state.free_text_mode = False
            st.session_state.show_simple_explanation = False
            st.session_state.is_simplifying = False

            if "free_text_answer" in st.session_state:
                del st.session_state["free_text_answer"]

            st.session_state.show_feedback = False
            st.rerun()

    # ── SIMPLER EXPLANATION FLOW ───────────────────
# ⚠️ Fetch is fine, render MUST be gated by feedback

if st.session_state.get("is_simplifying"):

    with st.spinner("Breaking it down more simply..."):
        try:
            r = requests.post(
                f"{BACKEND}/explain-better",
                json={
                    "concept": st.session_state.concept_name,
                    "core_idea": st.session_state.core_idea,
                    "ideal_explanation": st.session_state.ideal_explanation,
                    "difficulty": st.session_state.concept_difficulty
                },
                timeout=30
            )
            r.raise_for_status()
            data = r.json()

            st.session_state.simple_explanation = data.get("simple_explanation", "")
            st.session_state.show_simple_explanation = True
            st.session_state.is_simplifying = False

        except Exception as e:
            st.error(f"Could not simplify explanation: {str(e)}")
            st.session_state.is_simplifying = False


# ── RENDER (STRICTLY AFTER FEEDBACK) ───────────
if (
    st.session_state.get("show_feedback")
    and st.session_state.get("show_simple_explanation")
):
    st.markdown("### Simpler explanation")
    st.success(st.session_state.simple_explanation)

end_main_card()

# ── QUIZ DISPLAY ────────────────────────────────────────────────
# 🚫 IMPORTANT: Do NOT render MCQs while in Concept Challenge mode

if (
    not st.session_state.get("free_text_mode")
    and st.session_state.quiz
    and st.session_state.index < len(st.session_state.quiz)
):

    begin_main_card()

    q = st.session_state.quiz[st.session_state.index]

    # ── QUESTION ─────────────────────────────
    st.markdown(
        f"<div class='quiz-question'>{q.get('question', '—')}</div>",
        unsafe_allow_html=True
    )

    choices = q.get("choices", {})
    if not isinstance(choices, dict):
        end_main_card()
        st.session_state.index += 1
        st.rerun()

    option_items = [(k, v) for k, v in choices.items()]
    option_labels = [f"{k}. {v}" for k, v in option_items]

    # ── ANSWER OPTIONS ───────────────────────
    if len(option_labels) >= 4:
        col1, col2 = st.columns(2)

        with col1:
            left_opts = option_labels[: len(option_labels) // 2]
            left_choice = st.radio(
                " ",
                left_opts,
                index=None,
                key=f"radio_left_{st.session_state.index}"
            )

        with col2:
            right_opts = option_labels[len(option_labels) // 2 :]
            right_choice = st.radio(
                "  ",
                right_opts,
                index=None,
                key=f"radio_right_{st.session_state.index}"
            )

        selected_answer = left_choice or right_choice

    else:
        selected_answer = st.radio(
            "Select an answer:",
            option_labels,
            index=None,
            key=f"radio_{st.session_state.index}"
        )

    # ── SUBMIT ───────────────────────────────
    if st.button(
        "Submit answer",
        use_container_width=True,
        key=f"submit_quiz_{st.session_state.index}"
    ):
        if not selected_answer:
            st.warning("Please select an answer first")
            end_main_card()
            st.stop()

        letter = selected_answer.split(".", 1)[0].strip().upper()
        correct_letter = str(q.get("correct", "")).strip().upper()
        is_correct = (letter == correct_letter)

        try:
            requests.post(
                f"{BACKEND}/submit-answer",
                json={
                    "user_id": st.session_state.user_id,
                    "field_id": st.session_state.meta.get("field_id"),
                    "topic_id": st.session_state.meta.get("topic_id"),
                    "question_id": q.get("id"),
                    "question_text": q.get("question"),
                    "correct": is_correct
                },
                timeout=5
            )
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

    # ── FEEDBACK ─────────────────────────────
    if st.session_state.show_feedback:

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

        if st.button(
            "Next question →",
            use_container_width=True,
            key=f"next_quiz_{st.session_state.index}"
        ):
            st.session_state.show_feedback = False
            st.session_state.index += 1
            st.rerun()

    end_main_card()


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
                    start_quiz(
                        data["topic"],
                        data.get("start_difficulty", selected_difficulty),
                        num_questions=3,
                        is_adaptive=True
                    )

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
                    start_quiz(topic, selected_difficulty, num_questions=4)

                threading.Thread(
                    target=prefetch_next,
                    args=(topic, 4, selected_difficulty),
                    daemon=True
                ).start()
                st.rerun()