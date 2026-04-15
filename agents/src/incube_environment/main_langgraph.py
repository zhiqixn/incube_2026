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
    thread_id: int | str | None = None,
):
    """Run the multi-agent LangGraph workflow and stream results.

    Uses ``stream_mode=["messages", "updates"]`` so that:
    - ``"messages"`` events carry individual LLM tokens from the generator node
      as they arrive, enabling progressive UI updates.
    - ``"updates"`` events carry complete node state on completion, used for
      the planner (structured JSON output) and validator (structured output).

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
    thread_id:
        Optional tracing / checkpoint thread id.  When provided, it is
        passed to the LangGraph stream config so the planner agent's
        MemorySaver can maintain iterative state across invocations.

    Yields
    ------
    chunk : str
        The new text produced at this step (a single token during generator
        streaming, or a full section on node completion).
    accumulated : str
        The full response text accumulated so far.
    explanation : str
        Explanation text emitted by the planner node (empty otherwise).
    """
    accumulated = ""
    # Tokens streamed from the generator node before its "updates" event arrives.
    generator_streamed = ""
    # Set True once the generator "updates" event is consumed so we don't
    # double-yield the same content.
    generator_committed = False

    logger.info(
        "invoke_agent called — history turns=%d, uploaded_files=%d, instructions: %.80s",
        len(chat_history) if chat_history else 0,
        len(uploaded_files) if uploaded_files else 0,
        instructions,
    )

    stream_config = (
        {"configurable": {"thread_id": thread_id}} if thread_id is not None else None
    )

    stream = planner_worker.stream(
        {
            "instructions": instructions,
            "chat_history": chat_history or [],
            "uploaded_files": uploaded_files or [],
        },
        config=stream_config,
        stream_mode=["messages", "updates"],
    )

    try:
        for event_type, event_data in stream:

            # ── Token-level events ──────────────────────────────────────────
            if event_type == "messages":
                chunk_msg, metadata = event_data
                node_name = metadata.get("langgraph_node", "")
                token = chunk_msg.content if hasattr(chunk_msg, "content") else ""
                if not token:
                    continue

                # Only stream tokens from the generator (XML BT output).
                # Planner emits structured JSON (not useful to render partially);
                # validator emits structured JSON too — both stay node-level only.
                if node_name == "generator" and not generator_committed:
                    generator_streamed += token
                    partial_accumulated = accumulated + generator_streamed
                    yield token, partial_accumulated, ""

            # ── Node-completion events ──────────────────────────────────────
            elif event_type == "updates":
                for node_name, state_update in event_data.items():

                    if node_name == "planner" and "plan" in state_update:
                        plan_text = state_update["plan"]
                        explanation_text = state_update.get("explanation", "")
                        logger.info("Planner step completed")
                        chunk = f"**Plan:**\n\n{plan_text}\n\n---\n\n"
                        accumulated = chunk
                        # Reset generator tracking for potential retry loops.
                        generator_streamed = ""
                        generator_committed = False
                        yield chunk, accumulated, explanation_text

                    elif node_name == "generator" and "output" in state_update:
                        output_text = state_update["output"]
                        logger.info("Generator step completed")
                        generator_committed = True
                        # Use the canonical node output (includes any
                        # post-processing done after the LLM call).
                        accumulated += output_text
                        # Only yield if we never streamed tokens (fallback for
                        # non-streaming LLM backends).
                        if not generator_streamed:
                            yield output_text, accumulated, ""

                    elif node_name == "validator":
                        valid = state_update.get("valid")
                        feedback = state_update.get("feedback", "")
                        logger.info("Validator step — valid=%s", valid)
                        # Reset for potential retry loop.
                        generator_streamed = ""
                        generator_committed = False
                        if valid:
                            note = "\n\n---\n*Validation passed.*"
                            accumulated += note
                            yield note, accumulated, ""
                        elif valid is False and feedback:
                            note = f"\n\n---\n*Revision needed — {feedback}*"
                            accumulated += note
                            yield note, accumulated, ""
    except GeneratorExit:
        logger.info("invoke_agent generator closed by caller — shutting down stream gracefully")
        stream.close()


if __name__ == "__main__":
    logger.info("Instantiating planner...")
    logger.info("Topic: %s", prompt)

    output = ""
    for _chunk, output, _explanation in invoke_agent(prompt):
        pass

    logger.info("FINAL REPORT:\n%s", output)
