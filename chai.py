import os

from litellm import ModelResponse
from litellm import completion as lm_completion


class Chai:
    def __init__(self):
        self.model = os.environ.get("LLM_MODEL")

    def completion(self, **kwargs) -> ModelResponse:
        """
        Wrapper for litellm.completion

        :param kwargs: Keyword arguments
        :return: Completion
        """
        return lm_completion(model=self.model, **kwargs)
