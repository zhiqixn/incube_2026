from configs.runtime_config import prompt
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from IPython.display import Image, display
from agents.agent_langgraph import (
    planner,
    generator,
    validator,
)
from utils.utils_langgraph import State
from utils.logger import get_logger, setup_logger

setup_logger()
logger = get_logger()

if __name__ == "__main__":

    # Build workflow
    mission_builder = StateGraph(State)

    # Add the nodes
    mission_builder.add_node("planner", planner)
    mission_builder.add_node("generator", generator)
    mission_builder.add_node("validator", validator)

    # Add edges to connect nodes

    mission_builder.add_edge(START, "planner")
    mission_builder.add_edge("planner", "generator")
    mission_builder.add_edge("generator", "validator")
    mission_builder.add_edge("validator", END)

    # Compile the workflow
    planner_worker = mission_builder.compile()

    # Invoke
    logger.info("Instantiating planner...")
    logger.info("Topic: %s", prompt)

    state = planner_worker.invoke(
        {
            "instructions": prompt,
            # "section": {
            #     "name": "planner",
            #     "task": prompt,
            # },
        }
    )

    # from IPython.display import Markdown

    logger.info("FINAL REPORT:\n%s", state["output"])
