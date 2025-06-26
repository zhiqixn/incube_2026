from models.model import model
from tools import delegate_tasks, rag

user_cfgs = [
    {
        "name": "User",
        "description": (
            "User Agent used to initialize task" " to be performed by other agents"
        ),
        "user_topic_type": "User",
        "agent_topic_type": "Triage",
    }
]

autonomous_agents_cfgs = [
    {
        "name": "Triage",
        "description": "Triage agent to triage user tasks",
        "system_message": """You are a triage agent. You are responsible for triaging
user tasks and delegating them to the appropriate agents. You will receive user tasks
from the user agent and delegate them to the appropriate agents.

Your name: Triage
        """,
        "model": model,
        "delegate_tools": [delegate_tasks],
        "topics": ["RAG"],
        "broadcast_topic": "PLACEHOLDER_BROADCAST",
    },
    {
        "name": "RAG",
        "description": "RAG agent to answer user queries",
        "system_message": """You are a RAG agent. You are responsible for answering user
queries. You will receive user queries from the user agent and answer them using
retrieved information.""",
        "model": model,
        "delegate_tools": [],
        "tools": [rag],
        "topics": [],
    },
]
