import threading
import streamlit as st
import requests
import uuid

if "mastered_topics" not in st.session_state:
    st.session_state.mastered_topics = set()

BACKEND = "https://quiz.peterrazeghi.workers.dev"

DIAGRAMS = {

# ================= BIOLOGY =================
"cell": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Animal_cell_structure_en.svg",
"cell structure": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Animal_cell_structure_en.svg",
"mitosis": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Mitosis_stages.svg",
"meiosis": "https://upload.wikimedia.org/wikipedia/commons/9/9c/Meiosis_Stages.svg",
"dna": "https://upload.wikimedia.org/wikipedia/commons/8/87/DNA_double_helix_vertical.png",
"photosynthesis": "https://upload.wikimedia.org/wikipedia/commons/3/3d/Photosynthesis_overview.svg",
"ecosystem": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Food_web.svg",
"energy flow": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Trophic_levels.svg",
"nervous system": "https://upload.wikimedia.org/wikipedia/commons/1/1f/Nervous_system_diagram.svg",

# ================= CHEMISTRY =================
"periodic table": "https://upload.wikimedia.org/wikipedia/commons/0/0a/Periodic_table_large.svg",
"atomic structure": "https://upload.wikimedia.org/wikipedia/commons/8/82/Bohr_atom_model.svg",
"bond": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Ionic_and_covalent_bonds.png",
"molecular shape": "https://upload.wikimedia.org/wikipedia/commons/0/0c/VSEPR_shapes.png",
"reaction energy": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Reaction_coordinate_diagram.svg",
"ph scale": "https://upload.wikimedia.org/wikipedia/commons/3/3b/PH_scale.svg",
"gas laws": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Gas_laws.svg",

# ================= PHYSICS =================
"motion": "https://upload.wikimedia.org/wikipedia/commons/8/8c/Velocity_time_graph.png",
"acceleration": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Acceleration_graph.svg",
"force": "https://upload.wikimedia.org/wikipedia/commons/6/6b/Free_body_diagram2.svg",
"projectile": "https://upload.wikimedia.org/wikipedia/commons/7/7c/Projectile_motion.svg",
"electric field": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Electric_field_lines.svg",
"circuit": "https://upload.wikimedia.org/wikipedia/commons/1/1c/Series_and_parallel_circuits.svg",
"wave": "https://upload.wikimedia.org/wikipedia/commons/5/5d/Wave_interference.svg",

# ================= EARTH SCIENCE =================
"plate tectonics": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Plate_tectonics.svg",
"earth layers": "https://upload.wikimedia.org/wikipedia/commons/0/04/Earth_layers.svg",
"rock cycle": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Rock_cycle.svg",
"water cycle": "https://upload.wikimedia.org/wikipedia/commons/9/9b/Water_cycle.svg",
"volcano": "https://upload.wikimedia.org/wikipedia/commons/3/3c/Volcano_cross_section.svg",

# ================= MATH =================
"graph": "https://upload.wikimedia.org/wikipedia/commons/7/7f/Coordinate_plane.svg",
"slope": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Slope_rise_run.svg",
"triangle": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Triangle_angles_sum.svg",
"probability": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Probability_tree.svg",

# ================= ECONOMICS =================
"supply": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Supply_and_demand.svg",
"demand": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Supply_and_demand.svg",
"scarcity": "https://upload.wikimedia.org/wikipedia/commons/6/6c/Production_possibilities_frontier_curve.svg",

# ================= TECHNOLOGY =================
"algorithm": "https://upload.wikimedia.org/wikipedia/commons/8/8b/Flowchart_example.svg",
"database": "https://upload.wikimedia.org/wikipedia/commons/8/8d/Database_schema.svg",
"internet": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Internet_packet_routing.svg",
}

VISUAL_DOMAINS = [
    "biology",
    "chemistry",
    "physics",
    "geography",
    "earth",
    "mathematics",
    "math",
    "economics",
    "technology"
]

st.title("Knowledge")

GOAL = 20  # adjust later if you want

# ✅ CREATE USER FIRST (must come before API calls)
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# ✅ REAL DB MASTERY FETCH
def fetch_mastered_count():
    r = requests.get(
        f"{BACKEND}/mastered-count",
        params={"user_id": st.session_state.user_id},
        timeout=10
    )
    return r.json()["count"]

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

    # 🧠 Question (safe render)
    st.markdown(q.get("question", ""))

    # 🖼️ GUARANTEED SAFE IMAGE RENDER (no broken placeholders ever)
    image_url = q.get("image")

    if isinstance(image_url, str) and image_url.startswith("https://upload.wikimedia.org/"):
        st.image(image_url, use_container_width=True)

    # ------------------ answers ------------------

    if not st.session_state.show_feedback:

        choices = q.get("choices", {})

        for letter, text in choices.items():

            if st.button(
                f"{letter}. {text}",
                key=f"{st.session_state.index}-{letter}",
                use_container_width=True
            ):

                correct = (letter == q.get("correct"))

                post(
                    f"{BACKEND}/submit-answer",
                    {
                        "user_id": st.session_state.user_id,
                        "field_id": st.session_state.meta["field_id"],
                        "topic_id": st.session_state.meta["topic_id"],
                        "correct": correct
                    }
                )

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
