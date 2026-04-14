from configs.runtime_config import prompt
from langgraph.graph import StateGraph, START, END
from tools.tool_langgraph import should_continue
from agents.agent_langgraph import (
    planner,
    generator,
    validator,
)
from utils.utils_langgraph import State
from utils.logger import get_logger, setup_logger

setup_logger()
logger = get_logger()

# ---------------------------------------------------------------------------
# Build and compile the multi-agent workflow once at module level so it is
# ready when this module is imported by the frontend.
# ---------------------------------------------------------------------------
_builder = StateGraph(State)
_builder.add_node("planner", planner)
_builder.add_node("generator", generator)
_builder.add_node("validator", validator)

_builder.add_edge(START, "planner")
_builder.add_edge("planner", "generator")
_builder.add_edge("generator", "validator")

_builder.add_conditional_edges(
    "validator", should_continue, {END: END, "planner": "planner"}
)

planner_worker = _builder.compile()


def invoke_agent(
    instructions: str,
    chat_history: list | None = None,
    uploaded_files: list | None = None,
):
    """Run the multi-agent LangGraph workflow and stream results.

    Iterates over node-level updates emitted by the compiled graph and
    yields ``(chunk, accumulated)`` tuples so the caller can progressively
    update a display placeholder.

    Parameters
    ----------
    instructions:
        The user's request / mission specification text.
    chat_history:
        Prior conversation turns as a list of ``(user_msg, bot_msg)`` tuples.
        When provided, the planner receives the full conversation context so
        follow-up queries can reference earlier missions or clarifications.
    uploaded_files:
        Files attached to the current message, as a list of dicts produced
        by the frontend.  Text/YAML/JSON files are inlined into the planner
        message; image files are embedded as base64 ``image_url`` blocks.
        When present, these override the default mission spec.

    Yields
    ------
    chunk : str
        The new text produced at this step.
    accumulated : str
        The full response text accumulated so far.  After the generator
        node runs, ``accumulated`` becomes just the clean output so the
        final value stored by the caller is the finished report.
    """
    accumulated = ""

    logger.info(
        "invoke_agent called — history turns=%d, uploaded_files=%d, instructions: %.80s",
        len(chat_history) if chat_history else 0,
        len(uploaded_files) if uploaded_files else 0,
        instructions,
    )

    for event in planner_worker.stream({
        "instructions": instructions,
        "chat_history": chat_history or [],
        "uploaded_files": uploaded_files or [],
    }):
        for node_name, state_update in event.items():

            if node_name == "planner" and "plan" in state_update:
                plan_text = state_update["plan"]
                logger.info("Planner step completed")
                chunk = f"**Plan:**\n\n{plan_text}\n\n---\n\n"
                accumulated = chunk
                yield chunk, accumulated

            elif node_name == "generator" and "output" in state_update:
                output_text = state_update["output"]
                logger.info("Generator step completed")
                # Append XML output so the plan is preserved in the stream.
                # The full accumulated text (plan + XML + validation notes) is
                # what gets stored in the database for history retrieval.
                accumulated += output_text
                yield output_text, accumulated

            elif node_name == "validator":
                valid = state_update.get("valid")
                feedback = state_update.get("feedback", "")
                logger.info("Validator step — valid=%s", valid)
                if valid is False and feedback:
                    note = f"\n\n---\n*Revision needed — {feedback}*"
                    accumulated += note
                    yield note, accumulated


if __name__ == "__main__":
    logger.info("Instantiating planner...")
    logger.info("Topic: %s", prompt)

    full_output = ""
    for chunk, accumulated in invoke_agent(prompt):
        full_output = accumulated

    logger.info("FINAL REPORT:\n%s", full_output)