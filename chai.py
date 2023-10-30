import json
import os

import structlog
from litellm import ModelResponse
from litellm import completion as lm_completion

from plugins import Plugins

logger = structlog.get_logger()


class Chai:
    def __init__(self):
        self.model = os.environ.get("LLM_MODEL")
        self.plugins = Plugins()
        self.wit_smalltalk_api_key = os.environ.get("WIT_SMALLTALK_API_KEY", None)

    def completion(self, **kwargs) -> ModelResponse:
        """
        Wrapper for litellm.completion

        :param kwargs: Keyword arguments
        :return: Completion
        """
        kwargs["messages"], intent = self.reduce_messages_context(kwargs["messages"])
        functions = self.plugins.plugins if len(self.plugins.plugins) > 0 else None

        if functions and (not intent or intent == "casual"):
            kwargs["functions"] = functions

        response = lm_completion(model=self.model, **kwargs)

        fcall_tries = 0
        while (response["choices"][0]["finish_reason"] == "function_call") and (
            fcall_tries < int(os.environ.get("LLM_MAX_FCALL_TRIES", 5))
        ):
            message_content = response["choices"][0]["message"]["function_call"]

            fcall_response = self.plugins.call_function(
                name=message_content["name"],
                arguments=json.loads(message_content["arguments"]),
            )
            # Append the result of the function call to the messages history
            kwargs["messages"].append(
                {
                    "role": "function",
                    "name": message_content["name"],
                    "content": fcall_response,
                }
            )

            response = lm_completion(model=self.model, **kwargs)

        return response

    def reduce_messages_context(self, messages: list) -> tuple[list, str | None]:
        """
        Reduce the messages context where possible

        We are using intent recognition to determine if messages consist of
        "small talk" which means replies like "yes", "no", "ok", "thanks", etc.

        This will lead to removal of earlier messages which are not relevant
        anymore. We are only leaving the last 3 messages in the context.

        :param messages: List of messages
        :return: List of messages with reduced context and intent
        """
        intent = None

        # Context reduction is not required if there are less than 5 messages
        if len(messages) > 5:
            # Check if last message is small talk
            intent = self.plugins.wit(
                query=messages[-1]["content"],
                api_key=self.wit_smalltalk_api_key,
            )

            if intent == "casual":
                messages = [messages[0]] + messages[
                    -3:
                ]  # Keep system message, last 3 messages
                logger.debug("Reduced context", messages=messages)

        return messages, intent
