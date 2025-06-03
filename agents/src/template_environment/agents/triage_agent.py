import asyncio
import json
from typing import Callable, List, Tuple

from autogen_core import AgentId, MessageContext, TopicId
from autogen_core import FunctionCall, RoutedAgent, message_handler
from autogen_core.models import (
    AssistantMessage,
    UserMessage,
    ChatCompletionClient,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
)
from autogen_core.tools import FunctionTool

from configs.tools_config import delegate_cfg
from messaging.messaging_protocols import AgentResponse, AgentTask, UserTask
from utils.logger import get_logger

logger = get_logger()


class Triage(RoutedAgent):
    def __init__(
        self,
        description: str,
        system_message: SystemMessage,
        publish_topics: List[str],
        delegate_tools: List[Callable],
        model_client: ChatCompletionClient,
        broadcast_topic_type: str = "patient_profile",
    ):
        super().__init__(description)
        self._system_message = system_message
        self._model_client = model_client
        self._publish_topics = publish_topics
        self._delegate_tools = delegate_tools
        self._delegate_tool_schema = None
        self._broadcast_topic_type = broadcast_topic_type
        self._chat_history: List[LLMMessage] = []
        self._delegated_agents = []
        self._agent_topic_type = ""
        self._tool_result: List[FunctionExecutionResult] = []

    @message_handler
    async def handle_user_task(self, message: UserTask, ctx: MessageContext) -> None:
        """
        Handle a UserTask message by adding it to the chat history and broadcasting
        it to all agents. Then, send the chat history to the LLM and if it returns
        a list of function calls, delegate them. Otherwise, send the LLM response
        back to the user.

        Args:
            message: The UserTask message to be handled.
            ctx: The message context.
        """
        # add message to chat history
        self._chat_history.extend(message.context)

        # designate message soure topic type
        self._agent_topic_type = message.reply_to_topic_type

        if not self._delegate_tool_schema:
            await self.set_delegate_tools_schema()

        # broadcast the message to all agents
        logger.info("Broadcasting message to all agents")
        await self.publish_message(
            message, topic_id=TopicId(self._broadcast_topic_type, source=self.id.key)
        )

        # analyse user task and delegate if necessary by sending to LLM
        llm_result = await self._model_client.create(
            messages=[self._system_message] + self._chat_history,
            tools=self._delegate_tool_schema,
            cancellation_token=ctx.cancellation_token,
        )

        logger.info("LLM result: %s", llm_result)

        # if the LLM returns a list of function calls, delegate them
        if isinstance(llm_result.content, list) and all(
            isinstance(m, FunctionCall) for m in llm_result.content
        ):
            self._tool_result = []
            await self.handle_function_calls(llm_result, ctx)

        # if LLM response is not a list of function calls, send it back to user
        else:
            await self.publish_message(
                AgentResponse(
                    reply_to_topic_type=self.id.type,
                    context=[
                        AssistantMessage(
                            content=llm_result.content, source=self.id.type
                        )
                    ],
                ),
                topic_id=TopicId(message.reply_to_topic_type, source=self.id.key),
            )
            # add message to chat history
            self._chat_history.append(
                AssistantMessage(content=llm_result.content, source=self.id.type)
            )

    @message_handler
    async def handle_agent_response(
        self, message: AgentResponse, ctx: MessageContext
    ) -> None:
        """
        Handle a response from an agent that was delegated a task.

        This message handler is called when the triage agent receives a response from
        an agent that was delegated a task. If the response is a list of function calls,
        the triage agent delegates them. Otherwise, the triage agent sends the response
        back to the user.

        Args:
            message: The message containing the response from the delegated agent.
            ctx: The message context.

        Returns:
            None
        """
        logger.info("Triage received response from %s", message.reply_to_topic_type)

        # pop agent from list of delegated agents
        if message.reply_to_topic_type in self._delegated_agents:
            self._delegated_agents.remove(message.reply_to_topic_type)

        tool_proxy_result = self._tool_result

        for result in tool_proxy_result:
            result_proxy_content = (
                eval(result.content)
                if isinstance(result.content, str)
                else result.content
            )
            result_content = []
            for indiv_result in result_proxy_content:
                if indiv_result[0] == message.context[0].source:
                    indiv_result = (
                        indiv_result[0],
                        indiv_result[1] + [message.context],
                    )
                    result_content.append(indiv_result)
                else:
                    result_content.append(indiv_result)
            tool_result = FunctionExecutionResult(
                name=result.name, content=str(result_content), call_id=result.call_id
            )
            self._tool_result.remove(result)
            self._tool_result.append(tool_result)

        # if LLM response is not a list of function calls, send it back to user
        if len(self._delegated_agents) == 0:
            # add self._tool_result to chat history
            self._chat_history.append(
                FunctionExecutionResultMessage(content=self._tool_result)
            )

            self._tool_result = []

            # analyse user task and delegate if necessary by sending to LLM
            llm_result = await self._model_client.create(
                messages=[self._system_message] + self._chat_history,
                cancellation_token=ctx.cancellation_token,
            )

            logger.info("Triage sending response back to %s", self._agent_topic_type)
            await self.publish_message(
                AgentResponse(
                    reply_to_topic_type=self.id.type,
                    context=[
                        AssistantMessage(
                            content=llm_result.content, source=self.id.type
                        )
                    ],
                ),
                topic_id=TopicId(self._agent_topic_type, source=self.id.key),
            )
            # add message to chat history
            self._chat_history.append(
                AssistantMessage(content=llm_result.content, source=self.id.type)
            )

    async def handle_function_calls(
        self, llm_result: CreateResult, ctx: MessageContext
    ) -> None:
        """
        Process a list of function calls returned by the LLM.

        This method adds the function calls to the chat history, runs each function
        call against the corresponding delegate tool, and adds the results to the
        chat history. It also sends the function calls to the agents specified in
        the delegate targets.

        Args:
            llm_result: The result of the LLM, which should contain a list of
                function calls.
            ctx: The message context.

        Returns:
            None
        """
        # add message to chat history
        self._chat_history.append(
            AssistantMessage(content=llm_result.content, source=self.id.type)
        )

        # process each function call
        function_execution_results = []
        delegate_targets = []
        for call in llm_result.content:
            arguments = json.loads(call.arguments)
            assert call.name in self._delegate_tools, f"Unknown tool: {call.name}"
            delegate_targets_new = await self._delegate_tools[call.name].run_json(
                arguments, ctx.cancellation_token
            )
            delegate_targets += delegate_targets_new
            function_execution_results.append(
                FunctionExecutionResult(
                    name=call.name,
                    content=self._delegate_tools[call.name].return_value_as_string(
                        delegate_targets
                    ),
                    call_id=call.id,
                )
            )
            # save tool tasks to agent
            self._tool_result.append(
                FunctionExecutionResult(
                    name=call.name,
                    content=self._delegate_tools[call.name].return_value_as_string(
                        delegate_targets
                    ),
                    call_id=call.id,
                )
            )

        # delegate task to agents if delegate targets exist
        if len(delegate_targets) > 0:
            for target in delegate_targets:
                agent, messages = target
                await self.publish_message(
                    AgentTask(
                        reply_to_topic_type=self.id.type,
                        context=messages,
                    ),
                    topic_id=TopicId(agent, source=self.id.key),
                )
                self._delegated_agents.append(agent)

    async def set_delegate_tools_schema(self) -> None:
        """
        Set the schema of the delegate tools, which are used to create messages that
        will be sent to other agents for delegation.

        This function is called once during the initialization of the agent.

        The schema of the delegate tools is constructed by calling the
        `agent_metadata` method of the runtime for each agent type available for
        delegation, and then constructing a `FunctionTool` for each tool with the
        description of the agent types.

        The resulting schema is stored in `self._delegate_tool_schema`.
        """
        # get descriptions of agents available for delegation
        agents_descriptions = await asyncio.gather(
            *[
                self._get_agent_description(topic_id)
                for topic_id in self._publish_topics
            ]
        )
        logger.info("Agent descriptions:\n%s", "\n".join(agents_descriptions))

        # create delegate tools of FunctionTool type
        self._delegate_tools = dict(
            [
                (
                    tool.__name__,
                    FunctionTool(
                        tool,
                        description=delegate_cfg["description"].format(
                            agents="\n".join(agents_descriptions)
                        ),
                    ),
                )
                for tool in self._delegate_tools
            ]
        )
        self._delegate_tool_schema = [
            tool.schema for tool in self._delegate_tools.values()
        ]

    async def _get_agent_description(self, topic_id):
        metadata = await self._runtime.agent_metadata(AgentId(topic_id, "default"))
        description = metadata["description"]
        return f"{topic_id}"  #: {description}"
