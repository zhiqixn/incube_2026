import asyncio
import json
from typing import Callable, List

from autogen_core import (
    AgentId,
    FunctionCall,
    MessageContext,
    RoutedAgent,
    TopicId,
    message_handler,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
)
from autogen_core.tools import FunctionTool, Tool
from configs.tools_config import delegate_cfg
from messaging.messaging_protocols import AgentResponse, AgentTask, UserTask
from utils.logger import get_logger

logger = get_logger()


class BaseAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        system_message: SystemMessage,
        model_client: ChatCompletionClient,
        publish_topics: List[str],
        broadcast_topic_type: str = None,
        tools: List[Tool] = [],
        delegate_tools: List[Callable] = [],
    ):
        super().__init__(description)
        self._system_message = system_message
        self._model_client = model_client
        self._delegate_tools = delegate_tools
        self._delegate_tool_schema = None
        self._tools = dict([(tool.name, tool) for tool in tools])
        self._tool_schema = [tool.schema for tool in tools]
        self._publish_topics = publish_topics
        self._broadcast_topic_type = broadcast_topic_type
        self._chat_history: List[LLMMessage] = []
        self._delegated_agents = []
        self._delegation_queue = []
        self._sender_agent_topic_type = ""
        self._tool_result: List[FunctionExecutionResult] = []
        self._delegate_tool_result: List[FunctionExecutionResult] = []

    @message_handler
    async def handle_user_task(self, message: UserTask, ctx: MessageContext) -> None:
        """
        Handle a UserTask message and broadcasts it to all agents if
        broadcast_topic_type is not None.

        Then, sends the chat history to the LLM to generate a response, or
        a list of function calls, or delegate them. If a response message is returned,
        send the LLM response back to the user.

        Args:
            message: The UserTask message to be handled.
            ctx: The message context.
        """

        # designate message soure topic type
        self._sender_agent_topic_type = message.reply_to_topic_type

        # set delegate tool schema
        if not self._delegate_tool_schema and self._publish_topics:
            await self.set_delegate_tools_schema()

        if self._broadcast_topic_type:
            # add message to chat history
            self._chat_history.extend(message.context)

            # broadcast the message to all agents
            logger.info("Broadcasting message to all agents")
            await self.publish_message(
                message,
                topic_id=TopicId(self._broadcast_topic_type, source=self.id.key),
            )

            available_tools = (
                self._tool_schema + self._delegate_tool_schema
                if self._delegate_tool_schema
                else self._tool_schema
            )

            # Run user task
            llm_result = await self._model_client.create(
                messages=[self._system_message] + self._chat_history,
                tools=available_tools,
                cancellation_token=ctx.cancellation_token,
            )

            logger.info("LLM result: %s", llm_result)

            # if the LLM returns a list of function calls
            # handle function calls
            if isinstance(llm_result.content, list) and all(
                isinstance(m, FunctionCall) for m in llm_result.content
            ):
                self._tool_result = []
                self._delegate_tool_result = []
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
        else:
            self._system_message.content += (
                f"\n\nCurrent task context:{message.context[0].content}"
            )

    @message_handler
    async def handle_agent_task(self, message: AgentTask, ctx: MessageContext) -> None:
        """
        Handles AgentTask message.

        This message handler is called when the agent receives a task from another
        agent. It adds the task to the chat history and sends the chat
        history to the LLM. If the LLM returns a list of function calls,
        the agent runs them. Otherwise, the agent sends the LLM response
        back to the sending agent.

        Args:
            message: The AgentTask message to be handled.
            ctx: The message context.

        Returns:
            None
        """

        # add message to chat history
        self._chat_history.extend(message.context)
        # update topic type of agent to reply to
        self._sender_agent_topic_type = message.reply_to_topic_type

        if not self._delegate_tool_schema and self._publish_topics:
            await self.set_delegate_tools_schema()

        available_tools = (
            self._tool_schema + self._delegate_tool_schema
            if self._delegate_tool_schema
            else self._tool_schema
        )

        # analyse agent task
        llm_result = await self._model_client.create(
            messages=[self._system_message] + self._chat_history,
            tools=available_tools,
            cancellation_token=ctx.cancellation_token,
        )

        if isinstance(llm_result.content, list) and all(
            isinstance(m, FunctionCall) for m in llm_result.content
        ):
            self._tool_result = []
            self._delegate_tool_result = []
            await self.handle_function_calls(llm_result, ctx)

        # if LLM response is not a list of function calls, and no agent delegation
        # is required send it back to sender
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

            # add assistant message output to chat history
            self._chat_history.append(
                AssistantMessage(content=llm_result.content, source=self.id.type)
            )

    @message_handler
    async def handle_agent_response(
        self, message: AgentResponse, ctx: MessageContext
    ) -> None:
        """
        Handle an AgentResponse message.

        This message handler is called when the agent receives a response from an agent.
        It adds the response to the chat history and sends the chat history to the LLM.
        If the LLM returns a list of function calls, the agent runs them.
        Otherwise, the agent sends the LLM response back to the sending agent.

        Args:
            message: The AgentResponse message to be handled.
            ctx: The message context.

        Returns:
            None
        """
        logger.info(
            "%s received response from %s", self.id.type, message.reply_to_topic_type
        )

        # pop agent from list of delegated agents
        self._delegated_agents.remove(message.reply_to_topic_type)

        logger.info("Awaiting responses from: %s", self._delegated_agents)
        logger.info("To be delegated: %s", self._delegation_queue)

        tool_proxy_result = self._delegate_tool_result

        for result in tool_proxy_result:
            result_proxy_content = (
                eval(result.content)
                if isinstance(result.content, str)
                else result.content
            )
            result_content = []
            for indiv_result in result_proxy_content:
                if indiv_result[0] == message.context[0].source and not isinstance(
                    indiv_result[1], str
                ):
                    messages = "\n\n".join([m.content for m in message.context])
                    real_indiv_result = (indiv_result[0], messages)
                    result_content.append(real_indiv_result)
                else:
                    result_content.append(indiv_result)
            tool_result = FunctionExecutionResult(
                name=result.name, content=str(result_content), call_id=result.call_id
            )
            self._delegate_tool_result.remove(result)
            self._delegate_tool_result.append(tool_result)

        delegate_targets = self._delegation_queue

        if len(delegate_targets) > 0:
            while len(delegate_targets) > 0:
                target = delegate_targets.pop(0)
                agent, messages = target
                if agent in self._publish_topics:
                    if agent not in self._delegated_agents:
                        self._delegated_agents.append(agent)
                        self._delegation_queue.remove(target)
                        await self.publish_message(
                            AgentTask(
                                reply_to_topic_type=self.id.type,
                                context=messages,
                            ),
                            topic_id=TopicId(agent, source=self.id.key),
                        )

        # if there are no more delegated agents and no more tasks to delegate
        if len(self._delegated_agents) == 0 and len(self._delegation_queue) == 0:
            # add self._tool_result to chat history

            if self._tool_result:
                self._chat_history.append(
                    FunctionExecutionResultMessage(
                        content=self._tool_result + self._delegate_tool_result
                    )
                )
            else:
                self._chat_history.append(
                    FunctionExecutionResultMessage(content=self._delegate_tool_result)
                )

            self._tool_result = []
            self._delegate_tool_result = []

            available_tools = (
                self._tool_schema + self._delegate_tool_schema
                if self._delegate_tool_schema
                else self._tool_schema
            )

            # analyse agent task
            llm_result = await self._model_client.create(
                messages=[self._system_message] + self._chat_history,
                tools=available_tools,
                cancellation_token=ctx.cancellation_token,
            )

            if isinstance(llm_result.content, list) and all(
                isinstance(m, FunctionCall) for m in llm_result.content
            ):
                await self.handle_function_calls(llm_result, ctx)

            # if LLM response is not a list of function calls, and no agent delegation
            # is required send it back to sender
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
                    topic_id=TopicId(self._sender_agent_topic_type, source=self.id.key),
                )

                # add assistant message output to chat history
                self._chat_history.append(
                    AssistantMessage(content=llm_result.content, source=self.id.type)
                )

    async def handle_function_calls(
        self, llm_result: CreateResult, ctx: MessageContext
    ) -> None:
        """
        Process a list of function calls returned by the LLM and execute them using
        the appropriate tools or delegate tools.

        This method appends the function calls to the chat history, executes each
        function call using the corresponding tool or delegate tool, and appends
        the execution results to the chat history. If there are delegate targets,
        it further delegates tasks to the specified agents.

        Args:
            llm_result: The result of the LLM, which contains a list of function
                        calls to be processed.
            ctx: The message context which includes a cancellation token for
                managing task cancellation.

        Returns:
            None
        """

        # add message to chat history
        self._chat_history.append(
            AssistantMessage(content=llm_result.content, source=self.id.type)
        )

        delegate_targets = []
        # Process each function call.
        for call in llm_result.content:
            arguments = json.loads(call.arguments)

            if call.name in self._tools:
                logger.info("Running tool: %s", call.name)

                # run tool
                try:
                    tool_result = await self._tools[call.name].run_json(
                        arguments, ctx.cancellation_token
                    )
                    # save tool results
                    self._tool_result.append(
                        FunctionExecutionResult(
                            name=call.name,
                            content=self._tools[call.name].return_value_as_string(
                                tool_result
                            ),
                            call_id=call.id,
                        )
                    )
                except Exception as e:
                    self._tool_result.append(
                        FunctionExecutionResult(
                            name=call.name,
                            content=str(e),
                            call_id=call.id,
                            is_error=True,
                        )
                    )

            elif call.name in self._delegate_tools:
                # run delegate tool
                try:
                    next_delegate_targets = await self._delegate_tools[
                        call.name
                    ].run_json(arguments, ctx.cancellation_token)

                    new_delegate_targets = []

                    for target in next_delegate_targets:
                        if target[0] in self._publish_topics:
                            new_delegate_targets.append(target)
                        else:
                            new_delegate_targets.append(
                                (target[0], f"Error:{target[0]} is not a valid agent.")
                            )

                    delegate_targets += new_delegate_targets

                    # save pseudo delegate tool results
                    self._delegate_tool_result.append(
                        FunctionExecutionResult(
                            name=call.name,
                            content=self._delegate_tools[
                                call.name
                            ].return_value_as_string(new_delegate_targets),
                            call_id=call.id,
                        )
                    )
                except Exception as e:
                    self._delegate_tool_result.append(
                        FunctionExecutionResult(
                            name=call.name,
                            content=str(e),
                            call_id=call.id,
                            is_error=True,
                        )
                    )
            # if no such tool exists
            else:
                self._tool_result.append(
                    FunctionExecutionResult(
                        name=call.name,
                        content="valueError: Unknown tool: " + call.name,
                        call_id=call.id,
                        is_error=True,
                    )
                )

        # delegate task to agents if delegate targets exist
        if len(delegate_targets) > 0:
            while len(delegate_targets) > 0:
                target = delegate_targets.pop(0)
                agent, messages = target
                if agent in self._publish_topics:
                    if agent not in self._delegated_agents:
                        self._delegated_agents.append(agent)

                        await self.publish_message(
                            AgentTask(
                                reply_to_topic_type=self.id.type,
                                context=messages,
                            ),
                            topic_id=TopicId(agent, source=self.id.key),
                        )
                    else:
                        self._delegation_queue.append(target)
        else:
            # add tool results to chat history
            self._chat_history.append(
                FunctionExecutionResultMessage(content=self._tool_result)
            )

            available_tools = (
                self._tool_schema + self._delegate_tool_schema
                if self._delegate_tool_schema
                else self._tool_schema
            )

            # analyse agent task
            llm_result = await self._model_client.create(
                messages=[self._system_message] + self._chat_history,
                tools=available_tools,
                cancellation_token=ctx.cancellation_token,
            )

            if isinstance(llm_result.content, list) and all(
                isinstance(m, FunctionCall) for m in llm_result.content
            ):
                self._tool_result = []
                self._delegate_tool_result = []
                await self.handle_function_calls(llm_result, ctx)

            # if LLM response is not a list of function calls, and no agent delegation
            # is required send it back to sender
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
                    topic_id=TopicId(self._sender_agent_topic_type, source=self.id.key),
                )

                # add assistant message output to chat history
                self._chat_history.append(
                    AssistantMessage(content=llm_result.content, source=self.id.type)
                )

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

        assert self._delegate_tools, "No delegate tools found when publish_topics set"

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
        agent_description = metadata["description"]
        logger.info("Agent description for %s: %s", topic_id, agent_description)
        return f"{topic_id}"
