from models.model import *
from tools import *


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
        "name": "PLACEHOLDER",
        "description": "",
        "system_message": """""",
        "model": model,
        "delegate_tools": [delegate_tasks],
        "topics": [],
    },
]
