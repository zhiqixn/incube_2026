import streamlit as st

st.set_page_config(
    page_title="ATHENA",
    page_icon="⚡",
    layout="wide",
)

st.markdown("""
<style>
/* ── Base: force dark background across all Streamlit layers ── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="block-container"],
.main, .block-container,
section.main > div {
    background-color: #0d1117 !important;
}

/* ── Hide default Streamlit header bar ── */
[data-testid="stHeader"],
header[data-testid="stHeader"] {
    background-color: #0d1117 !important;
    border-bottom: 1px solid #21262d !important;
}
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display: none !important;
}

/* ── Force ALL text to be readable on dark background ── */
html, body,
[data-testid="stAppViewContainer"] *,
[data-testid="stSidebar"] * {
    color: #e6edf3 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background-color: #161b22 !important;
    border-right: 1px solid #30363d !important;
}

/* ── Headers ── */
h1, h2, h3, h4, h5, h6 {
    color: #f0f6fc !important;
    letter-spacing: 0.04em;
}

/* ── Paragraphs, labels, spans ── */
p, span, label, div, li {
    color: #e6edf3 !important;
}

/* ── Container borders ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    background-color: #161b22 !important;
}

/* ── Markdown text inside containers ── */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span {
    color: #e6edf3 !important;
}

/* ── Caption ── */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {
    color: #8b949e !important;
    font-family: monospace !important;
}

/* ── Divider ── */
hr { border-color: #30363d !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

/* ── Table ── */
table {
    border-collapse: collapse !important;
    width: 100% !important;
    background-color: #161b22 !important;
}
th {
    background-color: #21262d !important;
    color: #58a6ff !important;
    padding: 8px 12px !important;
    border: 1px solid #30363d !important;
    font-family: monospace !important;
    letter-spacing: 0.05em !important;
}
td {
    padding: 8px 12px !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    vertical-align: top !important;
}
tr:nth-child(even) td {
    background-color: #0d1117 !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================

with st.sidebar:
    st.markdown("### ⚡ ATHENA")
    st.caption("Autonomous Mission Planning")
    st.divider()
    st.caption("Select a page above.")

# =========================
# MAIN CONTENT
# =========================

st.markdown("## ATHENA")
st.markdown(
    "<span style='font-family:monospace;font-size:0.9rem;color:#8b949e;letter-spacing:0.05em;'>"
    "Autonomous Task-planning and Heterogeneous Execution for Networked Assets"
    "</span>",
    unsafe_allow_html=True,
)
st.divider()

st.markdown("""
### The Problem

In traditional autonomous mission planning, engineers and operators must manually interpret mission
objectives, decompose them into tasks, assign those tasks to available platforms, and handcraft the
behaviour trees that govern execution. This process is slow, brittle, and difficult to scale across
changing missions and mixed fleets.

| Challenge | Impact |
|---|---|
| **Mission Translation Friction** | Significant time spent manually converting mission briefs, operating constraints, and asset availability into task structures and behaviour trees |
| **Brittleness in New Mission Contexts** | Handcrafted behaviour trees degrade quickly when missions, terrain, asset mixes, or operating conditions change |
| **Reconfiguration Latency** | Each new mission or update requires a time-consuming manual replanning and tree redesign cycle before execution can begin |
| **Expertise Dependency** | Successful mission decomposition depends heavily on experienced autonomy engineers, creating a bottleneck |
| **Limited Adaptability** | When assets fail or priorities shift, existing behaviour trees often require manual intervention rather than systematic replanning |
""")

st.divider()

st.markdown("### What ATHENA Does")
st.markdown(
    "ATHENA is an agentic system that autonomously translates mission intent into executable "
    "behaviour trees for heterogeneous autonomous platforms — drones, UGVs, and USVs."
)

c1, c2, c3 = st.columns(3)

with c1:
    with st.container(border=True):
        st.markdown(
            "<span style='font-family:monospace;font-size:0.75rem;letter-spacing:0.08em;"
            "color:#58a6ff;'>◈ MISSION-AWARE ANALYSIS</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:0.85rem;color:#8b949e;margin:6px 0 0 0;line-height:1.5;'>"
            "Automatically interprets mission briefs, operational goals, environmental constraints, "
            "rules, and platform capability profiles to generate a structured mission representation."
            "</p>",
            unsafe_allow_html=True,
        )
    with st.container(border=True):
        st.markdown(
            "<span style='font-family:monospace;font-size:0.75rem;letter-spacing:0.08em;"
            "color:#58a6ff;'>◎ BEHAVIOUR TREE SYNTHESIS</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:0.85rem;color:#8b949e;margin:6px 0 0 0;line-height:1.5;'>"
            "Decomposes objectives into tasks, allocates those tasks across available assets, "
            "and produces executable, parameterised behaviour trees."
            "</p>",
            unsafe_allow_html=True,
        )

with c2:
    with st.container(border=True):
        st.markdown(
            "<span style='font-family:monospace;font-size:0.75rem;letter-spacing:0.08em;"
            "color:#58a6ff;'>◆ CONSTRAINT VALIDATION</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:0.85rem;color:#8b949e;margin:6px 0 0 0;line-height:1.5;'>"
            "Validates generated behaviour trees against the provided task vocabulary, resource "
            "limits, mission rules, and safety constraints before output."
            "</p>",
            unsafe_allow_html=True,
        )
    with st.container(border=True):
        st.markdown(
            "<span style='font-family:monospace;font-size:0.75rem;letter-spacing:0.08em;"
            "color:#58a6ff;'>◉ ADAPTIVE RECONFIGURATION</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:0.85rem;color:#8b949e;margin:6px 0 0 0;line-height:1.5;'>"
            "Revises and regenerates behaviour trees when mission conditions change: asset loss, "
            "degraded communications, evolving objectives, or new environmental constraints."
            "</p>",
            unsafe_allow_html=True,
        )

with c3:
    with st.container(border=True):
        st.markdown(
            "<span style='font-family:monospace;font-size:0.75rem;letter-spacing:0.08em;"
            "color:#58a6ff;'>✦ EXPLAINABLE OUTPUT</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:0.85rem;color:#8b949e;margin:6px 0 0 0;line-height:1.5;'>"
            "Provides a clear rationale for how mission goals were decomposed, why tasks were "
            "assigned to particular platforms, and how the resulting behaviour trees satisfy "
            "mission requirements."
            "</p>",
            unsafe_allow_html=True,
        )
