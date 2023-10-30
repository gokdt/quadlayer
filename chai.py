import json
import os

from litellm import ModelResponse
from litellm import completion as lm_completion

from plugins import Plugins


class Chai:
    def __init__(self):
        self.model = os.environ.get("LLM_MODEL")
        self.plugins = Plugins()

    def completion(self, **kwargs) -> ModelResponse:
        """
        Wrapper for litellm.completion

        :param kwargs: Keyword arguments
        :return: Completion
        """
        functions = self.plugins.plugins if len(self.plugins.plugins) > 0 else None

        if functions:
            kwargs["functions"] = functions

        response = lm_completion(model=self.model, **kwargs)

        fcall_tries = 0
        while (response["choices"][0]["finish_reason"] == "function_call") and (
            fcall_tries < 5
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
