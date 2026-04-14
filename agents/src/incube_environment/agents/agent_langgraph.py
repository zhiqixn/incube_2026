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

from langchain_core.messages import HumanMessage, SystemMessage
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


# Nodes
# TODO: Add structured output for output to include explanation
def planner(state: State):
    """Planner that generates a plan for the report"""

    logger.info("Instantiating Planner...")

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

    logger.info("Invoking planner with message content:\n%s", msg_content)
    result = llm.invoke(
        [
            SystemMessage(content=_AUGMENTED_PLANNER_PROMPT),
            HumanMessage(content=msg_content),
        ]
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
