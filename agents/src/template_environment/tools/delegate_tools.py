from typing import List, Tuple, Union
from autogen_core.models import AssistantMessage, LLMMessage, UserMessage
from pydantic import BaseModel, Field
from collections import defaultdict

class DelegationTask(BaseModel):
    agent: str = Field(..., description="The agent to delegate the task to.")
    task: str = Field(..., description="The details of the task to be delegated.")
    name: str = Field(..., description="The name of the agent delegating the task.")


def delegate_tasks(delegation_tasks: Union[List[DelegationTask], str]) -> List[Tuple[str, List[UserMessage]]]:
    """
    Groups delegation tasks by agent and prepares a single combined message per agent.

    Args:
        delegation_tasks (Union[List[DelegationTask], str]): A list of tasks or a string representation of it.

    Returns:
        List[Tuple[str, List[UserMessage]]]: A list of tuples with the agent and their combined tasks.
    """
    if isinstance(delegation_tasks, str):
        delegation_tasks = [DelegationTask(**t) for t in eval(delegation_tasks)]

    grouped = defaultdict(list)
    agent_sources = {}

    for task in delegation_tasks:
        grouped[task.agent].append(task.task)
        agent_sources[task.agent] = task.name  # assuming consistent delegator per agent

    return [
        (
            agent,
            [UserMessage(content="\n".join(tasks), source=agent_sources[agent])]
        )
        for agent, tasks in grouped.items()
    ]