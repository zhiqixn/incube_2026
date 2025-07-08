from typing import Union
from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
from configs.tools_config import think_cfg


class ThoughtTask(BaseModel):
    thought: str = Field(..., description="The thought to log.")
    context: str = Field(
        default="General reasoning",
        description="The context or reason for this thought.",
    )


def think_about(thought_task: str) -> str:
    """
    Process and log a thought task.

    This tool is used for:
    1. Brainstorming solutions to bugs or issues
    2. Planning complex refactoring approaches
    3. Designing new features and architectures
    4. Organizing thoughts during debugging
    5. Documenting decision-making processes

    Args:
        thought_task (Union[ThoughtTask, str]): A thought task

    Returns:
        str: A formatted string containing the logged thought.
    """
    return f"Thought: {thought_task}"


think_tool = FunctionTool(think_about, description=think_cfg["description"])
