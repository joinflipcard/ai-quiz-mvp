import threading
import streamlit as st
import requests
import uuid

import threading
import streamlit as st
import requests
import uuid

BACKEND = "https://quiz.peterrazeghi.workers.dev"

DIAGRAMS = {

    # ================= BIOLOGY =================
    "cell": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Animal_cell_structure_en.svg",
    "photosynthesis": "https://upload.wikimedia.org/wikipedia/commons/3/3d/Photosynthesis_overview.svg",
    "dna": "https://upload.wikimedia.org/wikipedia/commons/8/87/DNA_double_helix_vertical.png",
    "mitosis": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Mitosis_stages.svg",
    "meiosis": "https://upload.wikimedia.org/wikipedia/commons/9/9c/Meiosis_Stages.svg",
    "ecosystem": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Food_web.svg",
    "energy flow": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Trophic_levels.svg",
    "nervous system": "https://upload.wikimedia.org/wikipedia/commons/1/1f/Nervous_system_diagram.svg",

    # ================= CHEMISTRY =================
    "periodic": "https://upload.wikimedia.org/wikipedia/commons/0/0a/Periodic_table_large.svg",
    "bond": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Ionic_and_covalent_bonds.png",
    "molecular shape": "https://upload.wikimedia.org/wikipedia/commons/0/0c/VSEPR_shapes.png",
    "reaction energy": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Reaction_coordinate_diagram.svg",
    "ph": "https://upload.wikimedia.org/wikipedia/commons/3/3b/PH_scale.svg",
    "gas law": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Gas_laws.svg",
    "atomic structure": "https://upload.wikimedia.org/wikipedia/commons/8/82/Bohr_atom_model.svg",

    # ================= PHYSICS =================
    "motion": "https://upload.wikimedia.org/wikipedia/commons/8/8c/Velocity_time_graph.png",
    "acceleration": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Acceleration_graph.svg",
    "force": "https://upload.wikimedia.org/wikipedia/commons/6/6b/Free_body_diagram2.svg",
    "magnetic": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Right_hand_rule_current_magnetic_field.svg",
    "electric field": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Electric_field_lines.svg",
    "circuit": "https://upload.wikimedia.org/wikipedia/commons/1/1c/Series_and_parallel_circuits.svg",
    "wave": "https://upload.wikimedia.org/wikipedia/commons/5/5d/Wave_interference.svg",
    "projectile": "https://upload.wikimedia.org/wikipedia/commons/7/7c/Projectile_motion.svg",

    # ================= EARTH SCIENCE =================
    "plate tectonics": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Plate_tectonics.svg",
    "water cycle": "https://upload.wikimedia.org/wikipedia/commons/9/9b/Water_cycle.svg",
    "rock cycle": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Rock_cycle.svg",
    "earth layers": "https://upload.wikimedia.org/wikipedia/commons/0/04/Earth_layers.svg",
    "volcano": "https://upload.wikimedia.org/wikipedia/commons/3/3c/Volcano_cross_section.svg",
    "weather fronts": "https://upload.wikimedia.org/wikipedia/commons/2/28/Weather_fronts.svg",

    # ================= MATH =================
    "slope": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Slope_rise_run.svg",
    "triangle": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Triangle_angles_sum.svg",
    "graph": "https://upload.wikimedia.org/wikipedia/commons/7/7f/Coordinate_plane.svg",
    "area": "https://upload.wikimedia.org/wikipedia/commons/0/0c/Area_shapes.svg",
    "probability": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Probability_tree.svg",
    "function": "https://upload.wikimedia.org/wikipedia/commons/6/6b/Function_graph.svg",

    # ================= TECHNOLOGY =================
    "algorithm": "https://upload.wikimedia.org/wikipedia/commons/8/8b/Flowchart_example.svg",
    "program flow": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Program_flowchart.svg",
    "database": "https://upload.wikimedia.org/wikipedia/commons/8/8d/Database_schema.svg",
    "internet": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Internet_packet_routing.svg",
    "client server": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Client-server-model.svg",

    # ================= ECONOMICS =================
    "supply": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Supply_and_demand.svg",
    "demand": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Supply_and_demand.svg",
    "aggregate": "https://upload.wikimedia.org/wikipedia/commons/4/44/Aggregate_demand_aggregate_supply.svg",
    "economy flow": "https://upload.wikimedia.org/wikipedia/commons/7/7a/Circular_flow_of_income.svg",
    "scarcity": "https://upload.wikimedia.org/wikipedia/commons/6/6c/Production_possibilities_frontier_curve.svg"
}

if st.button("Load All Topics"):
    r = requests.get(f"{BACKEND}/all-topics")
    topics = r.json()
    st.write(f"Total topics: {len(topics)}")
    st.dataframe(topics)

st.title("Knowledge")

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

            threading.Thread(target=prefetch_next, daemon=True).start()

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

    # 📊 STATIC CONCEPT DIAGRAM (fast & reliable)
    diagram = None
    topic_text = st.session_state.meta["topic"].lower()

    for key, url in DIAGRAMS.items():
        if key.lower() in topic_text:
            diagram = url
            break

    if diagram:
        st.image(diagram, use_container_width=True)
    else:
        st.caption("Concept diagram will appear when relevant 📊")

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

        threading.Thread(target=prefetch_next, daemon=True).start()
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

                threading.Thread(target=prefetch_next, daemon=True).start()
                st.rerun()

