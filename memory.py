import os

import redis
import structlog
import tiktoken
from msgpack import packb, unpackb

logger = structlog.get_logger()


class Memory:
    def __init__(self):
        self.redis_client = redis.from_url(os.environ.get("REDIS_URL"))
        self.max_tokens = os.environ.get("MAX_TOKENS", 4096)
        self.enc = tiktoken.encoding_for_model("gpt-4")

    def get_messages(self, chat_id: str) -> list:
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
            total_tokens = sum([message["content_tokens"] for message in messages])
            while total_tokens > self.max_tokens:
                logger.debug(
                    "Removing oldest message",
                    chat_id=chat_id,
                    total_tokens=total_tokens,
                    max_tokens=self.max_tokens,
                    message=messages[0],
                )
                messages.pop(0)
                total_tokens = sum([message["content_tokens"] for message in messages])

            # Update redis
            self.redis_client.set(chat_id, packb(messages))

            return messages

        return []

    def add_message(self, chat_id: str, message: dict) -> None:
        """
        Add message to chat_id in redis

        :param chat_id: Chat ID
        :param message: Message to add
        """
        messages = self.get_messages(chat_id)
        message["content_tokens"] = len(self.enc.encode(message["content"]))
        messages.append(message)
        self.redis_client.set(chat_id, packb(messages))

    def delete_messages(self, chat_id: str) -> None:
        """
        Delete messages from chat_id in redis

        :param chat_id: Chat ID
        """
        self.redis_client.delete(chat_id)

    def get_profile(self, user_id: str) -> dict:
        """
        Get user profile from redis

        :param user_id: User ID
        :return: User profile
        """
        profile = self.redis_client.get(f"profile_{user_id}")
        if profile:
            return unpackb(profile)

        return {}

    def set_profile(self, user_id: str, profile: dict) -> None:
        """
        Set user profile in redis

        :param user_id: User ID
        :param profile: User profile
        """
        self.redis_client.set(f"profile_{user_id}", packb(profile))
