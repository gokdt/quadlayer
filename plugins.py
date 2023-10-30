import os

import requests
import structlog

logger = structlog.get_logger()


class Plugins:
    """
    Plugins for quadlayer

    We provide several plugins by default, but you can add your own plugins
    by adding them to the plugins list.
    """

    def __init__(self):
        search_plugin = {
            "name": "search",
            "description": "Search using search engine, useful when requires recent knowledge",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query to search",
                    },
                },
                "required": ["query"],
            },
        }

        self.plugins = []
        self.plugins_map = {}

        self.bing_api_key = os.environ.get("BING_API_KEY")

        if self.bing_api_key:
            logger.debug("Bing API key found, enabling search plugin")
            self.plugins.append(search_plugin)
            self.plugins_map["search"] = self.search

    def search(self, query: str) -> str:
        """
        Search using Bing

        :param query: Query
        :return: Search result
        """
        if not self.bing_api_key:
            raise Exception("Bing API key not found")

        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
        params = {"q": query}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        search_results = response.json()

        if not search_results["webPages"]["value"]:
            return "No results found"

        snippets = [
            f"{result['name']}: {result['snippet']}"
            for result in search_results["webPages"]["value"]
        ]
        return "\n\n".join(snippets)

    def call_function(self, name: str, arguments: dict) -> str:
        """
        Call a function

        :param name: Function name
        :param arguments: Function arguments
        :return: Function result
        """
        logger.debug("Calling function", name=name, arguments=arguments)
        if name not in self.plugins_map:
            raise Exception(f"Function {name} not found")

        return self.plugins_map[name](**arguments)
