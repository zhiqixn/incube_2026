from configs.runtime_config import prompt
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
from agents.agent_langgraph import (
    orchestrator,
    synthesizer,
    llm_call_1,
    llm_call_2,
    llm_call_3,
    route_decision,
)
from utils.utils_langgraph import State

if __name__ == "__main__":
    # user_request = prompt

    # print("User Request:", user_request)
    # print("\n" + "=" * 80 + "\n")

    # for step in orchestrator_agent.stream(
    #     {"messages": [{"role": "user", "content": user_request}]}
    # ):
    #     for update in step.values():
    #         for message in update.get("messages", []):
    #             message.pretty_print()

    # Build workflow
    orchestrator_worker_builder = StateGraph(State)

    # Add the nodes
    orchestrator_worker_builder.add_node("orchestrator", orchestrator)
    # orchestrator_worker_builder.add_node("llm_call", llm_call)
    orchestrator_worker_builder.add_node("synthesizer", synthesizer)
    orchestrator_worker_builder.add_node("llm_call_1", llm_call_1)
    orchestrator_worker_builder.add_node("llm_call_2", llm_call_2)
    orchestrator_worker_builder.add_node("llm_call_3", llm_call_3)
    # orchestrator_worker_builder.add_node("llm_call_router", llm_call_router)

    # Add edges to connect nodes
    orchestrator_worker_builder.add_edge(START, "orchestrator")
    # orchestrator_worker_builder.add_conditional_edges(
    #     "orchestrator", assign_workers, ["llm_call"]
    # )
    # orchestrator_worker_builder.add_edge("llm_call", "synthesizer")
    # orchestrator_worker_builder.add_edge("synthesizer", END)

    orchestrator_worker_builder.add_conditional_edges(
        "orchestrator",
        route_decision,
        {  # Name returned by route_decision : Name of next node to visit
            "llm_call_1": "llm_call_1",
            "llm_call_2": "llm_call_2",
            "llm_call_3": "llm_call_3",
        },
    )
    # orchestrator_worker_builder.add_edge("llm_call_1", END)
    orchestrator_worker_builder.add_edge("llm_call_2", END)
    orchestrator_worker_builder.add_edge("llm_call_3", END)
    orchestrator_worker_builder.add_edge("llm_call_1", "synthesizer")
    orchestrator_worker_builder.add_edge("synthesizer", END)

    # Compile the workflow
    orchestrator_worker = orchestrator_worker_builder.compile()

    # Show the workflow
    # display(Image(orchestrator_worker.get_graph().draw_mermaid_png()))

    # Invoke
    state = orchestrator_worker.invoke({"topic": prompt})

    from IPython.display import Markdown

    Markdown(state["final_report"])
