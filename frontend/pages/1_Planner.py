# =========================
# 1_Planner.py — ATHENA Multi-Agent Mission Planner
# =========================

import sys
import base64
import streamlit as st
import psycopg2

sys.path.insert(0, "/agents/src/incube_environment")
from main_langgraph import invoke_agent  # noqa: E402

# =========================
# CONFIG
# =========================

DB_CONFIG = {
    "host": "database",
    "database": "chatdb",
    "user": "dstaapp",
    "password": "dstaapp"
}

# =========================
# DB FUNCTIONS
# =========================

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def create_conversation():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations DEFAULT VALUES RETURNING id")
    cid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return cid


def get_conversations():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM conversations ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def update_conversation_title(conversation_id, title):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE conversations SET title = %s WHERE id = %s",
        (title, conversation_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_messages(conversation_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_message, bot_response FROM messages WHERE conversation_id = %s",
        (conversation_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def save_message(conversation_id, user_msg, bot_msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (conversation_id, user_message, bot_response) VALUES (%s, %s, %s)",
        (conversation_id, user_msg, bot_msg)
    )
    conn.commit()
    cur.close()
    conn.close()


# =========================
# TEMPLATES
# =========================

_DOMAIN_CONSTRAINT_BLOCK = (
    "\n\n"
    "DOMAIN CONSTRAINTS — mandatory pre-assignment check:\n"
    "Before assigning any action to any asset, read the `fleet` section of the "
    "uploaded mission_spec and classify each asset by its `domain` field. Then "
    "enforce the following hard rules without exception:\n\n"
    "  AIR assets (domain: air — quadrotor, fixed_wing):\n"
    "    Allowed: aerial search (lawnmower / racetrack / spiral), aerial track, "
    "overwatch, takeoff, land, ReturnHome.\n"
    "    FORBIDDEN: sail, surface patrol, ground patrol, drive, any water-surface "
    "or terrain-traversal action.\n"
    "    Additional — fixed_wing only: CANNOT encircle, CANNOT hover, CANNOT use "
    "partition-based exploration nodes "
    "(exploration_AssignPartitions, exploration_PartitionSearchArea, "
    "exploration_SetPartitions, exploration_SetPartitionAssignments, "
    "exploration_SetPartitionCompletion, exploration_IsAllPartitionsComplete, "
    "exploration_IsPartitionComplete, exploration_IsPartitionSet).\n\n"
    "  SEA assets (domain: sea — usv):\n"
    "    Allowed: surface search (sector_scan, perimeter, shoreline_sweep), "
    "surface track, surface encircle, surface patrol, ReturnHome.\n"
    "    FORBIDDEN: fly, flyover, takeoff, land, go_to_altitude, "
    "override_altitude, arm_motors, any aerial or ground-traversal action. "
    "USV nodes controller_CommandArm, controller_CommandLand, "
    "controller_CommandTakeOff, controller_SetHome, controller_SetMode, and "
    "mission_OverridePoseAltitude are NOT available on USV — never assign them.\n\n"
    "  LAND assets (domain: land — ugv):\n"
    "    Allowed: ground search (corridor_sweep, perimeter, waypoint_patrol), "
    "ground track, ground encircle, ReturnHome.\n"
    "    FORBIDDEN: fly, flyover, takeoff, land, sail, any aerial or "
    "water-surface action. UGV CANNOT hand off targets (HandoffTarget node is "
    "NOT available on UGV). UGV nodes controller_CommandArm, "
    "controller_CommandLand, controller_CommandTakeOff, controller_SetHome, "
    "controller_SetMode, controller_SetPointLocal, and "
    "mission_OverridePoseAltitude are NOT available on UGV — never assign them.\n\n"
    "After building the fleet roster, produce a one-line domain summary for each "
    "asset in the format: `<id> | <domain> | <platform_type> | <allowed actions>` "
    "and verify no forbidden action appears in any asset's behavior chain before "
    "finalising the plan."
)

TEMPLATES = [
    {
        "title": "AREA SURVEILLANCE",
        "icon": "◈",
        "summary": "Systematic ISR coverage of the full AO using all available UAV assets with overlapping fields of view.",
        "prompt": (
            "Using the asset inventory and area of operations defined in the attached "
            "mission_spec_edited.yaml, plan an Intelligence, Surveillance and Reconnaissance "
            "(ISR) mission.\n\n"
            "Objective: Achieve comprehensive coverage of the designated AO. "
            "Air assets (UAVs) conduct aerial search using patterns appropriate to their "
            "platform type (lawnmower / spiral for quadrotors; racetrack / corridor_pass "
            "for fixed-wing). Sea assets (USVs) conduct surface search of the coastal and "
            "littoral sectors using sector_scan or shoreline_sweep — they do not fly. "
            "Land assets (UGVs) hold at staging or conduct ground-level corridor sweeps "
            "within traversable terrain — they do not fly or sail. "
            "Minimise coverage gaps across all domains.\n\n"
            "Constraints: Maintain minimum safe separation between air assets. "
            "All assets must be recoverable on task completion."
            + _DOMAIN_CONSTRAINT_BLOCK
        ),
    },
    {
        "title": "SEARCH & SECURE",
        "icon": "◎",
        "summary": "Multi-domain search for the designated target, positive ID, then UGV/USV perimeter hold.",
        "prompt": (
            "Using the asset inventory and area of operations defined in the attached "
            "mission_spec_edited.yaml, plan a Search and Secure mission.\n\n"
            "Objective: Deploy multi-domain assets to systematically search the AO for the "
            "designated target, confirm identification, and establish a secure perimeter. "
            "Air assets (UAVs) conduct aerial search and overwatch using aerial-only patterns "
            "and nodes — they stay airborne throughout. "
            "Sea assets (USVs) search and patrol the water surface using surface nodes only — "
            "they do not use any aerial actions. "
            "Land assets (UGVs) close for ground-level confirmation and perimeter hold using "
            "ground traversal actions — they do not fly or sail.\n\n"
            "Constraints: ROE requires positive identification before any UGV / USV advance. "
            "All assets RTB on task completion or on low-battery threshold."
            + _DOMAIN_CONSTRAINT_BLOCK
        ),
    },
    {
        "title": "COORDINATED STRIKE",
        "icon": "◆",
        "summary": "Synchronised UAV/UGV/USV strike package with terminal guidance, payload delivery and BDA.",
        "prompt": (
            "Using the asset inventory and area of operations defined in the attached "
            "mission_spec_edited.yaml, plan a coordinated strike mission.\n\n"
            "Objective: Synchronise assets across all present domains to locate, designate, "
            "and neutralise the priority target within the AO. "
            "Air assets (UAVs) provide aerial terminal guidance and battle damage assessment "
            "using aerial search, track, and overwatch nodes — they remain airborne. "
            "Sea assets (USVs) execute the surface approach and payload delivery via surface "
            "navigation and track nodes — they do not use any aerial nodes. "
            "Land assets (UGVs) execute the ground approach and payload delivery via ground "
            "traversal nodes — they do not fly or sail.\n\n"
            "Constraints: Strike package must achieve simultaneous arrival within the "
            "engagement window. Abort criteria: any asset loss or comms blackout exceeding "
            "30 seconds triggers immediate RTB for all remaining assets."
            + _DOMAIN_CONSTRAINT_BLOCK
        ),
    },
]


# =========================
# HELPERS
# =========================

def parse_agent_outputs(full_text: str) -> tuple[str, str, str]:
    """Split concatenated agent output into plan, BehaviorTree XML, and validation sections."""
    plan_text = full_text
    bt_xml = ""
    validation_text = ""

    # Locate BehaviorTree / XML block
    xml_open_markers = ["<?xml", "<root ", "<BehaviorTree"]
    xml_start = -1
    for marker in xml_open_markers:
        idx = full_text.find(marker)
        if idx != -1 and (xml_start == -1 or idx < xml_start):
            xml_start = idx

    if xml_start != -1:
        xml_close_markers = ["</root>", "</BehaviorTree>"]
        xml_end = -1
        for marker in xml_close_markers:
            idx = full_text.find(marker, xml_start)
            if idx != -1:
                xml_end = idx + len(marker)
                break

        if xml_end != -1:
            plan_text = full_text[:xml_start].strip()
            bt_xml = full_text[xml_start:xml_end].strip()
            validation_text = full_text[xml_end:].strip()
        else:
            plan_text = full_text[:xml_start].strip()
            bt_xml = full_text[xml_start:].strip()

    return plan_text, bt_xml, validation_text


def agent_badge(label: str, state: str) -> str:
    """Return HTML badge for an agent node status."""
    colors = {
        "idle":    ("#4a5568", "#a0aec0"),
        "running": ("#744210", "#f6ad55"),
        "done":    ("#1a4731", "#68d391"),
        "error":   ("#742a2a", "#fc8181"),
    }
    bg, fg = colors.get(state, colors["idle"])
    icons = {"idle": "○", "running": "◉", "done": "✓", "error": "✗"}
    icon = icons.get(state, "○")
    return (
        f'<span style="background:{bg};color:{fg};padding:6px 14px;'
        f'border-radius:4px;font-family:monospace;font-size:0.85rem;'
        f'font-weight:600;letter-spacing:0.05em;">'
        f'{icon} {label}</span>'
    )


def arrow_html() -> str:
    return '<span style="color:#8b949e;font-size:1.2rem;padding:0 8px;">→</span>'


# =========================
# PAGE CONFIG & CSS
# =========================

st.set_page_config(
    layout="wide",
    page_title="ATHENA Planner",
    page_icon="⚡",
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

/* ── Mission brief textarea ── */
textarea, input[type="text"] {
    background-color: #161b22 !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    font-family: monospace !important;
}
textarea::placeholder,
input[type="text"]::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: #8b949e !important;
    opacity: 1 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"],
[data-testid="stFileUploaderDropzone"] {
    background-color: #161b22 !important;
    border: 1px dashed #444c56 !important;
    border-radius: 6px !important;
    color: #e6edf3 !important;
}

/* ── Buttons ── */
[data-testid="stButton"] > button,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"] {
    background-color: #1f6feb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stButton"] > button:hover {
    background-color: #388bfd !important;
}
[data-testid="stButton"] > button:disabled {
    background-color: #21262d !important;
    color: #8b949e !important;
}

/* ── Container borders ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    background-color: #161b22 !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background-color: #0d1117 !important;
    border-bottom: 1px solid #30363d !important;
}
[data-testid="stTabs"] [role="tab"] {
    color: #8b949e !important;
    font-family: monospace !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
    background-color: transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #58a6ff !important;
    border-bottom: 2px solid #58a6ff !important;
}
[data-testid="stTabContent"] {
    background-color: #0d1117 !important;
}

/* ── Code / XML blocks ── */
code, pre,
[data-testid="stCode"],
[data-testid="stCode"] * {
    background-color: #161b22 !important;
    color: #79c0ff !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
}

/* ── Markdown text inside tabs / containers ── */
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
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE
# =========================

defaults = {
    "conversation_id": None,
    "mission_history": [],        # list of (user_msg, full_response)
    "current_plan": "",
    "current_bt": "",
    "current_validation": "",
    "current_explanation": "",
    "agent_states": {"PLANNER": "idle", "GENERATOR": "idle", "VALIDATOR": "idle"},
    "executing": False,
    "pending_brief": "",          # template text waiting to be injected into the textarea
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Inject template text into the textarea widget key BEFORE the widget renders
if st.session_state.pending_brief:
    st.session_state.mission_input_box = st.session_state.pending_brief
    st.session_state.pending_brief = ""

# =========================
# SIDEBAR — MISSION ARCHIVE
# =========================

with st.sidebar:
    st.markdown("### ⚡ ATHENA")
    st.caption("Multi-Agent Mission Planner")
    st.divider()

    if st.button("＋  New Mission", use_container_width=True):
        st.session_state.conversation_id = create_conversation()
        st.session_state.mission_history = []
        st.session_state.current_plan = ""
        st.session_state.current_bt = ""
        st.session_state.current_validation = ""
        st.session_state.current_explanation = ""
        st.session_state.agent_states = {"PLANNER": "idle", "GENERATOR": "idle", "VALIDATOR": "idle"}

    st.markdown("**Mission Archive**")
    for cid, title in get_conversations():
        label = title if title else f"Mission #{cid}"
        if st.button(label, key=f"conv_{cid}", use_container_width=True):
            st.session_state.conversation_id = cid
            st.session_state.mission_history = get_messages(cid)
            # Restore last outputs if available
            if st.session_state.mission_history:
                _, last_response = st.session_state.mission_history[-1]
                p, b, v = parse_agent_outputs(last_response)
                st.session_state.current_plan = p
                st.session_state.current_bt = b
                st.session_state.current_validation = v
            st.session_state.agent_states = {
                k: ("done" if st.session_state.current_plan else "idle")
                for k in ["PLANNER", "GENERATOR", "VALIDATOR"]
            }

# =========================
# MAIN LAYOUT
# =========================

st.markdown("## MISSION CONTROL")
st.divider()

# ── Mission Brief Input ──────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("#### MISSION BRIEF")

    # ── Template selector ────────────────────────────────────────────────────
    st.caption("TEMPLATES — select to pre-fill brief (upload mission_spec_edited.yaml before executing)")
    t1, t2, t3 = st.columns(3)
    for col, tpl, idx in zip([t1, t2, t3], TEMPLATES, range(3)):
        with col:
            with st.container(border=True):
                st.markdown(
                    f"<span style='font-family:monospace;font-size:0.75rem;"
                    f"letter-spacing:0.08em;color:#58a6ff;'>"
                    f"{tpl['icon']} {tpl['title']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<p style='font-size:0.78rem;color:#8b949e;margin:4px 0 8px 0;"
                    f"line-height:1.4;'>{tpl['summary']}</p>",
                    unsafe_allow_html=True,
                )
                if st.button("USE TEMPLATE", key=f"tpl_{idx}", use_container_width=True):
                    st.session_state.pending_brief = tpl["prompt"]
                    st.rerun()

    st.divider()
    brief_col, upload_col = st.columns([3, 1])

    with brief_col:
        mission_input = st.text_area(
            label="brief",
            label_visibility="collapsed",
            placeholder=(
                "Describe the mission objective, asset inventory (UAVs / UGVs / USVs), "
                "area of operations, and any constraints or rules of engagement..."
            ),
            height=130,
            key="mission_input_box",
        )

    with upload_col:
        uploaded = st.file_uploader(
            "Attach files",
            type=["txt", "yaml", "json", "png", "jpeg", "jpg"],
            accept_multiple_files=True,
            label_visibility="visible",
        )
        execute_btn = st.button(
            "▶  EXECUTE MISSION",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.executing,
        )

# ── Agent Pipeline Status ────────────────────────────────────────────────────
pipeline_placeholder = st.empty()

def render_pipeline():
    pipeline_placeholder.markdown(
        "<div style='padding:12px 0 8px 0;'>"
        + agent_badge("PLANNER", st.session_state.agent_states["PLANNER"])
        + arrow_html()
        + agent_badge("GENERATOR", st.session_state.agent_states["GENERATOR"])
        + arrow_html()
        + agent_badge("VALIDATOR", st.session_state.agent_states["VALIDATOR"])
        + "</div>",
        unsafe_allow_html=True,
    )

render_pipeline()

st.divider()

# ── Output Tabs ──────────────────────────────────────────────────────────────
tab_plan, tab_bt, tab_exp, tab_val, tab_log = st.tabs([
    "MISSION PLAN",
    "BEHAVIOR TREE XML",
    "EXPLANATION",
    "VALIDATION REPORT",
    "EXECUTION LOG",
])

plan_placeholder = tab_plan.empty()
bt_placeholder = tab_bt.empty()
exp_placeholder = tab_exp.empty()
val_placeholder = tab_val.empty()
log_container = tab_log.container()

# Render any pre-existing outputs (e.g. after loading from archive)
if st.session_state.current_plan:
    plan_placeholder.markdown(st.session_state.current_plan)
if st.session_state.current_bt:
    bt_placeholder.code(st.session_state.current_bt, language="xml")
if st.session_state.current_explanation:
    exp_placeholder.markdown(st.session_state.current_explanation)
if st.session_state.current_validation:
    val_placeholder.markdown(st.session_state.current_validation)

# Render execution log from history
with log_container:
    for i, (user_msg, _) in enumerate(st.session_state.mission_history):
        st.caption(f"Mission {i + 1}")
        st.markdown(f"> {user_msg[:200]}{'...' if len(user_msg) > 200 else ''}")

# =========================
# EXECUTE MISSION
# =========================

if execute_btn and mission_input.strip():
    st.session_state.executing = True

    if not st.session_state.conversation_id:
        st.session_state.conversation_id = create_conversation()

    is_first = not st.session_state.mission_history

    # Process file attachments
    uploaded_files = []
    display_images = {}

    for uf in (uploaded or []):
        ext = uf.name.rsplit(".", 1)[-1].lower()
        if ext in ("txt", "yaml", "json"):
            uploaded_files.append({
                "name": uf.name,
                "type": "text",
                "content": uf.read().decode("utf-8"),
            })
        elif ext in ("png", "jpeg", "jpg"):
            raw = uf.read()
            display_images[uf.name] = raw
            uploaded_files.append({
                "name": uf.name,
                "type": "image",
                "media_type": "image/jpeg" if ext in ("jpeg", "jpg") else "image/png",
                "data": base64.b64encode(raw).decode("utf-8"),
            })

    # Show attached files in log
    if display_images or uploaded_files:
        with log_container:
            for uf in uploaded_files:
                if uf["name"] in display_images:
                    st.image(display_images[uf["name"]], caption=uf["name"], width=160)
                else:
                    st.caption(f"📄 {uf['name']}")

    # Reset outputs
    st.session_state.current_plan = ""
    st.session_state.current_bt = ""
    st.session_state.current_validation = ""
    st.session_state.current_explanation = ""
    plan_placeholder.empty()
    bt_placeholder.empty()
    exp_placeholder.empty()
    val_placeholder.empty()

    # ── Run agent pipeline ──
    full_response = ""

    st.session_state.agent_states["PLANNER"] = "running"
    render_pipeline()

    try:
        for chunk, accumulated, explanation in invoke_agent(
            mission_input.strip(),
            chat_history=st.session_state.mission_history,
            uploaded_files=uploaded_files,
        ):
            full_response = accumulated
            plan_text, bt_xml, val_text = parse_agent_outputs(full_response)

            # Capture explanation emitted by the planner step
            if explanation:
                st.session_state.current_explanation = explanation
                exp_placeholder.markdown(explanation)

            # Update agent states based on what's populated
            if bt_xml and st.session_state.agent_states["PLANNER"] == "running":
                st.session_state.agent_states["PLANNER"] = "done"
                st.session_state.agent_states["GENERATOR"] = "running"
                render_pipeline()
            if val_text and st.session_state.agent_states["GENERATOR"] == "running":
                st.session_state.agent_states["GENERATOR"] = "done"
                st.session_state.agent_states["VALIDATOR"] = "running"
                render_pipeline()

            # Stream to panels
            if plan_text:
                plan_placeholder.markdown(plan_text)
            if bt_xml:
                bt_placeholder.code(bt_xml, language="xml")
            if val_text:
                val_placeholder.markdown(val_text)

    except Exception as exc:
        st.error(f"Agent pipeline error: {exc}")

    # Finalise agent states (runs even after an exception)
    plan_text, bt_xml, val_text = parse_agent_outputs(full_response)
    st.session_state.agent_states["PLANNER"] = "done" if plan_text else "error"
    st.session_state.agent_states["GENERATOR"] = "done" if bt_xml else (
        "idle" if not plan_text else "error"
    )
    st.session_state.agent_states["VALIDATOR"] = "done" if val_text else (
        "idle" if not bt_xml else "error"
    )

    st.session_state.current_plan = plan_text
    st.session_state.current_bt = bt_xml
    st.session_state.current_validation = val_text
    # current_explanation is already set during streaming; no re-parse needed

    # Persist — always write to DB regardless of agent success/failure
    file_names = ", ".join(f["name"] for f in uploaded_files)
    user_msg_for_db = f"[Files: {file_names}]\n\n{mission_input.strip()}" if uploaded_files else mission_input.strip()
    save_message(st.session_state.conversation_id, user_msg_for_db, full_response)
    st.session_state.mission_history.append((user_msg_for_db, full_response))

    if is_first:
        try:
            title = mission_input.strip()[:30]
            if len(mission_input.strip()) > 30:
                title += "..."
            update_conversation_title(st.session_state.conversation_id, title)
        except Exception:
            pass

    st.session_state.executing = False
    st.rerun()
