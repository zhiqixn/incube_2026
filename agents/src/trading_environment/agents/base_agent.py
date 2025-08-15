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
    UserMessage,
    LLMMessage,
    SystemMessage,
)
from autogen_core.tools import FunctionTool, Tool
from configs.tools_config import delegate_cfg, condenser_cfg
from messaging.messaging_protocols import AgentResponse, AgentTask, UserTask
from pydantic import BaseModel
from utils.logger import get_logger
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace import get_current_span


logger = get_logger()


class BaseAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        system_message: SystemMessage,
        model: ChatCompletionClient,
        agent_topics: List[str] = [],
        handoff: bool = True,
        broadcast_topic: str = None,
        memory: List[str] = [],
        state: str = "",
        tools: List[Tool] = [],
        delegate_tools: List[Callable] = [],
    ):
        super().__init__(description)
        self._system_message = SystemMessage(content=system_message)
        self._model = model
        self._delegate_tools = delegate_tools
        self._delegate_tool_schema = None
        self._tools = dict([(tool.name, tool) for tool in tools])
        self._tool_schema = [tool.schema for tool in tools]
        self._handoff = handoff
        self._agent_topics = agent_topics
        self._broadcast_topic = broadcast_topic
        self._memory = memory
        self._state = state
        self._chat_history: dict[str, List[LLMMessage]] = {}
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

        self._chat_history["user_task"] = []

        # set delegate tool schema
        if not self._delegate_tool_schema and (self._agent_topics and self._handoff):
            await self.set_delegate_tools_schema()

        if self._broadcast_topic:
            if not message.broadcast:
                new_message = message.model_copy()
                new_message.broadcast = True
                # broadcast the message to all agents
                logger.info("Broadcasting message to all agents")
                await self.publish_message(
                    new_message,
                    topic_id=TopicId(self._broadcast_topic, source=self.id.key),
                )

        if not message.broadcast:
            print("Received user task")
            self._chat_history["user_task"].extend(message.context)
            available_tools = (
                self._tool_schema + self._delegate_tool_schema
                if self._delegate_tool_schema
                else self._tool_schema
            )

            current_span = get_current_span()
            current_span.set_attribute("available tools", str(available_tools))

            memory = []
            for state, messages in self._chat_history.items():
                if state in self._memory:
                    memory.extend(messages)

            # analyse agent task
            llm_result = await self._model.create(
                messages=[self._system_message] + memory,
                tools=available_tools,
                cancellation_token=ctx.cancellation_token,
            )

            # if the LLM returns a list of function calls
            # handle function calls
            if isinstance(llm_result.content, list) and all(
                isinstance(m, FunctionCall) for m in llm_result.content
            ):
                self._tool_result = []
                self._delegate_tool_result = []
                await self.handle_function_calls(llm_result, ctx)

            else:
                await self.transfer_control(llm_result, ctx)
        else:
            self._chat_history["user_task"].extend(message.context)

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

        logger.info("%s received task", self.id.type)

        # update agent memory
        self._chat_history = message.chat_history

        # update topic type of agent to reply to
        self._sender_agent_topic_type = message.reply_to_topic_type

        if not self._delegate_tool_schema and (self._agent_topics and self._handoff):
            await self.set_delegate_tools_schema()

        available_tools = (
            self._tool_schema + self._delegate_tool_schema
            if self._delegate_tool_schema
            else self._tool_schema
        )

        current_span = get_current_span()
        current_span.set_attribute("available tools", str(available_tools))

        # add context to llm based on relevant memory states
        memory = []
        for state, messages in self._chat_history.items():
            if state in self._memory:
                memory.extend(messages)

        # analyse agent task
        llm_result = await self._model.create(
            messages=[self._system_message] + memory + message.context,
            tools=available_tools,
            cancellation_token=ctx.cancellation_token,
        )

        if isinstance(llm_result.content, list) and all(
            isinstance(m, FunctionCall) for m in llm_result.content
        ):
            self._tool_result = []
            self._delegate_tool_result = []
            await self.handle_function_calls(llm_result, ctx)

        else:
            await self.transfer_control(llm_result, ctx)

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
                if agent in self._agent_topics:
                    if agent not in self._delegated_agents:
                        self._delegated_agents.append(agent)
                        self._delegation_queue.remove(target)
                        await self.publish_message(
                            AgentTask(
                                reply_to_topic_type=self.id.type,
                                context=messages,
                                chat_history=self._chat_history,
                            ),
                            topic_id=TopicId(agent, source=self.id.key),
                        )

        # if there are no more delegated agents and no more tasks to delegate
        if len(self._delegated_agents) == 0 and len(self._delegation_queue) == 0:

            if self._tool_result:
                tool_result_messages = FunctionExecutionResultMessage(
                    content=self._tool_result + self._delegate_tool_result
                )

            else:
                tool_result_messages = FunctionExecutionResultMessage(
                    content=self._delegate_tool_result
                )

            self._tool_result = []
            self._delegate_tool_result = []

            available_tools = (
                self._tool_schema + self._delegate_tool_schema
                if self._delegate_tool_schema
                else self._tool_schema
            )

            current_span = get_current_span()
            current_span.set_attribute("available tools", str(available_tools))

            # add context to llm based on relevant memory states
            memory = []
            for state, messages in self._chat_history.items():
                if state in self._memory:
                    memory.extend(messages)

            # analyse agent task
            llm_result = await self._model.create(
                messages=[self._system_message] + memory + tool_result_messages,
                tools=available_tools,
                cancellation_token=ctx.cancellation_token,
            )

            if isinstance(llm_result.content, list) and all(
                isinstance(m, FunctionCall) for m in llm_result.content
            ):
                await self.handle_function_calls(llm_result, ctx)

            # # if LLM response is not a list of function calls, and no agent delegation
            # # is required send it back to sender
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

                # add assistant message output to memory
                if self._state not in self._chat_history.keys():
                    self._chat_history[self._state] = []
                    logger.info("New memory state: %s", self._state)
                self._chat_history[self._state].append(
                    AssistantMessage(content=llm_result.content, source=self.id.type)
                )

    async def transfer_control(
        self, llm_result: CreateResult, ctx: MessageContext
    ) -> None:
        # add assistant message output to memory
        if self._state not in self._chat_history.keys():
            self._chat_history[self._state] = []
            logger.info("New memory state: %s", self._state)
        self._chat_history[self._state].append(
            AssistantMessage(content=llm_result.content, source=self.id.type)
        )

        if not self._handoff and self._agent_topics:
            transfer_targets_desc = await asyncio.gather(
                *[
                    self._get_agent_description(agent_id)
                    for agent_id in self._agent_topics
                ]
            )

            memory = []
            for state, messages in self._chat_history.items():
                if state in self._memory:
                    memory.extend(messages)

            for transfer_target, desc in zip(self._agent_topics, transfer_targets_desc):
                transfer_message = UserMessage(
                    content=(
                        "Based on the agent description:\n\n"
                        f"{desc}\n\n"
                        "Relay the initial user task and provide a succinct "
                        "task assignment for the {transfer_target} agent "
                        "required to fufill the user task, "
                    ),
                    source="User",
                )

                transfer_response = await self._model.create(
                    messages=[transfer_message],
                    tools=[],
                    cancellation_token=ctx.cancellation_token,
                )

                await self.publish_message(
                    AgentTask(
                        reply_to_topic_type=self._sender_agent_topic_type,
                        context=[
                            UserMessage(
                                content=transfer_response.content, source=self.id.type
                            )
                        ],
                        chat_history=self._chat_history,
                    ),
                    topic_id=TopicId(transfer_target, source=self.id.key),
                )
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

        delegate_targets = []
        # Process each function call.
        for call in llm_result.content:
            arguments = json.loads(call.arguments)

            if call.name in self._tools:
                logger.info("Running tool: %s", call.name)

                try:

                    if call.name == "condenser":

                        # Skip the condenser tool for now
                        continue
                        # condensed_history = []
                        # # condenser_model = model
                        # for message in self._chat_history:

                        #     if message.type == "FunctionExecutionResultMessage":
                        #         # print(message)
                        #         message_arg = {"message": message.content[0].content}
                        #         tool_result = await self._tools[call.name].run_json(
                        #             message_arg, ctx.cancellation_token
                        #         )
                        #         message.content[0].content = tool_result
                        #         # print(message)
                        #     condensed_history.append(message)
                        # self._chat_history = condensed_history

                        # self._tool_result.append(
                        #     FunctionExecutionResult(
                        #         name=call.name,
                        #         content=self._tools[call.name].return_value_as_string(
                        #             "Condenser executed"
                        #         ),
                        #         call_id=call.id,
                        #     )
                        # )
                    # save tool results
                    else:
                        tool_result = await self._tools[call.name].run_json(
                            arguments, ctx.cancellation_token
                        )

                        self._tool_result.append(
                            FunctionExecutionResult(
                                name=call.name,
                                content=self._tools[call.name].return_value_as_string(
                                    tool_result
                                ),
                                call_id=call.id,
                            )
                        )
                    logger.info("Tool %s executed.", call.name)
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
                        if target[0] in self._agent_topics:
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

                try:
                    tracer = trace.get_tracer(__name__)
                    with tracer.start_as_current_span(call.name) as span:
                        arguments = json.loads(call.arguments)
                        span.set_attribute("status", "ERROR")
                        span.set_status(Status(StatusCode.ERROR))
                        span.set_attribute("openinference.span.kind", "TOOL")
                        span.set_attribute("tool.name", call.name)
                        span.set_attribute("tool.description", "Invalid tool")
                        span.set_attribute("input.value", call.arguments)
                        span.set_attribute(
                            "output.value",
                            f"Exception: {call.name} is not a valid tool",
                        )
                        span.set_attribute("tool.parameters", list(arguments.keys()))
                        raise Exception(f"{call.name} is not a valid tool")
                except Exception:
                    pass

                self._tool_result.append(
                    FunctionExecutionResult(
                        name=call.name,
                        content=f"NameError: {call.name} is not a valid tool",
                        call_id=call.id,
                        is_error=True,
                    )
                )

        # delegate task to agents if delegate targets exist
        if len(delegate_targets) > 0:
            while len(delegate_targets) > 0:
                target = delegate_targets.pop(0)
                agent, messages = target
                if agent in self._agent_topics:
                    if agent not in self._delegated_agents:
                        self._delegated_agents.append(agent)

                        await self.publish_message(
                            AgentTask(
                                reply_to_topic_type=self.id.type,
                                context=messages,
                                chat_history=self._chat_history,
                            ),
                            topic_id=TopicId(agent, source=self.id.key),
                        )
                    else:
                        self._delegation_queue.append(target)
        else:

            available_tools = (
                self._tool_schema + self._delegate_tool_schema
                if self._delegate_tool_schema
                else self._tool_schema
            )

            # add context to llm based on relevant memory states
            memory = []
            for state, messages in self._chat_history.items():
                if state in self._memory:
                    memory.extend(messages)

            # analyse agent task
            llm_result = await self._model.create(
                messages=[
                    self._system_message,
                    *memory,
                    AssistantMessage(content=llm_result.content, source=self.id.type),
                    FunctionExecutionResultMessage(content=self._tool_result),
                ],
                tools=available_tools,
                cancellation_token=ctx.cancellation_token,
            )

            if isinstance(llm_result.content, list) and all(
                isinstance(m, FunctionCall) for m in llm_result.content
            ):

                self._delegate_tool_result = []
                await self.handle_function_calls(llm_result, ctx)

            # if LLM response is not a list of function calls, and no agent delegation
            # is required send it back to sender
            else:
                self._tool_result = []
                await self.transfer_control(llm_result, ctx)

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
            *[self._get_agent_description(topic_id) for topic_id in self._agent_topics]
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
        return f"{topic_id}: {agent_description}"
