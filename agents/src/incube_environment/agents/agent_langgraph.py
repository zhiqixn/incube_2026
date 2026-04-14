from pathlib import Path

from models.model_langgraph import llm
from configs.agents_config import (
    PLANNER_AGENT_PROMPT,
    GENERATION_AGENT_PROMPT,
    VALIDATION_AGENT_PROMPT,
)
from utils.utils_langgraph import (
    State,
    ValidationState,
)

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from utils.logger import get_logger

logger = get_logger()

# ---------------------------------------------------------------------------
# Skill references — read once at startup and injected into the planner
# system prompt so the local LLM receives all context without tool calls.
# ---------------------------------------------------------------------------
_SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "planner-skill"


def _read_ref(filename: str) -> str:
    try:
        return (_SKILL_DIR / filename).read_text()
    except Exception as exc:
        logger.warning("Could not read skill reference %s: %s", filename, exc)
        return ""


_SKILL_MD = _read_ref("SKILL.md")
_ACTION_FAMILIES = _read_ref("references/action_families.md")
_ACTION_LIBRARY = _read_ref("references/action_library.autonodyne.csv")
_PLANNER_SCHEMA = _read_ref("references/planner_output_schema.md")

_AUGMENTED_PLANNER_PROMPT = "\n\n---\n\n".join(
    part
    for part in [
        PLANNER_AGENT_PROMPT,
        f"## Planner Skill\n\n{_SKILL_MD}" if _SKILL_MD else "",
        f"## Action Families Reference\n\n{_ACTION_FAMILIES}" if _ACTION_FAMILIES else "",
        f"## Action Library (Autonodyne CSV)\n\n```\n{_ACTION_LIBRARY}\n```" if _ACTION_LIBRARY else "",
        f"## Planner Output Schema\n\n{_PLANNER_SCHEMA}" if _PLANNER_SCHEMA else "",
    ]
    if part
)

logger.info(
    "Planner system prompt built — skill_md=%d chars, action_families=%d chars, "
    "action_library=%d chars, schema=%d chars",
    len(_SKILL_MD),
    len(_ACTION_FAMILIES),
    len(_ACTION_LIBRARY),
    len(_PLANNER_SCHEMA),
)

# Augment the LLM with schema for structured output
validator_llm = llm.with_structured_output(ValidationState)


def _build_human_message(msg_content: str, uploaded_files: list) -> HumanMessage:
    """Build a HumanMessage, embedding uploaded files as multi-modal content blocks.

    Text/YAML/JSON files are inlined verbatim so the planner can read their
    contents directly.  Image files are embedded as base64 image_url blocks so
    vision-capable models can interpret maps or sensor imagery.  The user's
    text instructions are appended last.

    If no files are present the message degrades to a plain string, which is
    compatible with non-vision LLM backends.
    """
    if not uploaded_files:
        return HumanMessage(content=msg_content)

    content: list = []

    text_files = [f for f in uploaded_files if f.get("type") == "text"]
    image_files = [f for f in uploaded_files if f.get("type") == "image"]

    if text_files:
        file_names = ", ".join(f["name"] for f in text_files)
        content.append({
            "type": "text",
            "text": (
                f"The following mission specification file(s) have been uploaded "
                f"({file_names}). Use them as the authoritative source for all "
                f"mission parameters, fleet composition, and constraints.\n"
            ),
        })
        for f in text_files:
            content.append({
                "type": "text",
                "text": f"### {f['name']}\n\n```\n{f['content']}\n```",
            })

    for f in image_files:
        content.append({
            "type": "text",
            "text": f"Supporting image uploaded: {f['name']}",
        })
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{f['media_type']};base64,{f['data']}"},
        })

    content.append({"type": "text", "text": msg_content})

    return HumanMessage(content=content)


# Nodes
# TODO: Add structured output for output to include explanation
def planner(state: State):
    """Planner that generates a plan for the report"""

    logger.info("Instantiating Planner...")

    uploaded_files = state.get("uploaded_files") or []

    if state.get("valid") is False:
        msg_content = (
            f"Previous output was invalid. \n"
            f"Previous output: \n {state['output']} \n"
            f"Feedback: {state['feedback']} \n\n"
            f"Please revise the plan accordingly.\n\n"
            f"Instructions: {state['instructions']}"
        )
    else:
        msg_content = state["instructions"]

    # Build prior-turn messages so the planner has full conversational context
    history_messages = []
    for human_text, ai_text in (state.get("chat_history") or []):
        history_messages.append(HumanMessage(content=human_text))
        history_messages.append(AIMessage(content=ai_text))

    logger.info(
        "Invoking planner — history turns=%d, uploaded_files=%d, message content:\n%s",
        len(history_messages) // 2,
        len(uploaded_files),
        msg_content,
    )
    result = llm.invoke(
        [SystemMessage(content=_AUGMENTED_PLANNER_PROMPT)]
        + history_messages
        + [_build_human_message(msg_content, uploaded_files)]
    )
    logger.info("Plan generated:\n%s", result.content)
    return {"plan": result.content}


# TODO: Remove structured output
def generator(state: State):

    logger.info("Instantiating Generator...")

    completed_summary = llm.invoke(
        [
            SystemMessage(content=GENERATION_AGENT_PROMPT),
            HumanMessage(content=state["plan"]),
        ]
    )
    logger.info("Output generated:\n%s", completed_summary.content)
    return {"output": completed_summary.content}


def validator(state: State):

    logger.info("Instantiating Validator...")
    validation = validator_llm.invoke(
        [
            SystemMessage(content=VALIDATION_AGENT_PROMPT),
            HumanMessage(content=state["output"]),
        ]
    )
    logger.info("Validation result:\n%s", validation["valid"])

    # TODO: Save explanation to local folder if valid is true.
    return {"valid": validation["valid"], "feedback": validation["feedback"]}
