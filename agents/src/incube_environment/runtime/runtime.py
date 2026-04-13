from typing import Any, Dict
from autogen_core import SingleThreadedAgentRuntime
from utils.logger import get_logger

logger = get_logger()


class MemoryAgentRuntime(SingleThreadedAgentRuntime):
    def __init__(
        self,
        *,
        intervention_handlers=None,
        tracer_provider=None,
        ignore_unhandled_exceptions=True
    ):
        super().__init__(
            intervention_handlers=intervention_handlers,
            tracer_provider=tracer_provider,
            ignore_unhandled_exceptions=ignore_unhandled_exceptions,
        )
        self.memory: Dict[str, list] = {}

    def set_memory(self, key: str, value: list) -> None:
        """Set a value in memory."""
        self.memory[key] = value

    def edit_memory(self, key: str, value: list) -> None:
        """Edit a value in memory."""
        self.memory[key].append(value)

    def get_memory(self, key: str, default: list = None) -> Any:
        """Get a value from memory."""
        return self.memory.get(key, default)

    def get_all_agent_memory(self, states) -> list[str]:
        memory = []
        for state, messages in self.memory.items():
            if state in states:
                memory.extend(messages)
        return memory

    def add_new_memory_state(self, llm_result, state) -> None:
        if state not in self.memory.keys():
            self.set_memory(state, [])
            logger.info("New memory state: %s", state)

        self.edit_memory(state, state + "\n\n" + llm_result.content)

    def check_memory_state(self, state) -> bool:
        return state in self.memory.keys()
