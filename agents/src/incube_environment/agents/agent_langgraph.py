from pathlib import Path

from tools.tool_langgraph import get_reddit_company_news, get_YF_data_tool
from models.model_langgraph import llm
from configs.agents_config import (
    PLANNER_AGENT_PROMPT,
    GENERATION_AGENT_PROMPT,
    VALIDATION_AGENT_PROMPT,
)
from typing import Literal
from utils.utils_langgraph import (
    State,
    Output,
    ValidationState,
)

from langchain.messages import HumanMessage, SystemMessage
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver
from utils.logger import get_logger

logger = get_logger()

# ---------------------------------------------------------------------------
# Project root (used by FilesystemBackend to resolve skill paths)
# ---------------------------------------------------------------------------
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)

# ---------------------------------------------------------------------------
# Deep agent definitions
# Each agent is created via create_deep_agent with its skills and tools.
# The existing LLM and prompts are reused; skills augment the prompts
# with AgentSkills-compliant SKILL.md content via progressive disclosure.
# ---------------------------------------------------------------------------

planner_agent = create_deep_agent(
    model=llm,
    tools=[],
    system_prompt=PLANNER_AGENT_PROMPT,
    skills=["skills/planner-skill/"],
    backend=FilesystemBackend(root_dir=PROJECT_ROOT),
    checkpointer=MemorySaver(),
)
logger.info("Planner agent created with FilesystemBackend, root_dir=%s", PROJECT_ROOT)
logger.debug("Skills paths: skills/planner-skill/")

generator_agent = llm

# generator_agent = create_deep_agent(
#     model=llm,
#     tools=[get_reddit_company_news, get_YF_data_tool],
#     system_prompt=GENERATION_AGENT_PROMPT,
#     skills=[],
# )

validator_agent = llm

# validator_agent = create_deep_agent(
#     model=llm,
#     tools=[],
#     system_prompt=VALIDATION_AGENT_PROMPT,
#     skills=[],
# )

# Augment the LLM with schema for structured output (retained for
# generator and validator nodes that use structured output)
generator_llm = llm.with_structured_output(Output)
validator_llm = llm.with_structured_output(ValidationState)


# Nodes
def planner(state: State):
    """Planner that generates a plan for the report"""

    logger.info("Instantiating Planner...")
    logger.debug("Planner input instructions: %s", state["instructions"])

    result = planner_agent.invoke(
        {
            "messages": [
                HumanMessage(content=state["instructions"]),
            ]
        },
        config={"configurable": {"thread_id": "planner"}},
    )
    logger.info("Plan generated:\n%s", result["messages"][-1].content)
    return {"plan": result["messages"][-1].content}


def generator(state: State):

    logger.info("Instantiating Generator...")
    logger.info("Plan: %s", state["plan"])

    completed_summary = generator_llm.invoke(
        [
            SystemMessage(content=GENERATION_AGENT_PROMPT),
            HumanMessage(content=state["plan"]),
        ]
    )
    logger.info("Output generated:\n%s", completed_summary["output"])
    return {
        "output": completed_summary["output"],
        "explanation": completed_summary["explanation"],
    }


def validator(state: State):

    # logger.info("Instantiating Validator...")
    validation = validator_llm.invoke(
        [
            SystemMessage(content=VALIDATION_AGENT_PROMPT),
            HumanMessage(content=state["output"] + state["explanation"]),
        ]
    )
    logger.info("Validation result:\n%s", validation["valid"])
    return {"valid": validation["valid"], "feedback": validation["feedback"]}
