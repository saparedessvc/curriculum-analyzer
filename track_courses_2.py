import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Curriculum Dependency Analyzer",
    layout="wide"
)

st.title("Curriculum Dependency Analyzer")

# =========================================================
# LOAD DATA
# =========================================================

st.sidebar.header("Entering Fall Year")

source = st.sidebar.radio(
    "Curriculum Source Year",
    [
        "2024",
        "2026"
    ]
)

if source == "2024":

    concentration = st.sidebar.selectbox(
        "Concentration",
        [
            "Mechanical Engineering",
            "Materials Engineering",
            "Enviromental Engineering"
        ]
    )

    file_map_conc = {
        "Mechanical Engineering": "courses_data_2024.csv",
        "Materials Engineering": "courses_data_mat_2024.csv",
        "Enviromental Engineering": "courses_data_env_2024.csv"
    }
    
    file_map_pre = {
        "Mechanical Engineering": "prerequisites.csv",
        "Materials Engineering": "prerequisites_mat.csv",
        "Enviromental Engineering": "prerequisites_env.csv"
    }

    file_conc = file_map_conc[concentration]
    file_pre = file_map_pre[concentration]

    courses_df = pd.read_csv(file_conc)
    prereq_df = pd.read_csv(file_pre)
else:

    concentration = st.sidebar.selectbox(
        "Concentration",
        [
            "Mechanical Engineering",
            "Materials Engineering",
            "Enviromental Engineering"
        ]
    )

    folder_map = {
        "Mechanical Engineering": "/curricula/Mechanical2026",
        "Materials Engineering": "/curricula/Materials2026",
        "Enviromental Engineering": "/curricula/Enviromental2026"
    }

    folder = folder_map[concentration]

    courses_df = pd.read_csv(folder_map[concentration])
    prereq_df = pd.read_csv("prerequisites.csv")

#courses_df = pd.read_csv("courses_data.csv")
#prereq_df = pd.read_csv("prerequisites.csv")

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Simulation")

failed_course = st.sidebar.selectbox(
    "Select failed course",
    sorted(courses_df["course"].tolist())
)

analyze = st.sidebar.button("Analyze")

# =========================================================
# BUILD GRAPH
# =========================================================

G = nx.DiGraph()

for _, row in courses_df.iterrows():
    G.add_node(
        row["course"],
        year=row["year"],
        semester=row["semester"]
    )

for _, row in prereq_df.iterrows():
    G.add_edge(row["prerequisite"], row["course"])

# =========================================================
# ANALYSIS
# =========================================================

if analyze:

    student_completed = {
        failed_course: "F"
    }

    passing_grades = ["A", "B", "C"]

    def can_take_course(graph, course):

        ancestors = nx.ancestors(graph, course)

        return failed_course not in ancestors

    blocked = set()

    for node in G.nodes():

        if not can_take_course(G, node):
            blocked.add(node)

    # =====================================================
    # COMPUTE LEVELS
    # =====================================================

    def compute_levels(G):

        levels = {}

        for node in nx.topological_sort(G):

            preds = list(G.predecessors(node))

            if not preds:
                levels[node] = 0
            else:
                levels[node] = max(levels[p] for p in preds) + 1

        return levels

    levels = compute_levels(G)

    semester_index = {
        "Fall": 0,
        "Spring": 1
    }

    year_order = {
        1: "Freshman",
        2: "Sophomore",
        3: "Junior",
        4: "Senior"
    }

    x_scale = 5
    vertical_spacing = 4.5
    depth_shift = 0.5

    pos = {}
    semester_groups = {}
    min_y = 0

    for node in G.nodes():

        meta = G.nodes[node]
        key = (meta["year"], meta["semester"])

        semester_groups.setdefault(key, []).append(node)

    for (year, sem), nodes in semester_groups.items():

        nodes = sorted(nodes)

        x = (((year - 1) * 2) + semester_index[sem]) * x_scale

        total = len(nodes)

        for i, node in enumerate(nodes):

            y = ((total / 2 - i) * vertical_spacing)

            y -= levels[node] * depth_shift

            min_y = max(min_y, y)

            pos[node] = (x, y)

    # =====================================================
    # DRAW GRAPH
    # =====================================================

    fig, ax = plt.subplots(figsize=(20, 10))

    node_colors = []

    for node in G.nodes():

        if node == failed_course:
            node_colors.append("red")

        elif node in blocked:
            node_colors.append("orange")

        else:
            node_colors.append("lightblue")

    nx.draw_networkx(
        G,
        pos,
        node_color=node_colors,
        node_size=2600,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=20,
        font_size=8,
        font_weight="bold",
        ax=ax
    )

    for node, (x, y) in pos.items():

        meta = G.nodes[node]

        ax.text(
            x,
            min_y + 2,
            f"{year_order[meta['year']]}\n{meta['semester']}",
            ha="center",
            fontsize=11,
            fontweight="bold"
        )

    ax.text(
        30,
        min(y for _, y in pos.values()) - 2,
        "RED = Failed\nORANGE = Blocked\nBLUE = Available",
        bbox=dict(facecolor="white", alpha=.9),
        fontsize=11
    )

    ax.axis("off")

    st.pyplot(fig)

    # =====================================================
    # REPORT
    # =====================================================

    st.subheader("Blocked Courses")

    report = []

    for c in sorted(blocked):

        meta = G.nodes[c]

        report.append({
            "Course": c,
            "Year": meta["year"],
            "Semester": meta["semester"]
        })

    report_df = pd.DataFrame(report)

    st.dataframe(
        report_df,
        use_container_width=True
    )

    csv = report_df.to_csv(index=False).encode()

    st.download_button(
        "Download Report",
        csv,
        "blocked_courses.csv",
        "text/csv"
    )