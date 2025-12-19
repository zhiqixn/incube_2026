from langchain.tools import tool
from langchain.agents import create_agent
from tools.tool_langgraph import get_reddit_company_news
from models.model_langgraph import llm
from configs.agents_config import (
    SOCIAL_MEDIA_ANALYST_AGENT_PROMPT,
    ORCHESTRATOR_AGENT_PROMPT,
)
from langgraph.types import Send
from utils.utils_langgraph import WorkerState, State, Sections, Route

from langchain.messages import HumanMessage, SystemMessage

social_media_analyst_agent = create_agent(
    llm,
    tools=[
        get_reddit_company_news,
    ],
    system_prompt=SOCIAL_MEDIA_ANALYST_AGENT_PROMPT,
)


@tool
def analyze_social_media(request: str) -> str:
    """Analyze social media and company-specific news for trading insights.

    Use this when the user wants a comprehensive report on a company's recent
    social media activity, public sentiment, and news coverage.

    Handles retrieval of Reddit articles, sentiment interpretation, and synthesis
    of fine-grained insights relevant to traders and investors.

    Input: Company name (e.g., 'NVIDIA', 'Tesla', 'Sea Ltd')
    """
    print("Message received")
    result = social_media_analyst_agent.invoke(
        {"messages": [{"role": "user", "content": request}]}
    )
    return result["messages"][-1].text


# orchestrator_agent = create_agent(
#     llm,
#     tools=[analyze_social_media],
#     system_prompt=(
#         "You are a coordinator of a trading system tasked with communicating \
# information to the analysts to complete the user request."
#         "Break down user requests into appropriate tool calls and coordinate \
# the results. "
#         "When a request involves multiple actions, use multiple tools in sequence."
#     ),
# )

# Augment the LLM with schema for structured output
planner = llm.with_structured_output(Sections)


# Nodes
def orchestrator(state: State):
    """Orchestrator that generates a plan for the report"""
    print("Orchestrator invoked with state:", state)
    # Run the augmented LLM with structured output to serve as routing logic
    report_sections = planner.invoke(
        [
            SystemMessage(
                content="Route the input to social_media based on the user's request."
            ),
            HumanMessage(content=state["topic"]),
        ]
    )

    return {"sections": report_sections.sections}


# def llm_call(state: WorkerState):
#     """Worker writes a section of the report"""
#     print("LLM call invoked with state:", state)
#     # Generate section
#     section = llm.invoke(
#         [
#             SystemMessage(
#                 content="Write a report section following the provided name and \
# description. Include no preamble for each section. Use markdown formatting."
#             ),
#             HumanMessage(
#                 content=f"Here is the section name: {state['section'].name} and \
# description: {state['section'].description}"
#             ),
#         ]
#     )

#     # Write the updated section to completed sections
#     return {"completed_sections": [section.content]}


def synthesizer(state: State):
    """Synthesize full report from sections"""
    print("Synthesizer invoked with state:", state)
    # List of completed sections
    completed_sections = state["completed_sections"]

    # Format completed section to str to use as context for final sections
    completed_report_sections = "\n\n---\n\n".join(completed_sections)

    return {"final_report": completed_report_sections}


# Conditional edge function to create llm_call workers that each write a section
# def assign_workers(state: State):
#     """Assign a worker to each section in the plan"""
#     print("Assigning workers with state:", state)
#     # Kick off section writing in parallel via Send() API
#     return [Send("llm_call", {"section": s}) for s in state["sections"]]


# Nodes
def llm_call_1(state: State):
    print("LLM call 1 invoked with state:", state)
    section = llm.invoke(
        [
            SystemMessage(
                content="Write a report section following the provided name and \
                    description. Include no preamble for each section. Use \
                        markdown formatting."
            ),
            HumanMessage(
                content=f"Here is the section name: {state['section'].name} and \
                    description: {state['section'].description}"
            ),
        ]
    )

    # Write the updated section to completed sections
    return {"completed_sections": [section.content]}


def llm_call_2(state: State):
    print("LLM call 2 invoked with state:", state)
    result = llm.invoke(state["topic"])
    return {"output": result.content}


def llm_call_3(state: State):
    print("LLM call 3 invoked with state:", state)
    result = llm.invoke(state["topic"])
    return {"output": result.content}


# Augment the LLM with schema for structured output
router = llm.with_structured_output(Route)


# def llm_call_router(state: State):
#     """Route the input to the appropriate node"""
#     print("Router invoked with state:", state)
#     # Run the augmented LLM with structured output to serve as routing logic
#     decision = router.invoke(
#         [
#             SystemMessage(
#                 content="Route the input to Tesla based on the user's request."
#             ),
#             HumanMessage(content=state["topic"]),
#         ]
#     )

#     return {"decision": decision.step}


# Conditional edge function to route to the appropriate node
def route_decision(state: State):
    print("Routing decision with state:", state)
    print("Sections:", state["sections"])
    # Return the node name you want to visit next
    for section in state["sections"]:
        if section.name == "social_media":
            return [Send("llm_call_1", {"section": section})]
