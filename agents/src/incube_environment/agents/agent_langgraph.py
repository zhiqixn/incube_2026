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
    # Output,
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

    logger.info("Invoking planner agent with message content:\n%s", msg_content)
    result = planner_agent.invoke(
        {
            "messages": [
                HumanMessage(content=msg_content),
            ]
        },
        config={"configurable": {"thread_id": "planner"}},
    )
    logger.info("Plan generated:\n%s", result["messages"][-1].content)
    return {"plan": result["messages"][-1].content}


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
    resource_url = state['resource_url']
    content = state['output']

    logger.info(f"Validator got resource URL: {resource_url}")

    validation = validator_llm.invoke(
        [
            SystemMessage(content=VALIDATION_AGENT_PROMPT),
            HumanMessage(content=[
                {"type": "image_url", "image_url": {"url":resource_url}},
                {"type": "text", "content": content}
            ]),
        ]
    )
    
    logger.info("Validation result:\n%s", validation["valid"])

    # TODO: Save explanation to local folder if valid is true.
    return {"valid": validation["valid"], "feedback": validation["feedback"]}
