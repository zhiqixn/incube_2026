from autogen_core import MessageContext, TopicId
from autogen_core import RoutedAgent, message_handler

from messaging.messaging_protocols import AgentResponse, UserTask
from utils.logger import get_logger

logger = get_logger()


class UserAgent(RoutedAgent):
    def __init__(
        self, description: str, user_topic_type: str, agent_topic_type: str
    ) -> None:
        super().__init__(description)
        self._user_topic_type = user_topic_type
        self._agent_topic_type = agent_topic_type

    @message_handler
    async def handle_user_message(self, message: UserTask, ctx: MessageContext) -> None:
        """
        Handle a UserTask message by broadcasting it to the triage agent.

        Args:
            message: The UserTask message to be handled.
            ctx: The message context.
        """
        logger.info("Received message:\n%s", message.context)
        logger.info("Sending message to %s agent", self._agent_topic_type)

        # send message to triage agent
        await self.publish_message(
            message,
            topic_id=TopicId(self._agent_topic_type, source=self.id.key),
        )

    @message_handler
    async def handle_task_result(
        self, message: AgentResponse, ctx: MessageContext
    ) -> None:
        """
        Handle a response from a triage agent.

        This message handler is called when the user agent receives a response from
        the triage agent that was delegated a task and returned the result.

        Args:
            message: The message containing the response from the triage agent.
            ctx: The message context.

        Returns:
            None
        """
        assistant_msg = message.context[0]
        logger.info(
            "Final plan for %s:\n%s",
            self.id.key,
            assistant_msg.content,
        )
        return
