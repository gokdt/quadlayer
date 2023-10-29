import os

import redis
import structlog
from msgpack import packb, unpackb

logger = structlog.get_logger()


class Memory:
    def __init__(
        self,
        redis_url: str = os.getenv("REDIS_URL"),
        max_tokens: int = os.getenv("MAX_TOKENS"),
    ):
        self.redis_client = redis.from_url(redis_url)
        self.max_tokens = max_tokens

    def get_messages(self, chat_id: int) -> list:
        """
        Get messages from redis

        Older messages will be removed if total_tokens length is greater than max_tokens
        This does not remove the system messages as they are not part of the total_tokens length
        max_tokens should be set accordingly, depending on the model and system messages length

        :param chat_id: Chat ID
        :return: List of messages
        """

        messages = self.redis_client.get(chat_id)
        if messages:
            messages = unpackb(messages)
            # If total_tokens length is greater than max_tokens, remove the
            # oldest messages until it's not
            total_tokens = sum([message["prompt_tokens"] for message in messages])
            while total_tokens > self.max_tokens:
                logger.debug(
                    "Removing oldest message",
                    chat_id=chat_id,
                    total_tokens=total_tokens,
                    max_tokens=self.max_tokens,
                    message=messages[0],
                )
                messages.pop(0)
                total_tokens = sum([message["prompt_tokens"] for message in messages])

            # Update redis
            self.redis_client.set(chat_id, packb(messages))

            return messages

        return []

    def add_message(self, chat_id: int, message: dict) -> None:
        """
        Add message to chat_id in redis

        :param chat_id: Chat ID
        :param message: Message to add
        """
        messages = self.get_messages(chat_id)
        messages.append(message)
        self.redis_client.set(chat_id, packb(messages))

    def delete_messages(self, chat_id: int) -> None:
        """
        Delete messages from chat_id in redis

        :param chat_id: Chat ID
        """
        self.redis_client.delete(chat_id)
