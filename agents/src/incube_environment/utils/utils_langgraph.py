from typing import Annotated, List
from typing_extensions import TypedDict, Literal
from pydantic import BaseModel, Field
import operator
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage

# from tools.tool_langgraph import get_reddit_company_news


# tools = [get_reddit_company_news]
# tool_node = ToolNode(tools)


# Schema for structured output to use in planning
class Section(BaseModel):
    name: Literal["social_media_analyst", "market_analyst"] = Field(
        description="Name for this section of the report.",
    )
    task: str = Field(
        description="Assigned task for this section",
    )
    history: list = Field(description="Tracks past agent actions")


class Sections(BaseModel):
    sections: List[Section] = Field(
        description="Sections of the report.",
    )


class State(TypedDict):
    instructions: str
    plan: str
    output: str
    explanation: str
    valid: bool
    feedback: str
    resource_url: str  # URL to an external resource (e.g. MinIO presigned URL)
    chat_history: list  # list of (user_msg, bot_msg) tuples from prior turns
    uploaded_files: list  # list of file dicts: {name, type, content} or {name, type, media_type, data}
    # sections: list[Section]
    # completed_sections: Annotated[list, operator.add]
    # final_report: str
    # decision: str
    # output: str

    # 🔹 REQUIRED for tool-calling (transport only)
    # messages: list[BaseMessage]


class ValidationState(TypedDict):
    valid: bool
    feedback: str


class PlannerResponse(TypedDict):
    plan: str
    explanation: str


class WorkerState(TypedDict):
    section: Annotated[Section, operator.add]
    completed_sections: Annotated[list, operator.add]
    messages: Annotated[list[BaseMessage], operator.add]


# Schema for structured output to use as routing logic
class Route(BaseModel):
    step: Literal["Tesla", "Apple", "Microsoft"] = Field(
        None, description="The next step in the routing process"
    )
