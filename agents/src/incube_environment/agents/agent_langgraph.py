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

    logger.info("Instantiating Planner...")

    if state.get("output"):
        msg_content = f"{state['instructions']} \n\nHere is the validator feedback:\n \
            {state['output']}\n\nPlease revise the plan to address the feedback \
                and fix the issues identified."
    else:
        msg_content = state["instructions"]
    report_sections = llm.invoke(
        [
            SystemMessage(content=PLANNER_AGENT_PROMPT),
            HumanMessage(content=msg_content),
        ]
    )
    logger.info("Plan generated:\n%s", report_sections.content)
    return {"plan": report_sections.content}


def generator(state: State):

    logger.info("Instantiating Generator...")
    # logger.info("Plan: %s", state["plan"])

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

    logger.info("Instantiating Validator...")
    validation = validator_llm.invoke(
        [
            SystemMessage(content=VALIDATION_AGENT_PROMPT),
            HumanMessage(content=state["output"] + state["explanation"]),
        ]
    )
    logger.info("Validation result:\n%s", validation["valid"])
    return {"valid": validation["valid"], "feedback": validation["feedback"]}
