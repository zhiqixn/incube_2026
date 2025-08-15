from typing import List, Tuple, Union

from autogen_core.models import UserMessage
from pydantic import BaseModel, Field


class DelegationTask(BaseModel):
    agent: str = Field(..., description="The agent to delegate the task to.")
    task: str = Field(..., description="The details of the task to be delegated.")
    name: str = Field(..., description="The name of the agent delegating the task.")


def delegate_tasks(
    delegation_tasks: Union[List[DelegationTask], str],
) -> List[Tuple[str, List[UserMessage]]]:
    """
    Groups delegation tasks by agent and prepares a single combined message per agent.

    Args:
        delegation_tasks (Union[List[DelegationTask], str]): A list of tasks or a string
        representation of it.

    Returns:
        List[Tuple[str, List[UserMessage]]]: A list of tuples with the agent and their
        combined tasks.
    """
    if isinstance(delegation_tasks, str):
        delegation_tasks = [DelegationTask(**t) for t in eval(delegation_tasks)]

    return [
        (task.agent, [UserMessage(content=task.task, source=task.name)])
        for task in delegation_tasks
    ]
