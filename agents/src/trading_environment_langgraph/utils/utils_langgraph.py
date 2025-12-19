from typing import Annotated, List
from typing_extensions import TypedDict, Literal
from pydantic import BaseModel, Field
import operator


# Schema for structured output to use in planning
class Section(BaseModel):
    name: Literal["social_media"] = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Brief overview of the main topics and \
            concepts to be covered in this section.",
    )


class Sections(BaseModel):
    sections: List[Section] = Field(
        description="Sections of the report.",
    )


# Graph state
class State(TypedDict):
    topic: str  # Report topic
    sections: list[Section]  # List of report sections
    completed_sections: Annotated[
        list, operator.add
    ]  # All workers write to this key in parallel
    final_report: str  # Final report
    decision: str
    output: str


# Worker state
class WorkerState(TypedDict):
    section: Section
    completed_sections: Annotated[list, operator.add]


# Schema for structured output to use as routing logic
class Route(BaseModel):
    step: Literal["Tesla", "Apple", "Microsoft"] = Field(
        None, description="The next step in the routing process"
    )
