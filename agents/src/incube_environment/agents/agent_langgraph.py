from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END
from tools.tool_langgraph import get_reddit_company_news, get_YF_data_tool
from models.model_langgraph import llm
from configs.agents_config import (
    PLANNER_AGENT_PROMPT,
    GENERATION_AGENT_PROMPT,
    VALIDATION_AGENT_PROMPT,
)
from langgraph.types import Send
from typing import Literal
from utils.utils_langgraph import (
    WorkerState,
    State,
    Sections,
    Section,
    Route,
    Output,
    ValidationState,
)

from langchain.messages import HumanMessage, SystemMessage, ToolMessage
from utils.logger import get_logger

logger = get_logger()

# Testing
tools = [get_reddit_company_news, get_YF_data_tool]
# tools_by_name = {tool.name: tool for tool in tools}
social_media_llm = llm.bind_tools([get_reddit_company_news])
market_llm = llm.bind_tools([get_YF_data_tool])

# Augment the LLM with schema for structured output
generator_llm = llm.with_structured_output(Output)
validator_llm = llm.with_structured_output(ValidationState)


# Nodes
def planner(state: State):
    """Planner that generates a plan for the report"""

    # print(state["instructions"])
    report_sections = llm.invoke(
        [
            SystemMessage(content=PLANNER_AGENT_PROMPT),
            HumanMessage(content=state["instructions"]),
        ]
    )

    return {"plan": report_sections.content}


def generator(state: State):

    logger.info("Instantiating Generator...")
    logger.info("Plan: %s", state["plan"])

    # TODO Needs to be structured output
    completed_summary = generator_llm.invoke(
        [
            SystemMessage(content=GENERATION_AGENT_PROMPT),
            HumanMessage(content=state["plan"]),
        ]
    )

    return {
        "output": completed_summary["output"],
        "explanation": completed_summary["explanation"],
    }


def validator(state: State):

    # TODO: Needs to be structured output
    validation = validator_llm.invoke(
        [
            SystemMessage(content=VALIDATION_AGENT_PROMPT),
            HumanMessage(content=state["output"] + state["explanation"]),
        ]
    )
    return {"valid": validation["valid"], "feedback": validation["feedback"]}
