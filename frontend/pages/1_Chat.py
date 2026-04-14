# =========================
# app.py (Single Streamlit App with Backend Logic + PostgreSQL + vLLM)
# =========================

import sys
import base64
import streamlit as st
import psycopg2

# ---------------------------------------------------------------------------
# Make the agents package importable.  In Docker, ../agents is mounted at
# /agents; locally adjust this path as needed.
# ---------------------------------------------------------------------------
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

    return rows  # list of (id, title) tuples


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


# (stream_llm_response removed — replaced by planner_agent.create_plan + stream_execution)

# =========================
# STREAMLIT UI
# =========================

st.set_page_config(layout="wide")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []


# Sidebar
st.sidebar.title("Conversations")

if st.sidebar.button("New Conversation"):
    st.session_state.conversation_id = create_conversation()
    st.session_state.messages = []


# Load conversations
for cid, title in get_conversations():
    label = title if title else f"Conversation {cid}"
    if st.sidebar.button(label, key=f"conv_{cid}"):
        st.session_state.conversation_id = cid
        st.session_state.messages = get_messages(cid)


st.title("💬 ATHENA Planning Assistant")


# Display chat
for user_msg, bot_msg in st.session_state.messages:
    st.chat_message("user").write(user_msg)
    st.chat_message("assistant").write(bot_msg)


# Input (accept_file puts the attachment button inside the chat box, like ChatGPT)
if result := st.chat_input(
    "Type your message...",
    accept_file="multiple",
    file_type=["txt", "yaml", "json", "png", "jpeg", "jpg"],
):
    prompt = result.text or ""
    if not st.session_state.conversation_id:
        st.session_state.conversation_id = create_conversation()

    is_first_message = not st.session_state.messages

    # Process uploaded files into agent-facing dicts; keep raw bytes for display
    uploaded_files = []
    display_images = {}  # filename -> bytes, for rendering thumbnails

    for uf in (result.files or []):
        ext = uf.name.rsplit(".", 1)[-1].lower()
        if ext in ("txt", "yaml", "json"):
            uploaded_files.append({
                "name": uf.name,
                "type": "text",
                "content": uf.read().decode("utf-8"),
            })
        elif ext in ("png", "jpeg", "jpg"):
            raw_bytes = uf.read()
            display_images[uf.name] = raw_bytes
            uploaded_files.append({
                "name": uf.name,
                "type": "image",
                "media_type": "image/jpeg" if ext in ("jpeg", "jpg") else "image/png",
                "data": base64.b64encode(raw_bytes).decode("utf-8"),
            })

    # Show user message (with any file attachments)
    with st.chat_message("user"):
        st.write(prompt)
        for uf in uploaded_files:
            if uf["name"] in display_images:
                st.image(display_images[uf["name"]], caption=uf["name"], width=200)
            else:
                st.caption(f"📄 {uf['name']}")

    with st.chat_message("assistant"):
        text_placeholder = st.empty()
        full_response = ""

        for chunk, accumulated in invoke_agent(prompt):
            full_response = accumulated
            text_placeholder.write(full_response)

    # Persist to DB — embed file names in the user message for history readability
    if uploaded_files:
        file_names = ", ".join(f["name"] for f in uploaded_files)
        user_msg_for_db = f"[Files: {file_names}]\n\n{prompt}"
    else:
        user_msg_for_db = prompt

    save_message(st.session_state.conversation_id, user_msg_for_db, full_response)

    if is_first_message:
        try:
            title = prompt.strip()[:30]
            if len(prompt.strip()) > 30:
                title += "..."
            update_conversation_title(st.session_state.conversation_id, title)
        except Exception:
            pass  # title generation is best-effort; sidebar falls back to "Conversation N"

    st.session_state.messages.append((user_msg_for_db, full_response))
